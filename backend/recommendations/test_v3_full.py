"""Tests for the full v3 evaluation (#270) and the explanation check."""

import csv
import json
import tempfile
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from activities.models import DevelopmentalActivity

from . import heldout
from .evaluation import HELDOUT_COLUMNS
from .explanation_check import check, named_in, sentences
from .management.commands.evaluate_v3_full import strict_mean
from .management.commands.export_heldout_labels import COLUMNS as SHEET_COLUMNS
from .models import Recommendation
from .test_heldout import HeldOutCommandTestCase

RAW_FILES = (
    "v3_alpha_grid.csv",
    "v3_test_results.csv",
    "v3_per_profile_by_rater.csv",
    "v3_rater_agreement.json",
    "v3_confusion.csv",
    "v3_beyond_accuracy.csv",
    "v3_rank_grade_matrix.csv",
    "v3_ablation.csv",
    "v3_explanation_check.json",
    "v3_ungraded_pairs.csv",
)


class HelperTests(SimpleTestCase):
    def test_a_mean_with_an_unknown_value_is_unknown(self):
        self.assertIsNone(strict_mean([0.5, None, 1.0]))
        self.assertIsNone(strict_mean([]))
        self.assertEqual(strict_mean([0.5, 1.0]), 0.75)

    def test_sentences_split_at_full_stops_only(self):
        text = (
            "You recorded “Says ‘mama’” as not yet; most children do this by "
            "12 months. It's designed for children aged 6–12 months, your child's "
            "age group. Its aim is to help your baby talk."
        )
        self.assertEqual(len(sentences(text)), 3)

    def test_named_items_are_read_back(self):
        milestones, concerns, interests = named_in(
            "You recorded “Waves bye-bye” as not yet; most children do this by "
            "9 months. You said you'd like support with movement and that your "
            "child enjoys music, which points us towards activities for movement."
        )
        self.assertEqual(milestones, ["Waves bye-bye"])
        self.assertEqual(concerns, ["Motor"])
        self.assertEqual(interests, ["music"])

    def test_check_counts_items_not_in_the_profile_and_scores(self):
        child = SimpleNamespace(
            milestones=SimpleNamespace(values_list=lambda *a, **k: ["Waves bye-bye"]),
            interests=["Music"],
            concerns=["Motor"],
        )
        result = check(
            child,
            [
                "You recorded “Waves bye-bye” as not yet; most children do this "
                "by 9 months.",
                "You recorded “Claps” as not yet; most children do this by 9 "
                "months. Its score is 0.82.",
            ],
        )
        self.assertEqual(result["explanations"], 2)
        self.assertEqual(result["not_in_profile"], 1)  # "Claps"
        self.assertEqual(result["showing_a_score"], 1)
        self.assertEqual(result["max_sentences"], 2)


class V3FullCommandTestCase(HeldOutCommandTestCase):
    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.raw = Path(tmp.name) / "raw"

    def run_command(self):
        out = StringIO()
        call_command(
            "evaluate_v3_full",
            "--labels",
            str(self.path),
            "--extra-labels",
            str(self.path.with_name("none.csv")),
            "--raw-dir",
            str(self.raw),
            stdout=out,
            stderr=StringIO(),
        )
        return out.getvalue()

    def grade(self, keep=lambda child_id, activity_id: True):
        """A sheet grading every published activity (or those `keep` allows)."""
        ids = DevelopmentalActivity.objects.published().values_list(
            "activity_id", flat=True
        )
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HELDOUT_COLUMNS)
            writer.writeheader()
            for child in heldout.HELDOUT_CHILDREN:
                for activity_id in ids:
                    if keep(child.child_id, activity_id):
                        writer.writerow(
                            {
                                "child_id": child.child_id,
                                "split": child.split,
                                "activity_id": activity_id,
                                "relevance": int(activity_id[-1]) % 3,
                                "relevance_rater2": (int(activity_id[-1]) + 1) % 3,
                            }
                        )


