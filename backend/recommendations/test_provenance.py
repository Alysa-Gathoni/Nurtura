"""Tests for the held-out provenance sidecar and the unlabelled guard (#44)."""

import csv
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from activities.choices import ContentStatus
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from profiles.models import ReferenceMilestone
from profiles.rules import guidelines

from . import embeddings, provenance, ranking
from .evaluation import unlabelled_in_top
from .models import ActivityEmbedding
from .test_embeddings import FakeEncoder
from .test_heldout import HeldOutCommandTestCase
from .test_spot_check import DOMAIN_ACTIVITIES


class SidecarPathTests(SimpleTestCase):
    def test_sits_next_to_the_sheet(self):
        self.assertEqual(
            provenance.sidecar_path(Path("data/heldout_labels.csv")),
            Path("data/heldout_labels.provenance.json"),
        )


class UnlabelledInTopTests(SimpleTestCase):
    def test_counts_blank_and_missing_rows_per_method_and_child(self):
        rankings = {
            "H01": {"sbert-only": ["A", "B", "C"], 0.5: ["C", "D", "A"]},
            "H02": {"sbert-only": ["A", "B", "C"], 0.5: ["B", "A", "C"]},
        }
        relevance = {"H01": {"A": 2, "B": 0, "C": 1}, "H02": {"A": 0}}
        self.assertEqual(
            unlabelled_in_top(rankings, relevance, depth=2),
            {"sbert-only": {"H01": 0, "H02": 1}, 0.5: {"H01": 1, "H02": 1}},
        )


class SnapshotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_milestones", stdout=StringIO())

    def setUp(self):
        embeddings.set_encoder(FakeEncoder())
        self.addCleanup(embeddings.set_encoder, None)
        for fields in DOMAIN_ACTIVITIES:
            DevelopmentalActivity.objects.create(
                **activity_fields(content_status=ContentStatus.PUBLISHED, **fields)
            )
        call_command("embed_activities", stdout=StringIO())
        self.recorded = provenance.snapshot(rows={"H01": ["ACT-0956"]})

    def changes(self, rows=None):
        rows = rows or {"H01": ["ACT-0956"]}
        return provenance.differences(self.recorded, provenance.snapshot(rows=rows))

    def test_unchanged_state_has_no_differences(self):
        self.assertEqual(self.changes(), [])
        self.assertEqual(len(self.recorded["activities"]), len(DOMAIN_ACTIVITIES))
        self.assertEqual(self.recorded["embedding"]["model_name"], "fake-encoder")
        self.assertIn("generated_at", self.recorded["info"])

    def test_survives_a_round_trip_through_the_file(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "s.provenance.json"
        provenance.write(path, self.recorded)
        self.assertEqual(
            provenance.differences(
                provenance.read(path), provenance.snapshot(rows={"H01": ["ACT-0956"]})
            ),
            [],
        )

    def test_activity_content_edit(self):
        DevelopmentalActivity.objects.filter(activity_id="ACT-0951").update(
            description="Something else entirely."
        )
        self.assertEqual(self.changes(), ["activity content changed: ACT-0951"])

    def test_activities_added_and_unpublished(self):
        DevelopmentalActivity.objects.filter(activity_id="ACT-0952").update(
            content_status=ContentStatus.UNDER_REVIEW
        )
        DevelopmentalActivity.objects.create(
            **activity_fields(
                activity_id="ACT-0960", content_status=ContentStatus.PUBLISHED
            )
        )
        changes = "\n".join(self.changes())
        self.assertIn("Published activities added: ACT-0960", changes)
        self.assertIn("no longer Published (or deleted): ACT-0952", changes)
        self.assertIn("embeddings changed", changes)  # ACT-0952's vector left

    def test_rule_weight_change(self):
        with mock.patch.object(guidelines, "NOT_YET_DEFICIT", 12.0):
            self.assertEqual(self.changes(), ["rule weights changed: not_yet_deficit"])

    def test_ranking_setting_change(self):
        with mock.patch.object(ranking, "ONE_OLDER", 0.6):
            self.assertEqual(self.changes(), ["ranking settings changed: age_weights"])

    def test_catalogue_correction_counts_but_verification_does_not(self):
        ReferenceMilestone.objects.update(verified=True)
        self.assertEqual(self.changes(), [])
        ReferenceMilestone.objects.filter(milestone_key="CDC-02M-MO-01").update(
            expected_age_months=3
        )
        self.assertEqual(
            self.changes(), ["reference milestone catalogue changed: sha256"]
        )

    def test_re_embedding_with_another_model(self):
        ActivityEmbedding.objects.filter(activity__activity_id="ACT-0951").update(
            vector=b"\x00" * 16
        )
        self.assertEqual(self.changes(), ["embeddings changed: vectors_sha256"])

        other = FakeEncoder()
        other.name = "other-model"
        embeddings.set_encoder(other)
        changes = "\n".join(self.changes())
        self.assertIn("model_name", changes)
        self.assertIn("embedded_activities", changes)

    def test_sheet_rows_change(self):
        self.assertEqual(
            self.changes(rows={"H01": ["ACT-0956", "ACT-0951"]}),
            ["the sheet's (child_id, activity_id) rows were added or removed"],
        )


class EvaluateProvenanceAndGuardTests(HeldOutCommandTestCase):
    def evaluate(self):
        out = StringIO()
        call_command(
            "evaluate_alpha_grid",
            "--labels",
            str(self.path),
            stdout=out,
            stderr=StringIO(),
        )
        return out.getvalue()

    def label_all(self, blank=()):
        rows = self.read()
        for i, row in enumerate(rows):
            if i in blank:
                continue
            row["relevance"] = "2" if row["activity_id"] == "ACT-0951" else "0"
        self.write(rows)
        return rows

    def test_export_writes_a_sidecar_that_matches(self):
        self.publish()
        output = self.export()
        sidecar = provenance.sidecar_path(self.path)
        self.assertIn(f"Wrote the provenance sidecar to {sidecar}", output)
        self.assertTrue(sidecar.exists())
        self.label_all()
        self.assertIn("Matches the state the sheet was generated from", self.evaluate())

    def test_warns_when_an_activity_changed_after_export(self):
        self.publish()
        self.export()
        self.label_all()
        DevelopmentalActivity.objects.filter(activity_id="ACT-0953").update(
            activity_name="Renamed"
        )
        output = self.evaluate()
        self.assertIn("WARNING: the state differs", output)
        self.assertIn("activity content changed: ACT-0953", output)

    def test_warns_when_the_sidecar_is_missing(self):
        self.publish()
        self.export()
        provenance.sidecar_path(self.path).unlink()
        self.assertIn("WARNING: no provenance sidecar", self.evaluate())

    def test_fully_labelled_sheet_prints_test_results(self):
        self.publish()
        self.export()
        self.label_all()
        output = self.evaluate()
        self.assertIn("Top-5 candidates with no label, per ranking:", output)
        self.assertIn("| alpha 0.5 | 0 | 0 | 0 | 0 |", output)
        self.assertIn("Test set: alpha", output)
        self.assertNotIn("withheld", output)
        self.assertNotIn("Provisional", output)

    def test_one_blank_test_row_withholds_the_test_numbers(self):
        self.publish()
        self.export()
        rows = self.read()
        first_test = next(i for i, r in enumerate(rows) if r["split"] == "test")
        self.label_all(blank={first_test})

        output = self.evaluate()
        self.assertIn("Chosen alpha", output)
        self.assertNotIn("Provisional", output)  # every tune row is labelled
        self.assertIn("Test set: withheld", output)
        self.assertNotIn("Test set: alpha", output)
        self.assertNotIn("Content-gap child", output)
        self.assertIn("Agreement between raters", output)

    def test_blank_tune_row_makes_the_choice_provisional(self):
        self.publish()
        self.export()
        rows = self.read()
        first_tune = next(
            i
            for i, r in enumerate(rows)
            if r["split"] == "tune" and r["activity_id"] != "ACT-0951"
        )
        self.label_all(blank={first_tune})
        output = self.evaluate()
        self.assertIn("Provisional:", output)
        self.assertIn("Test set: withheld", output)


class SheetRowsHashTests(SimpleTestCase):
    def test_order_does_not_matter(self):
        self.assertEqual(
            provenance.sheet_rows_sha256({"H01": ["A", "B"], "H02": ["C"]}),
            provenance.sheet_rows_sha256({"H02": ["C"], "H01": ["B", "A"]}),
        )


class GeneratedSidecarTests(SimpleTestCase):
    """The committed sidecar belongs to the committed sheet."""

    def test_committed_sidecar_rows_match_the_committed_sheet(self):
        sheet = Path(settings.BASE_DIR).parent / "data/evaluation/heldout_labels.csv"
        sidecar = provenance.sidecar_path(sheet)
        if not sheet.exists() or not sidecar.exists():
            self.skipTest("held-out sheet not generated")
        rows = {}
        with open(sheet, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows.setdefault(row["child_id"], []).append(row["activity_id"])
        self.assertEqual(
            provenance.read(sidecar)["sheet_rows_sha256"],
            provenance.sheet_rows_sha256(rows),
        )


class CheckProvenanceFlagTests(HeldOutCommandTestCase):
    def check(self):
        out = StringIO()
        call_command(
            "evaluate_alpha_grid",
            "--labels",
            str(self.path),
            "--check-provenance",
            stdout=out,
            stderr=StringIO(),
        )
        return out.getvalue()

    def test_passes_and_prints_only_the_check(self):
        self.publish()
        self.export()
        output = self.check()
        self.assertIn("Matches the state the sheet was generated from", output)
        self.assertNotIn("Tune set", output)
        self.assertNotIn("Labelling status", output)

    def test_fails_when_anything_changed(self):
        self.publish()
        self.export()
        DevelopmentalActivity.objects.filter(activity_id="ACT-0951").update(
            description="Changed."
        )
        with self.assertRaisesMessage(CommandError, "Provenance check failed"):
            self.check()

    def test_fails_without_a_sidecar(self):
        self.publish()
        self.export()
        provenance.sidecar_path(self.path).unlink()
        with self.assertRaisesMessage(CommandError, "Provenance check failed"):
            self.check()
