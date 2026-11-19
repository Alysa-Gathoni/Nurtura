"""Compare SBERT, TF-IDF and their hybrid on the held-out labels (#248).

Usage (from backend/):
    python manage.py compare_tfidf [--labels PATH] [--extra-labels PATH]
        [--export-unlabelled PATH [--force]] [--markdown]

The similarity is  beta * SBERT cosine + (1 - beta) * TF-IDF cosine.  Each
beta in BETAS (0 = TF-IDF only, 1 = SBERT only, the app's setting) is scored
on the v2 held-out labels in two rankings fixed in advance:

- similarity-only (no rule priority, no age weight): is the search better?
- alpha = settings.RANKING_ALPHA (0.7): is what the app would show better?

Alpha is not re-tuned.

The rule for choosing beta was written down before any result was seen
(19 Nov 2026, issue #248):

    On the tune children at alpha = 0.7, take the beta with the highest mean
    nDCG@5. It replaces beta = 1 only if its mean is at least MIN_GAIN (0.02)
    higher than beta = 1's; otherwise the app keeps SBERT only. The chosen
    beta is then reported once on the test children.

Every beta is shown on the test set too, for the record, but the decision is
the tune-set rule.

TF-IDF may put activities in a top 5 that nobody has labelled. They count as
not relevant, and the comparison is marked provisional while any exist;
--export-unlabelled writes them as a blind, shuffled sheet in the held-out
format, to grade and pass back with --extra-labels.

The held-out children are created inside a transaction that is rolled back,
so nothing is stored and the app's setting is unchanged.
"""

import csv
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings

from recommendations import heldout
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

BETAS = (0.0, 0.25, 0.5, 0.75, 1.0)
CURRENT = 1.0
MIN_GAIN = 0.02
USERNAME = "tfidf-comparison@nurtura.invalid"
NAMES = [name for name, _ in METRICS]


def choose_beta(tune_means, current=CURRENT, min_gain=MIN_GAIN):
    """The pre-registered rule: {beta: mean nDCG@5 on tune} -> chosen beta."""
    known = {b: m for b, m in tune_means.items() if m is not None}
    if current not in known:
        return current
    best = max(known, key=lambda b: (known[b], b == current))
    return best if known[best] >= known[current] + min_gain else current


