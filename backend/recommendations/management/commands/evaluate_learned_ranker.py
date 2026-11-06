"""Run the learned-ranker experiment (#183).

Usage (from backend/):
    python manage.py evaluate_learned_ranker [--labels PATH]
        [--extra-labels PATH] [--export-unlabelled PATH [--force]] [--markdown]

Follows docs/experiment_learned_ranker.md, fixed before the first run:

- trains on the tune children's labelled pairs and scores the test
  children (and the content-gap child) once;
- checks generalisation with leave-one-child-out on tune;
- compares nDCG and precision with SBERT-only and with the app's formula
  at settings.RANKING_ALPHA, on the same labels;
- reports the learned weights and applies the decision rule.

While any top-5 activity of the learned ranker is unlabelled, only the
counts are printed, so grading the extra pairs stays blind. Export them
with --export-unlabelled, grade them, and pass them back with
--extra-labels. The children are created in a transaction that is rolled
back.
"""

import csv
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recommendations import heldout, learned_ranker
from recommendations.evaluation import (
    METRICS,
    SELECTION_METRIC,
    LabelError,
    compare,
    load_heldout_labels,
    mean,
    score_all,
)

from .evaluate_alpha_grid import DEFAULT_LABELS
from .export_heldout_labels import COLUMNS

USERNAME = "learned-ranker@nurtura.invalid"
NAMES = [name for name, _ in METRICS]
MARGIN = 0.02  # the decision rule's margin, as for alpha


