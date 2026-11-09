"""Tests for the held-out statistics and age-weight sensitivity (#196)."""

import csv
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from activities.choices import AgeRange

from . import ranking, statistics
from .management.commands.evaluate_statistics import AGE_SCENARIOS, age_weights
from .management.commands.export_heldout_labels import COLUMNS
from .test_heldout import HeldOutCommandTestCase


class PairedStatisticsTests(SimpleTestCase):
    def test_bootstrap_interval_contains_the_mean_and_is_reproducible(self):
        diffs = [0.1, 0.3, -0.05, 0.2, 0.25, 0.0, 0.15, 0.4]
        low, high = statistics.bootstrap_ci(diffs)
        mean = sum(diffs) / len(diffs)
        self.assertLess(low, mean)
        self.assertGreater(high, mean)
        self.assertEqual((low, high), statistics.bootstrap_ci(diffs))

    def test_constant_differences_give_a_point_interval(self):
        self.assertEqual(statistics.bootstrap_ci([0.2] * 5), (0.2, 0.2))

    def test_wilcoxon_drops_ties(self):
        n, w, p = statistics.wilcoxon([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
        self.assertEqual(n, 6)
        self.assertEqual(w, 0)
        self.assertAlmostEqual(p, 2 / 64)  # exact: all six signs positive

    def test_wilcoxon_with_no_differences_is_not_applicable(self):
        self.assertEqual(statistics.wilcoxon([0.0, 0.0]), (0, None, None))

    def test_paired_counts_and_skips_missing_scores(self):
        result = statistics.paired([0.9, 0.5, None, 0.4], [0.5, 0.5, 0.7, 0.6])
        self.assertEqual(result.n, 3)
        self.assertEqual((result.improved, result.tied, result.worse), (1, 1, 1))
        self.assertAlmostEqual(result.mean_diff, (0.4 + 0.0 - 0.2) / 3)
        self.assertEqual(result.wilcoxon_n, 2)

    def test_no_pairs_is_an_error(self):
        with self.assertRaises(ValueError):
            statistics.paired([None], [0.5])


class AgeScenarioTests(SimpleTestCase):
    def test_the_first_scenario_is_the_current_weights(self):
        _, weights = AGE_SCENARIOS[0]
        self.assertEqual(
            weights,
            (
                ranking.SAME_BRACKET,
                ranking.ONE_YOUNGER,
                ranking.ONE_OLDER,
                ranking.TWO_AWAY,
                ranking.FURTHER,
            ),
        )

    def test_weights_are_replaced_and_restored(self):
        older = AgeRange.MONTHS_12_18  # one bracket older than a 9-month-old
        self.assertEqual(ranking.age_weight(9, older), 0.5)
        with age_weights((1.0, 0.2, 0.3, 0.4, 0.5)):
            self.assertEqual(ranking.age_weight(9, older), 0.3)
        self.assertEqual(ranking.age_weight(9, older), 0.5)


class EvaluateStatisticsTests(HeldOutCommandTestCase):
    def run_command(self):
        out = StringIO()
        call_command(
            "evaluate_statistics",
            "--labels",
            str(self.path),
            stdout=out,
            stderr=StringIO(),
        )
        return out.getvalue()

    def label_every_row(self):
        with open(self.path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            row["relevance"] = str(int(row["activity_id"][-1]) % 3)
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    def test_refuses_unlabelled_rankings(self):
        self.publish()
        self.export()
        with self.assertRaisesMessage(CommandError, "no label"):
            self.run_command()

    def test_reports_paired_statistics_and_sensitivity(self):
        self.publish()
        self.export()
        self.label_every_row()
        output = self.run_command()
        for text in (
            "Paired nDCG@5: alpha 0.7 against each",
            "Test (primary)",
            "SBERT-only",
            "95% CI",
            "Age-weight sensitivity at alpha 0.7",
            *(name for name, _ in AGE_SCENARIOS),
        ):
            self.assertIn(text, output)