class Command(BaseCommand):
    help = "Compare SBERT, TF-IDF and their hybrid on the held-out labels."

    def add_arguments(self, parser):
        parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
        parser.add_argument(
            "--extra-labels",
            type=Path,
            help="Graded sheet of pairs exported with --export-unlabelled.",
        )
        parser.add_argument(
            "--export-unlabelled",
            type=Path,
            help="Write the unlabelled top-5 pairs here as a blind sheet.",
        )
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--markdown", action="store_true")

    def handle(self, *args, **options):
        self.markdown = options["markdown"]
        self.alpha = float(settings.RANKING_ALPHA)
        self.methods = (heldout.BASELINE, self.alpha)
        relevance, sheet_rows = self._labels(options)
        results = self._rankings()

        by_split = {
            split: [c.child_id for c in heldout.HELDOUT_CHILDREN if c.split == split]
            for split in heldout.SPLITS
        }
        unlabelled = self._unlabelled(results, relevance, by_split)
        tune = self._means("Tune set", results, relevance, by_split["tune"])
        chosen = choose_beta(tune[self.alpha])
        self._decision(tune[self.alpha], chosen)
        self._means("Test set (for the record)", results, relevance, by_split["test"])
        self._test_outcomes(results, relevance, by_split["test"], chosen)
        self._line("")
        if unlabelled:
            self.stdout.write(
                self.style.WARNING(
                    f"Provisional: {len(unlabelled)} top-{heldout.POOL_DEPTH} "
                    "activities have no label and count as not relevant. Export "
                    "them with --export-unlabelled, grade them, and pass them "
                    "back with --extra-labels."
                )
            )
        else:
            self._line("Every top-5 activity of every ranking is labelled.")
        if options["export_unlabelled"]:
            self._export(options, unlabelled, results["activities"], sheet_rows)

    # Labels

    def _labels(self, options):
        paths = [options["labels"]]
        if options["extra_labels"]:
            paths.append(options["extra_labels"])
        relevance, sheet_rows = {}, {}
        for path in paths:
            try:
                labels = load_heldout_labels(path)
            except LabelError as exc:
                raise CommandError(
                    f"Can't use {path}:\n  " + "\n  ".join(exc.problems)
                ) from exc
            for child_id, grades in labels.relevance.items():
                for activity_id, grade in grades.items():
                    known = relevance.get(child_id, {}).get(activity_id)
                    if known is not None and known != grade:
                        raise CommandError(
                            f"{child_id} / {activity_id} is graded {known} in one "
                            f"sheet and {grade} in another."
                        )
                    relevance.setdefault(child_id, {})[activity_id] = grade
            for child_id, ids in labels.rows.items():
                sheet_rows.setdefault(child_id, set()).update(ids)
        return relevance, sheet_rows

    # Rankings

    def _rankings(self):
        """{beta: {child_id: {method: ids}}}, plus activities by ID."""
        rankings, activities = {beta: {} for beta in BETAS}, {}
        with transaction.atomic():
            caregiver = get_user_model().objects.create_user(username=USERNAME)
            profiles = [
                (child.child_id, heldout.create_child(child, caregiver))
                for child in heldout.HELDOUT_CHILDREN
            ]
            for beta in BETAS:
                with override_settings(RETRIEVAL_BETA=beta):
                    for child_id, profile in profiles:
                        found, ranked = heldout.rankings_for(
                            profile, alphas=[self.alpha]
                        )
                        rankings[beta][child_id] = {m: ranked[m] for m in self.methods}
                        activities.update(found)
            transaction.set_rollback(True)
        return {"rankings": rankings, "activities": activities}

    # Report

    def _scores(self, results, relevance, beta, method, child_ids):
        return [
            score_all(results["rankings"][beta][c][method], relevance.get(c, {}))
            for c in child_ids
        ]

    def _unlabelled(self, results, relevance, by_split):
        self._heading("Unlabelled top-5 activities")
        missing, rows = set(), []
        for beta in BETAS:
            for method in self.methods:
                per_split = []
                for split in heldout.SPLITS:
                    count = 0
                    for child_id in by_split[split]:
                        graded = relevance.get(child_id, {})
                        ranked = results["rankings"][beta][child_id][method]
                        for activity_id in ranked[: heldout.POOL_DEPTH]:
                            if activity_id not in graded:
                                count += 1
                                missing.add((child_id, activity_id))
                    per_split.append(count)
                rows.append(
                    [
                        self._beta(beta),
                        self._method(method),
                        *map(str, per_split),
                        str(sum(per_split)),
                    ]
                )
        self._table(["Beta", "Ranking", *heldout.SPLITS, "total"], rows)
        return sorted(missing)

    def _means(self, title, results, relevance, child_ids):
        """Prints the table; returns {method: {beta: mean nDCG@5}}."""
        self._heading(f"{title} ({len(child_ids)} children): mean of each metric")
        rows, selection = [], {m: {} for m in self.methods}
        for method in self.methods:
            for beta in BETAS:
                scores = self._scores(results, relevance, beta, method, child_ids)
                means = {n: mean(s[n] for s in scores) for n in NAMES}
                selection[method][beta] = means[SELECTION_METRIC]
                rows.append(
                    [
                        self._method(method),
                        self._beta(beta),
                        *(self._fmt(means[n]) for n in NAMES),
                    ]
                )
        self._table(["Ranking", "Beta", *NAMES], rows)
        return selection

    def _decision(self, tune_means, chosen):
        self._heading("Decision (rule fixed before the results)")
        if all(m is None for m in tune_means.values()):
            self._line("No graded tune pairs, so no decision: beta stays 1.0.")
            return
        best = max(
            (b for b in tune_means if tune_means[b] is not None),
            key=lambda b: tune_means[b],
        )
        self._line(
            f"Best on tune at alpha {self.alpha:.1f}: {self._beta(best)} "
            f"({self._fmt(tune_means[best])}); SBERT only: "
            f"{self._fmt(tune_means[CURRENT])}. Needed gain: {MIN_GAIN}."
        )
        if chosen == CURRENT:
            self._line("Chosen: beta 1.0 (SBERT only): the app keeps its setting.")
        else:
            self._line(f"Chosen: {self._beta(chosen)}.")

    def _test_outcomes(self, results, relevance, child_ids, chosen):
        self._heading(
            f"Test set: the chosen {self._beta(chosen)} against SBERT only, per child"
        )
        if chosen == CURRENT:
            self._line("The chosen beta is SBERT only, so there is nothing to compare.")
            return
        rows = []
        for method in self.methods:
            counts = {"improved": 0, "tied": 0, "worse": 0}
            for child_id in child_ids:
                grades = relevance.get(child_id, {})
                new = score_all(results["rankings"][chosen][child_id][method], grades)
                old = score_all(results["rankings"][CURRENT][child_id][method], grades)
                outcome = compare(new[SELECTION_METRIC], old[SELECTION_METRIC])
                if outcome:
                    counts[outcome] += 1
            rows.append(
                [
                    self._method(method),
                    f"{counts['improved']} / {counts['tied']} / {counts['worse']}",
                ]
            )
        self._table(["Ranking", f"Improved / tied / worse on {SELECTION_METRIC}"], rows)
        self._line("")
        self._line("With this few children, no significance claims are made.")

    def _export(self, options, missing, activities, sheet_rows):
        path = options["export_unlabelled"]
        if path.exists() and not options["force"]:
            raise CommandError(f"{path} already exists. Use --force to overwrite it.")
        by_child = {}
        for child_id, activity_id in missing:
            if activity_id not in sheet_rows.get(child_id, set()):
                by_child.setdefault(child_id, []).append(activity_id)
        rows = []
        for child in heldout.HELDOUT_CHILDREN:
            for activity_id in heldout.shuffled(
                by_child.get(child.child_id, []), child.child_id
            ):
                activity = activities[activity_id]
                rows.append(
                    {
                        "child_id": child.child_id,
                        "split": child.split,
                        "child_profile": child.profile,
                        "activity_id": activity_id,
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

    # Output helpers

    def _method(self, method):
        if method == heldout.BASELINE:
            return "similarity-only"
        return f"alpha {method:.1f}"

    @staticmethod
    def _beta(beta):
        names = {0.0: " (TF-IDF only)", 1.0: " (SBERT only)"}
        return f"beta {beta:.2f}{names.get(beta, '')}"

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
