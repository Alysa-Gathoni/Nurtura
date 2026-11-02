"""Tests for the embedding-model comparison (#172)."""

import csv
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError

from .management.commands.export_heldout_labels import COLUMNS
from .models import ActivityEmbedding
from .test_embeddings import FakeEncoder
from .test_heldout import HeldOutCommandTestCase

LOADER = "recommendations.management.commands.compare_embedding_model.load_candidate"


class CandidateEncoder(FakeEncoder):
    """A different stand-in model: same words, shifted buckets."""

    name = "candidate-encoder"

    def encode(self, texts):
        return super().encode([f"{t} candidate" for t in texts])


class CompareEmbeddingModelTests(HeldOutCommandTestCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch(LOADER, return_value=CandidateEncoder())
        self.loader = patcher.start()
        self.addCleanup(patcher.stop)

    def label_all(self, path, grade="1"):
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            row["relevance"] = grade
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        return rows

    def compare(self, *args):
        out = StringIO()
        call_command(
            "compare_embedding_model",
            "--labels",
            str(self.path),
            *args,
            stdout=out,
            stderr=StringIO(),
        )
        return out.getvalue()

    def test_reports_both_models_on_the_fixed_rankings(self):
        self.publish()
        self.export()
        self.label_all(self.path)
        output = self.compare()
        self.assertIn("fake-encoder", output)
        self.assertIn("candidate-encoder", output)
        self.assertIn("SBERT-only", output)
        self.assertIn("alpha 0.7", output)
        self.assertNotIn("alpha 0.3", output)  # no re-tuning
        self.assertIn("Tune set (11 children)", output)
        self.assertIn("Test set (8 children)", output)
        self.assertIn("Improved / tied / worse on nDCG@5", output)

    def test_stored_embeddings_and_encoder_are_unchanged(self):
        self.publish()
        self.export()
        before = {
            e.activity_id: (e.model_name, bytes(e.vector))
            for e in ActivityEmbedding.objects.all()
        }
        self.compare()
        after = {
            e.activity_id: (e.model_name, bytes(e.vector))
            for e in ActivityEmbedding.objects.all()
        }
        self.assertEqual(after, before)
        from . import embeddings

        self.assertEqual(embeddings.get_encoder().name, "fake-encoder")

    def test_export_and_merge_unlabelled_pairs(self):
        self.publish()
        self.export()
        self.label_all(self.path)
        extra = self.path.with_name("extra.csv")
        output = self.compare("--export-unlabelled", str(extra))
        self.assertIn("Wrote", output)
        with open(extra, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(list(rows[0].keys()) if rows else COLUMNS, COLUMNS)
        for row in rows:
            self.assertEqual(row["relevance"], "")

        if rows:
            self.label_all(extra)
            merged = self.compare("--extra-labels", str(extra))
            self.assertIn("Every top-5 activity of both rankings is labelled", merged)

        with self.assertRaisesMessage(CommandError, "already exists"):
            self.compare("--export-unlabelled", str(extra))

    def test_conflicting_grades_are_refused(self):
        self.publish()
        self.export()
        rows = self.label_all(self.path, grade="2")
        extra = self.path.with_name("extra.csv")
        with open(extra, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerow({**rows[0], "relevance": "0"})
        with self.assertRaisesMessage(CommandError, "graded 2 in one sheet and 0"):
            self.compare("--extra-labels", str(extra))

    def test_candidate_must_differ_from_the_current_model(self):
        self.publish()
        self.export()
        with self.assertRaisesMessage(CommandError, "already the current model"):
            self.compare("--model", "fake-encoder")
