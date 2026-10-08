"""Tests for the weighted ranking function (#35)."""

import datetime
from io import StringIO
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from activities.choices import AgeRange, ContentStatus
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from profiles.models import ChildProfile

from . import embeddings
from .ranking import (
    FURTHER,
    ONE_OLDER,
    ONE_YOUNGER,
    SAME_BRACKET,
    TWO_AWAY,
    age_weight,
    child_bracket,
    rank,
    rank_candidates,
)
from .retrieval import Candidate
from .test_embeddings import FakeEncoder
from .test_spot_check import DOMAIN_ACTIVITIES

SCORES = {
    "Cognitive": 0.2,
    "Language": 1.0,
    "Motor": 0.5,
    "Sensory": 0.2,
    "Socio-Emotional": 0.2,
}


def evaluation(age_months=13.0, scores=None):
    return SimpleNamespace(age_months=age_months, scores=scores or SCORES)


def candidate(activity_id, domain, age_range, similarity):
    activity = SimpleNamespace(
        activity_id=activity_id, developmental_domain=domain, age_range=age_range
    )
    return Candidate(activity=activity, similarity=similarity)


def ids(ranked):
    return [r.activity.activity_id for r in ranked]


class AgeWeightTests(SimpleTestCase):
    def test_child_bracket_boundaries(self):
        self.assertEqual(child_bracket(0), 0)
        self.assertEqual(child_bracket(5.99), 1)
        self.assertEqual(child_bracket(6.0), 2)  # start of 6-12 is inclusive
        self.assertEqual(child_bracket(35.9), 5)
        self.assertEqual(child_bracket(40), 5)  # 36+ months use the last bracket
        self.assertIsNone(child_bracket(-2))
        self.assertIsNone(child_bracket(None))

    def test_asymmetric_weights_for_a_13_month_old(self):
        expected = {
            AgeRange.MONTHS_12_18: SAME_BRACKET,
            AgeRange.MONTHS_6_12: ONE_YOUNGER,
            AgeRange.MONTHS_18_24: ONE_OLDER,
            AgeRange.MONTHS_3_6: TWO_AWAY,
            AgeRange.MONTHS_24_36: TWO_AWAY,
            AgeRange.MONTHS_0_3: FURTHER,
        }
        for age_range, weight in expected.items():
            with self.subTest(age_range=age_range):
                self.assertEqual(age_weight(13, age_range), weight)
        self.assertEqual(
            (SAME_BRACKET, ONE_YOUNGER, ONE_OLDER, TWO_AWAY, FURTHER),
            (1.0, 0.7, 0.5, 0.25, 0.1),
        )

    def test_prenatal_pool_is_unweighted(self):
        self.assertEqual(age_weight(-3, AgeRange.PRENATAL), 1.0)


