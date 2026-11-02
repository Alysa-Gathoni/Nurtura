"""Compare a candidate embedding model with the current one (#172).

Usage (from backend/):
    python manage.py compare_embedding_model [--model NAME] [--labels PATH]
        [--extra-labels PATH] [--export-unlabelled PATH [--force]] [--markdown]

Both models are scored on the same held-out labels (the v2 sheet by default)
and only on the two rankings fixed in advance:

- SBERT-only: is the semantic search itself better?
- alpha = settings.RANKING_ALPHA (0.7): is what the app shows better?

Alpha is not re-tuned. The candidate's vectors are written inside a
transaction that is rolled back, and the encoder is restored afterwards, so
the stored embeddings and the app are unchanged.

The candidate may put activities in a top 5 that nobody has labelled. They
are counted, and --export-unlabelled writes them as a blind, shuffled sheet
in the held-out format. Once graded, pass it back with --extra-labels.
While any top-5 activity of either ranking is unlabelled, the comparison is
marked provisional.
"""

import csv
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from activities.models import DevelopmentalActivity
from recommendations import embeddings, heldout
from recommendations.evaluation import (
    METRICS,
    SELECTION_METRIC,
    LabelError,
    compare,
    load_heldout_labels,
    mean,
    score_all,
)
from recommendations.models import ActivityEmbedding

from .evaluate_alpha_grid import DEFAULT_LABELS
from .export_heldout_labels import COLUMNS

DEFAULT_MODEL = "multi-qa-MiniLM-L6-cos-v1"
MODELS_DIR = Path(settings.BASE_DIR) / "models"
USERNAME = "model-comparison@nurtura.invalid"
NAMES = [name for name, _ in METRICS]


def load_candidate(name):
    """The candidate encoder, downloaded once into backend/models/ (gitignored)."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(
        f"sentence-transformers/{name}", cache_folder=str(MODELS_DIR)
    )
    return embeddings.SentenceTransformerEncoder(model, name=name)


class Command(BaseCommand):
    help = "Compare a candidate embedding model on the held-out labels."

    def add_arguments(self, parser):
        parser.add_argument("--model", default=DEFAULT_MODEL)
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
        alpha = float(settings.RANKING_ALPHA)
        self.methods = (heldout.BASELINE, alpha)
        relevance, sheet_rows = self._labels(options)

        current = embeddings.get_encoder()
        if options["model"] == current.name:
            raise CommandError(f"{current.name} is already the current model.")
        try:
            candidate = load_candidate(options["model"])
        except Exception as exc:
            raise CommandError(f"Can't load {options['model']}: {exc}") from exc

        results = {current.name: self._rankings()}
        try:
            results[candidate.name] = self._rankings(candidate)
        finally:
            embeddings.set_encoder(current)

        by_split = {
            split: [c.child_id for c in heldout.HELDOUT_CHILDREN if c.split == split]
            for split in heldout.SPLITS
        }
        unlabelled = self._unlabelled(results, relevance, by_split)
        for split, title in (("tune", "Tune set"), ("test", "Test set")):
            self._means(title, results, relevance, by_split[split])
        self._test_outcomes(results, relevance, by_split["test"], candidate.name)
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
            self._line("Every top-5 activity of both rankings is labelled.")
        if options["export_unlabelled"]:
            self._export(options, unlabelled, results[candidate.name], sheet_rows)

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

    def _rankings(self, encoder=None):
        """{child_id: {method: ids}}, plus activities by ID, for one model."""
        rankings, activities = {}, {}
        with transaction.atomic():
            if encoder is not None:
                self._embed_all(encoder)
                embeddings.set_encoder(encoder)
            caregiver = get_user_model().objects.create_user(username=USERNAME)
            for child in heldout.HELDOUT_CHILDREN:
                profile = heldout.create_child(child, caregiver)
                found, ranked = heldout.rankings_for(profile, alphas=[self.methods[1]])
                rankings[child.child_id] = {m: ranked[m] for m in self.methods}
                activities.update(found)
            transaction.set_rollback(True)
        return {"rankings": rankings, "activities": activities}

    def _embed_all(self, encoder):
        published = list(DevelopmentalActivity.objects.published())
        texts = [embeddings.activity_text(a) for a in published]
        vectors = encoder.encode(texts)
        for activity, text, vector in zip(published, texts, vectors):
            ActivityEmbedding.objects.update_or_create(
                activity=activity,
                defaults={
                    "model_name": encoder.name,
                    "dimensions": encoder.dimensions,
                    "text_hash": embeddings.text_hash(encoder.name, text),
                    "vector": embeddings.to_bytes(vector),
                },
            )

    # Report

    def _unlabelled(self, results, relevance, by_split):
        self._heading("Unlabelled top-5 activities")
        missing, rows = set(), []
        for model, result in results.items():
            for method in self.methods:
                per_split = []
                for split in heldout.SPLITS:
                    count = 0
                    for child_id in by_split[split]:
                        graded = relevance.get(child_id, {})
                        top = result["rankings"][child_id][method][: heldout.POOL_DEPTH]
                        for activity_id in top:
                            if activity_id not in graded:
                                count += 1
                                missing.add((child_id, activity_id))
                    per_split.append(count)
                rows.append(
                    [
                        model,
                        self._method(method),
                        *map(str, per_split),
                        str(sum(per_split)),
                    ]
                )
        self._table(["Model", "Ranking", *heldout.SPLITS, "total"], rows)
        return sorted(missing)

    def _means(self, title, results, relevance, child_ids):
        self._heading(f"{title} ({len(child_ids)} children): mean of each metric")
        rows = []
        for method in self.methods:
            for model, result in results.items():
                scores = [
                    score_all(result["rankings"][c][method], relevance.get(c, {}))
                    for c in child_ids
                ]
                rows.append(
                    [
                        self._method(method),
                        model,
                        *(self._fmt(mean(s[n] for s in scores)) for n in NAMES),
                    ]
                )
        self._table(["Ranking", "Model", *NAMES], rows)

    def _test_outcomes(self, results, relevance, child_ids, candidate):
        self._heading(f"Test set: {candidate} against the current model, per child")
        current = next(m for m in results if m != candidate)
        rows = []
        for method in self.methods:
            counts = {"improved": 0, "tied": 0, "worse": 0}
            for child_id in child_ids:
                grades = relevance.get(child_id, {})
                new = score_all(
                    results[candidate]["rankings"][child_id][method], grades
                )
                old = score_all(results[current]["rankings"][child_id][method], grades)
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

    def _export(self, options, missing, candidate, sheet_rows):
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
                activity = candidate["activities"][activity_id]
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
        return "SBERT-only" if method == heldout.BASELINE else f"alpha {method:.1f}"

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
