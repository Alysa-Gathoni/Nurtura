"""Tests for the held-out set, alpha selection and the grid-search commands (#37)."""

import csv
import tempfile
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from activities.choices import AgeRange, ContentStatus, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from profiles.models import ChildProfile, ReferenceMilestone
from profiles.rules import build_profile

from . import embeddings, heldout
from .evaluation import (
    LabelError,
    compare,
    load_heldout_labels,
    precision_at_k,
    rater_agreement,
    select_alpha,
)
from .management.commands.export_heldout_labels import COLUMNS
from .test_embeddings import FakeEncoder
from .test_spot_check import DOMAIN_ACTIVITIES

User = get_user_model()
ALL_DOMAINS = {d.value for d in Domain}


class HeldOutDefinitionTests(SimpleTestCase):
    def test_twenty_children_with_unique_ids(self):
        ids = [c.child_id for c in heldout.HELDOUT_CHILDREN]
        self.assertEqual(len(ids), 20)
        self.assertEqual(len(set(ids)), 20)
        self.assertEqual(set(ids), set(heldout.HELDOUT_BY_ID))

    def test_split_is_11_tune_8_test_1_gap(self):
        counts = {s: 0 for s in heldout.SPLITS}
        for child in heldout.HELDOUT_CHILDREN:
            counts[child.split] += 1
        self.assertEqual(counts, {"tune": 11, "test": 8, "gap": 1})

    def test_only_the_content_gap_child_is_in_the_gap_split(self):
        gap = [c.child_id for c in heldout.HELDOUT_CHILDREN if c.content_gap]
        self.assertEqual(gap, ["H17"])
        self.assertEqual(heldout.HELDOUT_BY_ID["H17"].split, "gap")

    def test_stored_split_matches_the_stratified_procedure(self):
        assignment = heldout.stratified_split(heldout.HELDOUT_CHILDREN)
        for child in heldout.HELDOUT_CHILDREN:
            if child.split != "gap":
                with self.subTest(child=child.child_id):
                    self.assertEqual(assignment[child.child_id], child.split)

    def test_no_overlap_with_the_development_samples(self):
        from .samples import SAMPLES_BY_KEY

        self.assertFalse(set(heldout.HELDOUT_BY_ID) & set(SAMPLES_BY_KEY))

    def test_alpha_grid_and_pool_depth(self):
        self.assertEqual(
            [round(a, 1) for a in heldout.ALPHAS],
            [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        )
        self.assertEqual(heldout.POOL_DEPTH, 5)


class PoolTests(SimpleTestCase):
    def test_pool_is_the_union_of_each_top_k(self):
        rankings = {
            heldout.BASELINE: ["A", "B", "C", "D"],
            0.0: ["B", "A", "E", "F"],
            1.0: ["G", "A", "B", "H"],
        }
        self.assertEqual(heldout.pool(rankings, depth=2), ["A", "B", "G"])
        self.assertEqual(heldout.pool(rankings, depth=3), ["A", "B", "C", "E", "G"])

    def test_shuffle_is_deterministic_per_child_and_a_permutation(self):
        ids = [f"ACT-{i:04d}" for i in range(12)]
        first = heldout.shuffled(ids, "H01")
        self.assertEqual(first, heldout.shuffled(list(reversed(ids)), "H01"))
        self.assertEqual(sorted(first), ids)
        self.assertNotEqual(first, ids)


class SelectAlphaTests(SimpleTestCase):
    def test_single_best(self):
        curve = {0.0: 0.5, 0.5: 0.8, 1.0: 0.6}
        self.assertEqual(select_alpha(curve), (0.5, [0.5]))

    def test_middle_of_the_qualifying_range(self):
        curve = {0.0: 0.5, 0.2: 0.79, 0.3: 0.80, 0.4: 0.785, 0.6: 0.785, 0.7: 0.6}
        chosen, qualifying = select_alpha(curve)
        self.assertEqual(qualifying, [0.2, 0.3, 0.4, 0.6])
        self.assertEqual(chosen, 0.4)  # midpoint 0.4

    def test_tie_goes_to_the_lower_alpha(self):
        curve = {0.1: 0.8, 0.2: 0.8, 0.5: 0.4}
        self.assertEqual(select_alpha(curve)[0], 0.1)  # midpoint 0.15

    def test_chosen_alpha_always_qualifies(self):
        # Midpoint 0.5 is not itself within tolerance; choose the nearest
        # qualifying alpha instead.
        curve = {0.0: 0.80, 0.5: 0.50, 0.9: 0.79, 1.0: 0.81}
        chosen, qualifying = select_alpha(curve)
        self.assertEqual(qualifying, [0.0, 0.9, 1.0])
        self.assertEqual(chosen, 0.9)

    def test_tolerance_boundary_is_inclusive(self):
        chosen, qualifying = select_alpha({0.0: 0.78, 1.0: 0.80})
        self.assertEqual(qualifying, [0.0, 1.0])
        self.assertEqual(chosen, 0.0)

    def test_missing_values_are_ignored(self):
        self.assertEqual(select_alpha({0.0: None, 0.5: 0.7}), (0.5, [0.5]))
        self.assertEqual(select_alpha({0.0: None}), (None, []))


class MetricHelperTests(SimpleTestCase):
    def test_precision_threshold(self):
        relevance = {"A": 2, "B": 1, "C": 0}
        ranked = ["A", "B", "C"]
        self.assertAlmostEqual(precision_at_k(ranked, relevance, 3), 2 / 3)
        self.assertAlmostEqual(precision_at_k(ranked, relevance, 3, 2), 1 / 3)

    def test_compare(self):
        self.assertEqual(compare(0.8, 0.5), "improved")
        self.assertEqual(compare(0.5, 0.5), "tied")
        self.assertEqual(compare(0.4, 0.5), "worse")
        self.assertIsNone(compare(None, 0.5))

    def test_rater_agreement_uses_rows_rated_by_both(self):
        first = {"H01": {"A": 2, "B": 1, "C": 0, "D": 2}}
        second = {"H01": {"A": 2, "B": 2, "C": 1}}
        agreement = rater_agreement(first, second)
        self.assertEqual(agreement["items"], 3)
        self.assertAlmostEqual(agreement["exact"], 1 / 3)
        self.assertAlmostEqual(agreement["relevant_at_1"], 2 / 3)  # C differs
        self.assertAlmostEqual(agreement["relevant_at_2"], 2 / 3)  # B differs
        self.assertIsNone(rater_agreement(first, {}))


class LoadHeldOutLabelsTests(SimpleTestCase):
    def write(self, rows, columns=COLUMNS):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "labels.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({c: "" for c in columns} | row)
        return path

    def test_reads_grades_rater2_and_rows(self):
        path = self.write(
            [
                dict(child_id="H01", split="tune", activity_id="A", relevance="2"),
                dict(
                    child_id="H01",
                    split="tune",
                    activity_id="B",
                    relevance="0",
                    relevance_rater2="1",
                ),
                dict(child_id="H02", split="test", activity_id="A"),
            ]
        )
        labels = load_heldout_labels(path)
        self.assertEqual(labels.relevance, {"H01": {"A": 2, "B": 0}})
        self.assertEqual(labels.rater2, {"H01": {"B": 1}})
        self.assertEqual(labels.rows, {"H01": ["A", "B"], "H02": ["A"]})
        self.assertEqual((labels.total_rows, labels.labelled_rows), (3, 2))

    def test_collects_every_problem(self):
        path = self.write(
            [
                dict(child_id="H99", split="tune", activity_id="A"),
                dict(child_id="H03", split="tune", activity_id="A"),  # is test
                dict(child_id="H01", split="tune", activity_id="A", relevance="3"),
                dict(child_id="H01", split="tune", activity_id="A"),
                dict(
                    child_id="H01",
                    split="tune",
                    activity_id="B",
                    relevance_rater2="x",
                ),
            ]
        )
        with self.assertRaises(LabelError) as ctx:
            load_heldout_labels(path)
        problems = "\n".join(ctx.exception.problems)
        self.assertIn("unknown child_id 'H99'", problems)
        self.assertIn("stored split is 'test'", problems)
        self.assertIn("relevance '3'", problems)
        self.assertIn("duplicate row for H01 / A", problems)
        self.assertIn("relevance_rater2 'x'", problems)

    def test_missing_columns(self):
        path = self.write([], columns=["child_id", "activity_id"])
        with self.assertRaises(LabelError) as ctx:
            load_heldout_labels(path)
        self.assertIn("split", ctx.exception.problems[0])


class HeldOutProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_milestones", stdout=StringIO())

    def test_milestones_exist_and_are_due(self):
        for child in heldout.HELDOUT_CHILDREN:
            for key in child.not_yet + child.achieved:
                with self.subTest(child=child.child_id, key=key):
                    reference = ReferenceMilestone.objects.get(milestone_key=key)
                    self.assertGreaterEqual(
                        child.age_months, float(reference.expected_age_months)
                    )

    def test_profiles_put_the_intended_domains_on_top(self):
        caregiver = User.objects.create_user(username="caregiver")
        for child in heldout.HELDOUT_CHILDREN:
            if child.not_yet:
                intended = {
                    ReferenceMilestone.objects.get(milestone_key=k).domain
                    for k in child.not_yet
                }
            elif child.concerns:
                intended = set(child.concerns)
            else:
                intended = ALL_DOMAINS  # on track: no domain stands out
            with self.subTest(child=child.child_id):
                evaluation = build_profile(heldout.create_child(child, caregiver))
                top = max(evaluation.scores.values())
                tops = {d for d, s in evaluation.scores.items() if s == top}
                self.assertEqual(tops, intended)
                self.assertEqual(evaluation.age_months < 0, child.age_months < 0)


class HeldOutCommandTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_milestones", stdout=StringIO())

    def setUp(self):
        embeddings.set_encoder(FakeEncoder())
        self.addCleanup(embeddings.set_encoder, None)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "heldout_labels.csv"

    def publish(self):
        for fields in DOMAIN_ACTIVITIES:
            DevelopmentalActivity.objects.create(
                **activity_fields(content_status=ContentStatus.PUBLISHED, **fields)
            )
        DevelopmentalActivity.objects.create(
            **activity_fields(
                content_status=ContentStatus.PUBLISHED,
                activity_id="ACT-0957",
                activity_name="Babble Back",
                developmental_domain=Domain.LANGUAGE,
                age_range=AgeRange.MONTHS_0_3,
                developmental_goal="Early cooing and turn-taking",
                description="Copy your baby's coos and smile back.",
            )
        )
        call_command("embed_activities", stdout=StringIO())

    def export(self, *args):
        out = StringIO()
        call_command(
            "export_heldout_labels",
            "--output",
            str(self.path),
            *args,
            stdout=out,
            stderr=StringIO(),
        )
        return out.getvalue()

    def read(self):
        with open(self.path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def write(self, rows):
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)


class ExportHeldOutLabelsTests(HeldOutCommandTestCase):
    def test_nothing_published(self):
        with self.assertRaisesMessage(CommandError, "No Published activities"):
            self.export()

    def test_blind_columns_and_pooled_rows(self):
        self.publish()
        output = self.export()
        rows = self.read()

        self.assertEqual(list(rows[0].keys()), COLUMNS)
        for hidden in ("similarity", "score", "rank", "priority", "domain"):
            self.assertFalse(any(hidden in c for c in COLUMNS))
        self.assertIn(f"Wrote {len(rows)} rows for 20 children", output)
        self.assertEqual({r["child_id"] for r in rows}, set(heldout.HELDOUT_BY_ID))
        for row in rows:
            child = heldout.HELDOUT_BY_ID[row["child_id"]]
            self.assertEqual(row["split"], child.split)
            self.assertEqual(row["child_profile"], child.profile)
            self.assertEqual(
                row["age_range"] == AgeRange.PRENATAL, child.age_months < 0
            )
            self.assertEqual(
                (row["relevance"], row["notes"], row["relevance_rater2"]),
                ("", "", ""),
            )
        # 6 post-natal activities, all within the top 5 of some ranking.
        h03 = [r["activity_id"] for r in rows if r["child_id"] == "H03"]
        self.assertEqual(len(h03), 6)
        self.assertNotEqual(h03, sorted(h03))  # shuffled, not ID order
        self.assertFalse(User.objects.exists())
        self.assertFalse(ChildProfile.objects.exists())

    def test_deterministic_and_refuses_to_overwrite(self):
        self.publish()
        self.export()
        first = self.path.read_bytes()
        with self.assertRaisesMessage(CommandError, "already exists"):
            self.export()
        self.export("--force")
        self.assertEqual(self.path.read_bytes(), first)


class EvaluateAlphaGridTests(HeldOutCommandTestCase):
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

    def chosen_line(self, output):
        return next(line for line in output.splitlines() if "Chosen alpha" in line)

    def test_unlabelled_sheet_cannot_choose_alpha(self):
        self.publish()
        self.export()
        output = self.evaluate()
        self.assertIn("0 of", output)
        self.assertIn("alpha can't be chosen", output)

    def test_invalid_labels_are_reported(self):
        self.write([{c: "" for c in COLUMNS} | dict(child_id="H03", split="tune")])
        with self.assertRaisesMessage(CommandError, "stored split is 'test'"):
            self.evaluate()

    def test_full_report(self):
        self.publish()
        self.export()
        rows = self.read()
        for row in rows:
            language = row["activity_id"] in ("ACT-0951", "ACT-0957")
            row["relevance"] = "2" if language else "0"
        rows[0]["relevance_rater2"] = rows[0]["relevance"]
        self.write(rows)

        output = self.evaluate()
        self.assertIn(f"{len(rows)} of {len(rows)} rows labelled", output)
        self.assertIn("Tune set (11 children)", output)
        self.assertIn("| SBERT-only |", output)
        self.assertIn("| alpha 1.0 |", output)
        self.assertIn("Chosen alpha (middle of that range)", output)
        self.assertIn("Test set: alpha", output)
        self.assertIn("(of 8). With this few children", output)
        self.assertIn("Content-gap child (reported separately)", output)
        self.assertIn("| H17 |", output)
        self.assertIn("1 rows rated by both: exact agreement 100%", output)
        self.assertFalse(User.objects.exists())

    def test_alpha_is_chosen_on_tune_only(self):
        self.publish()
        self.export()
        rows = self.read()
        for row in rows:
            row["relevance"] = "2" if row["activity_id"] == "ACT-0951" else "0"
        self.write(rows)
        before = self.chosen_line(self.evaluate())

        # Changing every test and gap label must not change the choice.
        for row in rows:
            if row["split"] != "tune":
                row["relevance"] = "0" if row["activity_id"] == "ACT-0951" else "2"
        self.write(rows)
        self.assertEqual(self.chosen_line(self.evaluate()), before)