class Command(BaseCommand):
    help = "Train a learned ranker on the tune children and test it once."

    def add_arguments(self, parser):
        parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
        parser.add_argument("--extra-labels", type=Path)
        parser.add_argument("--export-unlabelled", type=Path)
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--markdown", action="store_true")

    def handle(self, *args, **options):
        self.markdown = options["markdown"]
        alpha = float(settings.RANKING_ALPHA)
        relevance, sheet_rows = self._labels(options)
        split = {
            s: [c.child_id for c in heldout.HELDOUT_CHILDREN if c.split == s]
            for s in heldout.SPLITS
        }
        candidates = self._candidates(alpha)

        X, y = learned_ranker.training_set(split["tune"], candidates, relevance)
        model = learned_ranker.fit(X, y)
        learned = {}
        for child_id in split["tune"]:  # leave one child out
            others = [c for c in split["tune"] if c != child_id]
            loco = learned_ranker.fit(
                *learned_ranker.training_set(others, candidates, relevance)
            )
            learned[child_id] = learned_ranker.rank(loco, candidates[child_id])
        for child_id in split["test"] + split["gap"]:
            learned[child_id] = learned_ranker.rank(model, candidates[child_id])

        self._heading("Data")
        counts = {g: int((y == g).sum()) for g in (0, 1, 2)}
        self._line(
            f"Trained on {len(y)} labelled pairs of {len(split['tune'])} tune "
            f"children (grade 0: {counts[0]}, 1: {counts[1]}, 2: {counts[2]}); "
            f"features: {', '.join(learned_ranker.FEATURES)}; multinomial "
            f"logistic regression, standardised features, C = {learned_ranker.C}."
        )

        missing = self._unlabelled(learned, relevance, split)
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    f"Provisional: {len(missing)} top-{heldout.POOL_DEPTH} "
                    "activities of the learned ranker have no label, so no "
                    "results are printed. Export them with --export-unlabelled, "
                    "grade them, and pass them back with --extra-labels."
                )
            )
            if options["export_unlabelled"]:
                self._export(options, missing, candidates, sheet_rows)
            return

        methods = {
            "SBERT-only": lambda c: candidates[c].sbert,
            f"alpha {alpha:.1f}": lambda c: candidates[c].hybrid,
            "Learned ranker": lambda c: learned[c],
        }
        scores = {
            name: {c: score_all(ranking(c), relevance.get(c, {})) for c in candidates}
            for name, ranking in methods.items()
        }
        hybrid_name = f"alpha {alpha:.1f}"
        loco = self._means("Tune set, leave one child out", scores, split["tune"])
        test = self._means("Test set", scores, split["test"])
        outcomes = self._per_child(scores, split["test"], hybrid_name)
        self._means("Content-gap child (reported separately)", scores, split["gap"])
        self._weights(model)
        self._decision(loco, test, outcomes, hybrid_name)

    # Data

    def _labels(self, options):
        relevance, sheet_rows = {}, {}
        paths = [options["labels"]]
        if options["extra_labels"]:
            paths.append(options["extra_labels"])
        for path in paths:
            try:
                labels = load_heldout_labels(path)
            except LabelError as exc:
                raise CommandError(
                    f"Can't use {path}:\n  " + "\n  ".join(exc.problems)
                ) from exc
            for child_id, grades in labels.relevance.items():
                for aid, grade in grades.items():
                    known = relevance.get(child_id, {}).get(aid)
                    if known is not None and known != grade:
                        raise CommandError(
                            f"{child_id} / {aid} is graded {known} in one sheet "
                            f"and {grade} in another."
                        )
                    relevance.setdefault(child_id, {})[aid] = grade
            for child_id, ids in labels.rows.items():
                sheet_rows.setdefault(child_id, set()).update(ids)
        return relevance, sheet_rows

    def _candidates(self, alpha):
        found = {}
        with transaction.atomic():
            caregiver = get_user_model().objects.create_user(username=USERNAME)
            for child in heldout.HELDOUT_CHILDREN:
                profile = heldout.create_child(child, caregiver)
                found[child.child_id] = learned_ranker.candidates_for(profile, alpha)
            transaction.set_rollback(True)
        return found

    def _unlabelled(self, learned, relevance, split):
        self._heading("Unlabelled top-5 activities of the learned ranker")
        missing, rows = set(), []
        for name, ids in split.items():
            count = 0
            for child_id in ids:
                for aid in learned[child_id][: heldout.POOL_DEPTH]:
                    if aid not in relevance.get(child_id, {}):
                        count += 1
                        missing.add((child_id, aid))
            rows.append([name, str(count)])
        self._table(["Split", "Unlabelled"], rows)
        return sorted(missing)

    def _export(self, options, missing, candidates, sheet_rows):
        path = options["export_unlabelled"]
        if path.exists() and not options["force"]:
            raise CommandError(f"{path} already exists. Use --force to overwrite it.")
        by_child = {}
        for child_id, aid in missing:
            if aid not in sheet_rows.get(child_id, set()):
                by_child.setdefault(child_id, []).append(aid)
        rows = []
        for child in heldout.HELDOUT_CHILDREN:
            for aid in heldout.shuffled(
                by_child.get(child.child_id, []), child.child_id
            ):
                activity = candidates[child.child_id].activities[aid]
                rows.append(
                    {
                        "child_id": child.child_id,
                        "split": child.split,
                        "child_profile": child.profile,
                        "activity_id": aid,
                        "activity_name": activity.activity_name,
                        "activity_description": activity.description,
                        "age_range": activity.age_range,
                        "relevance": "",
                        "notes": "",
                        "relevance_rater2": "",
                    }
                )
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        self._line(f"Wrote {len(rows)} unlabelled pair(s) to {path}")

    # Report

    def _means(self, title, scores, child_ids):
        self._heading(f"{title} ({len(child_ids)} children)")
        means, rows = {}, []
        for name, by_child in scores.items():
            values = {n: mean(by_child[c][n] for c in child_ids) for n in NAMES}
            means[name] = values
            rows.append([name, *(self._fmt(values[n]) for n in NAMES)])
        self._table(["Ranking", *NAMES], rows)
        return means

    def _per_child(self, scores, child_ids, hybrid_name):
        self._heading(f"Test set, per child ({SELECTION_METRIC})")
        rows, outcomes = [], {"improved": 0, "tied": 0, "worse": 0}
        for c in child_ids:
            new = scores["Learned ranker"][c][SELECTION_METRIC]
            old = scores[hybrid_name][c][SELECTION_METRIC]
            base = scores["SBERT-only"][c][SELECTION_METRIC]
            outcome = compare(new, old)
            if outcome:
                outcomes[outcome] += 1
            rows.append(
                [c, self._fmt(base), self._fmt(old), self._fmt(new), outcome or "n/a"]
            )
        self._table(
            [
                "Child",
                "SBERT-only",
                hybrid_name,
                "Learned",
                f"Learned vs {hybrid_name}",
            ],
            rows,
        )
        self._line("")
        self._line(
            f"Learned against {hybrid_name}: {outcomes['improved']} improved, "
            f"{outcomes['tied']} tied, {outcomes['worse']} worse. With this few "
            "children, no significance claims are made."
        )
        return outcomes

    def _weights(self, model):
        self._heading("Learned weights (standardised, towards grade 2 over grade 0)")
        weights = learned_ranker.weights(model)
        self._table(
            ["Feature", "Weight"],
            [
                [f, f"{w:+.3f}"]
                for f, w in sorted(weights.items(), key=lambda x: -abs(x[1]))
            ],
        )

    def _decision(self, loco, test, outcomes, hybrid_name):
        self._heading("Decision rule")
        learned, hybrid = test["Learned ranker"], test[hybrid_name]
        checks = [
            (
                f"Test {SELECTION_METRIC} at least {MARGIN} above {hybrid_name}",
                learned[SELECTION_METRIC] is not None
                and hybrid[SELECTION_METRIC] is not None
                and learned[SELECTION_METRIC] >= hybrid[SELECTION_METRIC] + MARGIN,
            ),
            (
                "More test children improve than get worse",
                outcomes["improved"] > outcomes["worse"],
            ),
            (
                f"Leave-one-out tune {SELECTION_METRIC} not below {hybrid_name}'s",
                loco["Learned ranker"][SELECTION_METRIC] is not None
                and loco["Learned ranker"][SELECTION_METRIC]
                >= loco[hybrid_name][SELECTION_METRIC],
            ),
        ]
        self._table(
            ["Condition", "Met"], [[text, "yes" if ok else "no"] for text, ok in checks]
        )
        self._line("")
        if all(ok for _, ok in checks):
            self._line(
                "All three are met: the learned ranker may replace the formula, "
                "if the evaluation is re-frozen."
            )
        else:
            self._line(f"Not all are met: {hybrid_name} stays.")

    # Output helpers

    @staticmethod
    def _fmt(value):
        return "n/a" if value is None else f"{value:.3f}"

    def _heading(self, text):
        self.stdout.write(f"\n## {text}" if self.markdown else f"\n== {text}")

    def _line(self, text):
        self.stdout.write(text)

    def _table(self, header, rows):
        if self.markdown:
            self.stdout.write("| " + " | ".join(header) + " |")
            self.stdout.write("|" + "---|" * len(header))
            for row in rows:
                self.stdout.write("| " + " | ".join(row) + " |")
        else:
            widths = [max(len(str(x)) for x in col) for col in zip(header, *rows)]
            for row in [header, *rows]:
                self.stdout.write(
                    "  ".join(str(x).ljust(w) for x, w in zip(row, widths))
                )
