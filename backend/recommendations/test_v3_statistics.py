"""Tests for the v3 significance tests (#268)."""

import csv
from io import StringIO
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from activities.models import DevelopmentalActivity

from . import heldout
from .evaluation import HELDOUT_COLUMNS
from .management.commands.evaluate_v3_statistics import merge_grades, ungraded
from .models import Recommendation
from .test_heldout import HeldOutCommandTestCase


class MergeGradesTests(SimpleTestCase):
    def sheet(self, relevance=None, rater2=None):
        return SimpleNamespace(relevance=relevance or {}, rater2=rater2 or {})

    def test_sheets_are_merged_per_rater(self):
        sheets = [
            ("a.csv", self.sheet({"H01": {"A": 2}}, {"H01": {"A": 1}})),
            ("b.csv", self.sheet({"H01": {"B": 0}}, {"H01": {"B": 0}})),
        ]
        self.assertEqual(merge_grades(sheets, "relevance"), {"H01": {"A": 2, "B": 0}})
        self.assertEqual(merge_grades(sheets, "rater2"), {"H01": {"A": 1, "B": 0}})

    def test_a_pair_graded_differently_is_an_error(self):
        sheets = [
            ("a.csv", self.sheet({"H01": {"A": 2}})),
            ("b.csv", self.sheet({"H01": {"A": 1}})),
        ]
        with self.assertRaisesMessage(CommandError, "graded 2 in one sheet and 1"):
            merge_grades(sheets, "relevance")

    def test_ungraded_counts_top_k_slots_only(self):
        rankings = {"H01": {"m": ["A", "B", "C", "D", "E", "F"]}}
        grades = {"H01": {"A": 1, "B": 0, "C": 2}}
        self.assertEqual(ungraded(rankings, grades, ["m"]), 2)  # D and E, not F


class EvaluateV3StatisticsTests(HeldOutCommandTestCase):
    def run_command(self):
        out = StringIO()
        call_command(
            "evaluate_v3_statistics",
            "--labels",
            str(self.path),
            "--extra-labels",
            str(self.path.with_name("none.csv")),
            stdout=out,
            stderr=StringIO(),
        )
        return out.getvalue()

    def grade_everything(self, second_rater=True):
        """A sheet grading every published activity for every child."""
        ids = DevelopmentalActivity.objects.published().values_list(
            "activity_id", flat=True
        )
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HELDOUT_COLUMNS)
            writer.writeheader()
            for child in heldout.HELDOUT_CHILDREN:
                for activity_id in ids:
                    writer.writerow(
                        {
                            "child_id": child.child_id,
                            "split": child.split,
                            "activity_id": activity_id,
                            "relevance": int(activity_id[-1]) % 3,
                            "relevance_rater2": (
                                (int(activity_id[-1]) + 1) % 3 if second_rater else ""
                            ),
                        }
                    )

    def test_refuses_ungraded_rankings(self):
        self.publish()
        self.export()  # the exported sheet has no grades
        with self.assertRaisesMessage(CommandError, "no label"):
            self.run_command()

    @override_settings(RETRIEVAL_BETA=1.0)
    def test_refuses_to_run_at_beta_1(self):
        self.publish()
        self.grade_everything()
        with self.assertRaisesMessage(CommandError, "RETRIEVAL_BETA is 1"):
            self.run_command()

    def test_reports_both_comparisons_for_both_raters_and_stores_nothing(self):
        self.publish()
        self.grade_everything()
        before = Recommendation.objects.count(), get_user_model().objects.count()
        output = self.run_command()
        self.assertEqual(
            (Recommendation.objects.count(), get_user_model().objects.count()), before
        )
        for text in (
            "v3: retrieval beta 0.25",
            "Paired nDCG@5, researcher's grades",
            "Paired nDCG@5, nurse's grades",
            "SBERT only (beta 1, similarity only)",
            "v2 system (beta 1, alpha 0.7)",
            "Test (primary)",
            "95% CI",
            "aren't changed",
        ):
            self.assertIn(text, output)

    def test_without_second_rater_grades_their_section_is_withheld(self):
        self.publish()
        self.grade_everything(second_rater=False)
        output = self.run_command()
        self.assertIn("no grade from the nurse", output)
        self.assertIn("Paired nDCG@5, researcher's grades", output)
