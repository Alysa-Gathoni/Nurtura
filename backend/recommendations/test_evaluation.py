"""Tests for relevance labels, metrics and the labelling template (#36)."""

import csv
import math
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from activities.choices import AgeRange, ContentStatus
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields

from .evaluation import (
    LabelError,
    evaluate,
    load_labels,
    ndcg_at_k,
    precision_at_k,
)
from .samples import SAMPLE_PROFILES, SAMPLES_BY_KEY


class MetricTests(SimpleTestCase):
    def test_precision_counts_relevance_of_one_or_more(self):
        relevance = {"a": 2, "b": 1, "c": 0}
        self.assertEqual(precision_at_k(["a", "c", "b", "x"], relevance, 4), 0.5)
        # Unlabelled ("x") counts as not relevant; short lists still divide by k.
        self.assertEqual(precision_at_k(["a"], relevance, 5), 0.2)

    def test_ndcg_hand_computed(self):
        relevance = {"a": 2, "b": 1, "c": 0}
        # DCG of [b, a, c] = (2^1-1)/log2(2) + (2^2-1)/log2(3) + 0
        # Ideal [a, b, c]  = (2^2-1)/log2(2) + (2^1-1)/log2(3) + 0
        expected = (1 + 3 / math.log2(3)) / (3 + 1 / math.log2(3))
        self.assertAlmostEqual(ndcg_at_k(["b", "a", "c"], relevance, 3), expected)
        self.assertAlmostEqual(expected, 0.7967, places=4)

    def test_ndcg_perfect_and_worst(self):
        relevance = {"a": 2, "b": 1, "c": 0, "d": 0}
        self.assertAlmostEqual(ndcg_at_k(["a", "b", "c"], relevance, 3), 1.0)
        self.assertEqual(ndcg_at_k(["c", "d"], relevance, 2), 0.0)

    def test_ndcg_ideal_uses_all_labels_not_just_retrieved(self):
        # A relevant activity that wasn't ranked still sets the ideal.
        relevance = {"a": 2, "b": 2}
        self.assertLess(ndcg_at_k(["a", "x"], relevance, 2), 1.0)

    def test_ndcg_undefined_without_relevant_labels(self):
        self.assertIsNone(ndcg_at_k(["a"], {"a": 0}, 5))
        self.assertIsNone(ndcg_at_k(["a"], {}, 5))


class EvaluateTests(SimpleTestCase):
    def test_means_and_unlabelled_counts(self):
        labels = {
            "language-delay": {"L1": 2, "L2": 1, "M1": 0},
            "motor-delay": {"M1": 0, "L1": 0},  # nothing relevant: no nDCG
        }
        rankings = {
            "language-delay": ["L1", "L2", "X"],
            "motor-delay": ["M1", "L1", "Y"],
            "cognitive-delay": ["C1"],  # no labels at all
        }
        result = evaluate(rankings, labels, k=3)

        by_key = {s.sample_key: s for s in result.samples}
        self.assertAlmostEqual(by_key["language-delay"].precision, 2 / 3)
        self.assertAlmostEqual(by_key["language-delay"].ndcg, 1.0)
        self.assertIsNone(by_key["motor-delay"].ndcg)
        self.assertAlmostEqual(result.mean_precision, (2 / 3 + 0 + 0) / 3)
        self.assertAlmostEqual(result.mean_ndcg, 1.0)  # only defined samples
        self.assertEqual(result.unlabelled_in_top_k, 1 + 1 + 1)
        self.assertEqual(result.unlabelled_samples, ["cognitive-delay"])

    def test_k_must_be_positive(self):
        with self.assertRaises(ValueError):
            evaluate({}, {}, k=0)


