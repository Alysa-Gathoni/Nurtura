"""Tests for the diversity, novelty, coverage and personalisation measures (#199)."""

import math
from io import StringIO

import numpy as np
from django.core.management import call_command
from django.test import SimpleTestCase

from . import beyond_accuracy as ba
from .test_heldout import HeldOutCommandTestCase


class MeasureTests(SimpleTestCase):
    def test_intra_list_diversity(self):
        vectors = {
            "a": np.array([1.0, 0.0]),
            "b": np.array([1.0, 0.0]),
            "c": np.array([0.0, 1.0]),
        }
        self.assertEqual(ba.intra_list_diversity(["a", "b"], vectors), 0.0)
        # Pairs: a-b 0, a-c 1, b-c 1.
        self.assertAlmostEqual(ba.intra_list_diversity(["a", "b", "c"], vectors), 2 / 3)
        self.assertIsNone(ba.intra_list_diversity(["a"], vectors))

    def test_area_diversity(self):
        areas = {"a": "Motor", "b": "Motor", "c": "Language", "d": "Sensory"}
        self.assertEqual(ba.area_diversity(["a", "b"], areas), 0.5)
        self.assertEqual(ba.area_diversity(["a", "c", "d"], areas), 1.0)
        self.assertIsNone(ba.area_diversity([], areas))

    def test_catalogue_coverage(self):
        self.assertEqual(ba.catalogue_coverage([["a", "b"], ["b", "c"]], 6), 0.5)
        self.assertIsNone(ba.catalogue_coverage([["a"]], 0))

    def test_novelty(self):
        # Everyone sees "a": no surprise.
        self.assertEqual(ba.novelty([["a"], ["a"]]), 0.0)
        # Each of four lists has its own activity: log2(4) bits.
        self.assertAlmostEqual(ba.novelty([["a"], ["b"], ["c"], ["d"]]), 2.0)
        # "a" in 2 of 2 lists (0 bits), "b" in 1 of 2 (1 bit): 3 slots.
        self.assertAlmostEqual(ba.novelty([["a", "b"], ["a"]]), 1 / 3)
        self.assertIsNone(ba.novelty([]))

    def test_personalisation(self):
        self.assertEqual(ba.personalisation([["a", "b"], ["a", "b"]]), 0.0)
        self.assertEqual(ba.personalisation([["a", "b"], ["c", "d"]]), 1.0)
        self.assertEqual(ba.personalisation([["a", "b"], ["a", "c"]]), 0.5)
        self.assertIsNone(ba.personalisation([["a"]]))
        self.assertFalse(math.isnan(ba.personalisation([["a"], ["b"], ["a"]])))


class EvaluateBeyondAccuracyTests(HeldOutCommandTestCase):
    def test_reports_every_ranking(self):
        self.publish()
        out = StringIO()
        call_command("evaluate_beyond_accuracy", stdout=out, stderr=StringIO())
        output = out.getvalue()
        for text in (
            "Top 5 of 20 held-out children",
            "SBERT-only",
            "alpha 0.0",
            "alpha 0.7",
            "alpha 1.0",
            "Intra-list diversity",
            "Personalisation (same age band)",
        ):
            self.assertIn(text, output)