class EvaluateV3FullTests(V3FullCommandTestCase):
    @override_settings(RETRIEVAL_BETA=1.0)
    def test_refuses_to_run_at_beta_1(self):
        self.publish()
        self.grade()
        with self.assertRaisesMessage(CommandError, "RETRIEVAL_BETA is 1"):
            self.run_command()

    def test_fully_graded_reports_every_section_writes_raw_and_stores_nothing(self):
        self.publish()
        self.grade()
        before = Recommendation.objects.count(), get_user_model().objects.count()
        output = self.run_command()
        self.assertEqual(
            (Recommendation.objects.count(), get_user_model().objects.count()), before
        )
        for text in (
            "Label coverage",
            "1. Alpha grid",
            "chosen alpha",
            "2. Test set at alpha 0.7",
            "3. Per-profile nDCG@5",
            "4. Agreement between raters",
            "Cohen's kappa, quadratic",
            "5. Test: alpha 0.7 against SBERT only",
            "6. Beyond accuracy",
            "7. Ablation",
            "8. Explanation check",
            "Ungraded pairs across all settings: 0",
        ):
            self.assertIn(text, output)
        self.assertNotIn("UNKNOWN |", output)
        for name in RAW_FILES:
            self.assertTrue((self.raw / name).exists(), name)
        check_ = json.loads((self.raw / "v3_explanation_check.json").read_text())
        self.assertEqual(check_["profiles"], len(heldout.HELDOUT_CHILDREN))
        self.assertEqual(check_["items_not_in_stored_profile"], 0)
        self.assertEqual(check_["explanations_showing_a_score"], 0)

    def test_ungraded_pairs_are_unknown_and_listed_without_grades(self):
        self.publish()
        self.grade(keep=lambda child_id, activity_id: activity_id != "ACT-0957")
        output = self.run_command()
        self.assertIn("UNKNOWN", output)
        with open(
            self.raw / "v3_ungraded_pairs.csv", newline="", encoding="utf-8"
        ) as f:
            rows = list(csv.DictReader(f))
        self.assertTrue(rows)
        self.assertEqual({r["activity_id"] for r in rows}, {"ACT-0957"})
        self.assertEqual({r["relevance"] for r in rows}, {""})
        self.assertEqual({r["relevance_rater2"] for r in rows}, {""})
        self.assertEqual({r["missing_for"] for r in rows}, {"researcher and nurse"})


class ExportUngradedTests(V3FullCommandTestCase):
    def export(self, *extra):
        out = StringIO()
        sheet = self.raw.parent / "v3_extra_blank.csv"
        call_command(
            "evaluate_v3_full",
            "--labels",
            str(self.path),
            "--extra-labels",
            "--export-ungraded",
            str(sheet),
            *extra,
            stdout=out,
            stderr=StringIO(),
        )
        return sheet, out.getvalue()

    def test_the_sheet_is_blind_and_has_only_the_ungraded_pairs(self):
        self.publish()
        self.grade(keep=lambda child_id, activity_id: activity_id != "ACT-0957")
        sheet, output = self.export()
        with open(sheet, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertEqual(reader.fieldnames, list(SHEET_COLUMNS))
        self.assertTrue(rows)
        self.assertEqual({r["activity_id"] for r in rows}, {"ACT-0957"})
        self.assertEqual({r["relevance"] for r in rows}, {""})
        self.assertEqual({r["relevance_rater2"] for r in rows}, {""})
        # Nothing reveals which setting or rank produced a pair.
        for column in ("settings", "rank", "alpha", "score"):
            self.assertNotIn(column, reader.fieldnames)
        self.assertIn(f"Wrote {len(rows)} ungraded pair(s)", output)

    def test_an_existing_sheet_is_not_overwritten_without_force(self):
        self.publish()
        self.grade()
        sheet = self.raw.parent / "v3_extra_blank.csv"
        sheet.parent.mkdir(parents=True, exist_ok=True)
        sheet.write_text("keep me", encoding="utf-8")
        with self.assertRaisesMessage(CommandError, "already exists"):
            self.export()
        self.assertEqual(sheet.read_text(encoding="utf-8"), "keep me")
        self.export("--force")
        self.assertNotEqual(sheet.read_text(encoding="utf-8"), "keep me")