class LoadLabelsTests(SimpleTestCase):
    def write(self, text):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "labels.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_reads_labels_and_skips_empty_relevance(self):
        path = self.write(
            "sample_key,activity_id,relevance,notes\n"
            "language-delay,ACT-0001,2,good fit\n"
            "language-delay,ACT-0002,0,\n"
            "language-delay,ACT-0003,,\n"
            "motor-delay,ACT-0001,1,\n"
        )
        self.assertEqual(
            load_labels(path),
            {
                "language-delay": {"ACT-0001": 2, "ACT-0002": 0},
                "motor-delay": {"ACT-0001": 1},
            },
        )

    def test_reports_every_problem(self):
        path = self.write(
            "sample_key,activity_id,relevance\n"
            "language-delay,ACT-0001,3\n"
            "no-such-sample,ACT-0001,1\n"
            "motor-delay,,1\n"
            "motor-delay,ACT-0002,yes\n"
            "language-delay,ACT-0004,1\n"
            "language-delay,ACT-0004,2\n"
        )
        with self.assertRaises(LabelError) as ctx:
            load_labels(path)
        problems = "\n".join(ctx.exception.problems)
        self.assertEqual(len(ctx.exception.problems), 5)
        self.assertIn("line 2: relevance '3' must be 0, 1 or 2", problems)
        self.assertIn("line 3: unknown sample_key 'no-such-sample'", problems)
        self.assertIn("line 4: missing activity_id", problems)
        self.assertIn("line 5: relevance 'yes'", problems)
        self.assertIn("line 7: duplicate label", problems)

    def test_missing_columns_or_file(self):
        with self.assertRaises(LabelError) as ctx:
            load_labels(self.write("sample_key,activity_id\nlanguage-delay,ACT-0001\n"))
        self.assertIn("missing column(s): relevance", ctx.exception.problems[0])
        with self.assertRaises(LabelError):
            load_labels(Path(tempfile.gettempdir()) / "definitely-missing.csv")


class SampleKeyTests(SimpleTestCase):
    def test_keys_are_unique_and_stable(self):
        self.assertEqual(len(SAMPLES_BY_KEY), len(SAMPLE_PROFILES))
        self.assertEqual(
            list(SAMPLES_BY_KEY),
            [
                "language-delay",
                "motor-delay",
                "cognitive-delay",
                "socio-emotional-delay",
                "sensory-concern",
                "language-and-motor-delay",
                "expecting-parent",
            ],
        )


class ExportTemplateTests(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "template.csv"
        DevelopmentalActivity.objects.create(
            **activity_fields(activity_id="ACT-0001")  # Draft
        )
        DevelopmentalActivity.objects.create(
            **activity_fields(
                activity_id="ACT-0002",
                activity_name="Peekaboo",
                content_status=ContentStatus.PUBLISHED,
            )
        )
        DevelopmentalActivity.objects.create(
            **activity_fields(
                activity_id="ACT-0003",
                activity_name="Talk to Your Bump",
                age_range=AgeRange.PRENATAL,
            )
        )

    def export(self, *args):
        out = StringIO()
        call_command(
            "export_relevance_template", "--output", str(self.path), *args, stdout=out
        )
        return out.getvalue()

    def test_one_row_per_sample_and_eligible_activity(self):
        self.assertIn("Wrote 13 rows", self.export())  # 6 x 2 + 1
        rows = list(csv.DictReader(open(self.path, encoding="utf-8")))
        postnatal_samples = [s for s in SAMPLE_PROFILES if s.age_months >= 0]
        self.assertEqual(len(rows), len(postnatal_samples) * 2 + 1)

        expecting = [r for r in rows if r["sample_key"] == "expecting-parent"]
        self.assertEqual([r["activity_id"] for r in expecting], ["ACT-0003"])
        language = [r for r in rows if r["sample_key"] == "language-delay"]
        self.assertEqual([r["activity_id"] for r in language], ["ACT-0001", "ACT-0002"])
        self.assertEqual(
            {r["content_status"] for r in language}, {"Draft", "Published"}
        )
        self.assertTrue(all(r["relevance"] == "" for r in rows))
        self.assertEqual(load_labels(self.path), {})

    def test_refuses_to_overwrite_without_force(self):
        self.export()
        with self.assertRaisesMessage(CommandError, "already exists"):
            self.export()
        self.assertIn("Wrote", self.export("--force"))