class RankCandidatesTests(SimpleTestCase):
    def test_score_formula(self):
        ranked = rank_candidates(
            [
                candidate("A", "Language", AgeRange.MONTHS_6_12, 0.60),
                candidate("B", "Motor", AgeRange.MONTHS_12_18, 0.40),
                candidate("C", "Sensory", AgeRange.MONTHS_12_18, 0.50),
            ],
            evaluation(),
            alpha=0.4,
        )
        by_id = {r.activity.activity_id: r for r in ranked}
        # A: sim_norm 1.0, priority 1.0, one bracket younger (0.7)
        self.assertAlmostEqual(by_id["A"].score, 0.7 * (0.6 * 1.0 + 0.4 * 1.0))
        # B: sim_norm 0.0, priority 0.5, same bracket
        self.assertAlmostEqual(by_id["B"].score, 1.0 * (0.6 * 0.0 + 0.4 * 0.5))
        # C: sim_norm 0.5, priority 0.2, same bracket
        self.assertAlmostEqual(by_id["C"].score, 1.0 * (0.6 * 0.5 + 0.4 * 0.2))
        self.assertEqual(ids(ranked), ["A", "C", "B"])
        self.assertEqual(by_id["A"].similarity_norm, 1.0)
        self.assertEqual(by_id["B"].similarity_norm, 0.0)

    def test_alpha_zero_without_age_is_similarity_order(self):
        cands = [
            candidate("A", "Motor", AgeRange.MONTHS_0_3, 0.70),
            candidate("B", "Language", AgeRange.MONTHS_12_18, 0.65),
            candidate("C", "Sensory", AgeRange.MONTHS_24_36, 0.50),
        ]
        self.assertEqual(
            ids(rank_candidates(cands, evaluation(), 0.0, use_age=False)),
            ["A", "B", "C"],
        )

    def test_alpha_one_ranks_by_priority_then_similarity(self):
        cands = [
            candidate("A", "Sensory", AgeRange.MONTHS_12_18, 0.90),
            candidate("B", "Language", AgeRange.MONTHS_12_18, 0.40),
            candidate("C", "Language", AgeRange.MONTHS_12_18, 0.55),
            candidate("D", "Motor", AgeRange.MONTHS_12_18, 0.60),
        ]
        self.assertEqual(
            ids(rank_candidates(cands, evaluation(), 1.0)), ["C", "B", "D", "A"]
        )

    def test_age_weighting_demotes_older_bracket(self):
        # The 13-month-old's preview problem: an 18-24 month activity with the
        # highest similarity came first.
        cands = [
            candidate("ball", "Motor", AgeRange.MONTHS_18_24, 0.66),
            candidate("balance", "Motor", AgeRange.MONTHS_12_18, 0.59),
            candidate("roll", "Motor", AgeRange.MONTHS_6_12, 0.59),
            candidate("tummy", "Motor", AgeRange.MONTHS_0_3, 0.56),
        ]
        motor_first = evaluation(scores={**SCORES, "Language": 0.1, "Motor": 1.0})
        self.assertEqual(
            ids(rank_candidates(cands, motor_first, 0.0, False))[0], "ball"
        )
        ranked = rank_candidates(cands, motor_first, 0.5)
        # balance 1.0 x (0.5*0.3 + 0.5) = 0.65; ball 0.5 x 1.0 = 0.50;
        # roll 0.7 x 0.65 = 0.455; tummy 0.1 x 0.5 = 0.05
        self.assertEqual(ids(ranked), ["balance", "ball", "roll", "tummy"])
        self.assertAlmostEqual(ranked[0].score, 0.65)
        self.assertAlmostEqual(ranked[1].score, 0.50)

    def test_scores_stay_between_zero_and_one(self):
        cands = [
            candidate(str(i), domain, age, sim)
            for i, (domain, age, sim) in enumerate(
                [
                    ("Language", AgeRange.MONTHS_12_18, 0.9),
                    ("Motor", AgeRange.MONTHS_0_3, 0.1),
                    ("Sensory", AgeRange.MONTHS_6_12, 0.5),
                ]
            )
        ]
        for alpha in (0.0, 0.3, 0.7, 1.0):
            for r in rank_candidates(cands, evaluation(), alpha):
                self.assertGreaterEqual(r.score, 0.0)
                self.assertLessEqual(r.score, 1.0)

    def test_single_candidate_and_ties(self):
        (only,) = rank_candidates(
            [candidate("A", "Language", AgeRange.MONTHS_12_18, 0.3)], evaluation(), 0.5
        )
        self.assertEqual(only.similarity_norm, 1.0)
        tied = [
            candidate("B", "Language", AgeRange.MONTHS_12_18, 0.5),
            candidate("A", "Language", AgeRange.MONTHS_12_18, 0.5),
        ]
        self.assertEqual(ids(rank_candidates(tied, evaluation(), 0.5)), ["A", "B"])

    def test_alpha_must_be_between_zero_and_one(self):
        for bad in (-0.1, 1.01):
            with self.subTest(alpha=bad), self.assertRaises(ValueError):
                rank_candidates([], evaluation(), bad)
        self.assertEqual(rank_candidates([], evaluation(), 0.5), [])


class RankIntegrationTests(TestCase):
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
        self.caregiver = get_user_model().objects.create_user(username="caregiver")

    def child(self, days_old):
        return ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Amani",
            date_of_birth=timezone.localdate() - datetime.timedelta(days=days_old),
        )

    @override_settings(RANKING_ALPHA=0.3)
    def test_ranks_whole_eligible_pool_with_default_alpha(self):
        result = rank(self.child(300))
        self.assertEqual(result.alpha, 0.3)
        # Five post-natal fixture activities; the prenatal one is excluded.
        self.assertEqual(len(result.ranked), 5)
        self.assertNotIn("ACT-0956", ids(result.ranked))
        scores = [r.score for r in result.ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_limit_and_explicit_alpha(self):
        result = rank(self.child(300), alpha=1.0, limit=2)
        self.assertEqual(result.alpha, 1.0)
        self.assertEqual(len(result.ranked), 2)

    def test_expecting_parent_gets_prenatal_pool(self):
        expecting = ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Baby",
            date_of_birth=timezone.localdate() + datetime.timedelta(days=60),
        )
        self.assertEqual(ids(rank(expecting).ranked), ["ACT-0956"])
