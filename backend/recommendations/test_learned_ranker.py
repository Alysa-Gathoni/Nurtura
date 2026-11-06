"""Tests for the learned-ranker experiment (#183)."""

import csv
from io import StringIO

import numpy as np
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from . import learned_ranker
from .management.commands.export_heldout_labels import COLUMNS
from .test_heldout import HeldOutCommandTestCase


class LearnedRankerUnitTests(SimpleTestCase):
    def test_ranks_by_expected_gain(self):
        # Grade rises with the first feature.
        X = np.array([[i, 0, 0, 1, 0, 0] for i in range(9)], dtype=float)
        y = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2])
        model = learned_ranker.fit(X, y)
        child = learned_ranker.ChildCandidates(
            features={"low": X[0], "mid": X[4], "high": X[8]},
            sbert=[],
            hybrid=[],
            activities={},
        )
        self.assertEqual(learned_ranker.rank(model, child), ["high", "mid", "low"])
        weights = learned_ranker.weights(model)
        self.assertEqual(set(weights), set(learned_ranker.FEATURES))
        self.assertGreater(weights["similarity"], 0)


class EvaluateLearnedRankerTests(HeldOutCommandTestCase):
    def run_command(self, *args):
        out = StringIO()
        call_command(
            "evaluate_learned_ranker",
            "--labels",
            str(self.path),
            *args,
            stdout=out,
            stderr=StringIO(),
        )
        return out.getvalue()

    def label(self, path, rule):
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            row["relevance"] = rule(row)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def grade(row):
        return (
            "2"
            if row["activity_id"] in ("ACT-0951", "ACT-0957")
            else ("1" if int(row["activity_id"][-1]) % 2 else "0")
        )

    def test_withholds_results_until_every_top_5_is_labelled(self):
        self.publish()
        self.export()
        self.label(self.path, self.grade)
        extra = self.path.with_name("extra.csv")

        first = self.run_command("--export-unlabelled", str(extra))
        if "Provisional" in first:
            self.assertNotIn("Test set (8 children)", first)
            self.assertNotIn("Decision rule", first)
            self.label(extra, self.grade)
            final = self.run_command("--extra-labels", str(extra))
        else:
            final = first

        for text in (
            "Trained on",
            "Tune set, leave one child out (11 children)",
            "Test set (8 children)",
            "Content-gap child (reported separately) (1 children)",
            "Learned weights",
            "Decision rule",
            "SBERT-only",
            "alpha 0.7",
            "Learned ranker",
        ):
            self.assertIn(text, final)

    def test_conflicting_grades_are_refused(self):
        self.publish()
        self.export()
        self.label(self.path, lambda r: "2")
        extra = self.path.with_name("extra.csv")
        with open(self.path, newline="", encoding="utf-8") as f:
            first = next(csv.DictReader(f))
        with open(extra, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerow({**first, "relevance": "0"})
        with self.assertRaisesMessage(CommandError, "graded 2 in one sheet and 0"):
            self.run_command("--extra-labels", str(extra))
