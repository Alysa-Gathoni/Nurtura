"""Tests for stored, ranked recommendations and their API (#52)."""

import threading
import unittest
import uuid
from io import StringIO
from types import SimpleNamespace
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from activities.choices import AgeRange, ContentStatus, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from feedback.models import CompletedActivity
from profiles.models import ChildProfile, ReferenceMilestone

from . import embeddings, generation, heldout
from .models import Recommendation
from .ranking import (
    FURTHER,
    SAME_BRACKET,
    rank,
    rank_candidates,
)
from .retrieval import Candidate
from .test_embeddings import FakeEncoder
from .test_spot_check import DOMAIN_ACTIVITIES

User = get_user_model()

# More post-natal activities, so most children have at least 5 candidates.
EXTRA_ACTIVITIES = [
    dict(
        activity_id="ACT-0961",
        activity_name="Babble Back and Forth",
        developmental_domain=Domain.LANGUAGE,
        age_range=AgeRange.MONTHS_3_6,
        developmental_goal="Turn-taking with sounds",
        description="Copy your baby's coos and babbling, then pause so they can "
        "answer you.",
    ),
    dict(
        activity_id="ACT-0962",
        activity_name="Tummy Time Reach",
        developmental_domain=Domain.MOTOR,
        age_range=AgeRange.MONTHS_3_6,
        developmental_goal="Head control and reaching",
        description="Place a toy just out of reach during tummy time to "
        "encourage lifting the head and reaching.",
    ),
    dict(
        activity_id="ACT-0963",
        activity_name="Stack and Topple",
        developmental_domain=Domain.COGNITIVE,
        age_range=AgeRange.MONTHS_12_18,
        developmental_goal="Stacking and cause and effect",
        description="Stack two or three soft blocks together, then knock them "
        "down and build again.",
    ),
    dict(
        activity_id="ACT-0964",
        activity_name="Hug and Name Feelings",
        developmental_domain=Domain.SOCIO_EMOTIONAL,
        age_range=AgeRange.MONTHS_12_18,
        developmental_goal="Affection and feelings",
        description="Cuddle and hug, and name feelings like happy and sad "
        "during play.",
    ),
]

CARD_FIELDS = {
    "id",
    "batch",
    "position",
    "generated_at",
    "activity_id",
    "activity_name",
    "developmental_domain",
    "age_range",
    "short_description",
    "explanation",
}


def publish_catalogue():
    for fields in DOMAIN_ACTIVITIES + EXTRA_ACTIVITIES:
        DevelopmentalActivity.objects.create(
            **activity_fields(content_status=ContentStatus.PUBLISHED, **fields)
        )
    call_command("embed_activities", stdout=StringIO())


def url(child):
    return reverse("child-recommendations", args=[child.pk])


# Ranking-score bound


def _candidate(activity_id, domain, age_range, similarity):
    activity = SimpleNamespace(
        activity_id=activity_id, developmental_domain=domain, age_range=age_range
    )
    return Candidate(activity=activity, similarity=similarity)


class RankingScoreBoundTests(SimpleTestCase):
    """ranking_score = age_weight x ((1 - a) x sim_norm + a x priority) is in [0, 1]."""

    ALPHAS = (0.0, 1e-12, 0.1, 0.3, 0.5, 0.7, 0.9, 1 - 1e-12, 1.0)

    def evaluation(self, priority, age_months):
        scores = {d.value: priority for d in Domain}
        return SimpleNamespace(scores=scores, age_months=age_months)

    def test_extreme_inputs_stay_in_bounds(self):
        # Raw cosine at both extremes (-1 and 1, which retrieval clips to),
        # priorities 0 and 1, every age weight from same bracket to far away.
        ages = [AgeRange.MONTHS_0_3, AgeRange.MONTHS_12_18, AgeRange.MONTHS_24_36]
        candidates = [
            _candidate(f"A{i}", Domain.LANGUAGE, age, sim)
            for i, (age, sim) in enumerate(
                (age, sim) for age in ages for sim in (-1.0, 1.0, 0.0)
            )
        ]
        for alpha in self.ALPHAS:
            for priority in (0.0, 1.0):
                for age_months in (1, 30, -2):  # young, old, prenatal
                    ranked = rank_candidates(
                        candidates, self.evaluation(priority, age_months), alpha
                    )
                    for r in ranked:
                        with self.subTest(alpha=alpha, priority=priority):
                            self.assertGreaterEqual(r.score, 0.0)
                            self.assertLessEqual(r.score, 1.0)
                            self.assertGreaterEqual(r.similarity_norm, 0.0)
                            self.assertLessEqual(r.similarity_norm, 1.0)

    def test_maximum_is_exactly_one_and_minimum_exactly_zero(self):
        candidates = [
            _candidate("TOP", Domain.LANGUAGE, AgeRange.MONTHS_0_3, 1.0),
            _candidate("LOW", Domain.LANGUAGE, AgeRange.MONTHS_0_3, -1.0),
        ]
        for alpha in self.ALPHAS:
            top = rank_candidates(candidates, self.evaluation(1.0, 1), alpha)[0]
            self.assertEqual(top.score, 1.0)
            low = rank_candidates(candidates, self.evaluation(0.0, 1), alpha)[-1]
            self.assertEqual(low.score, 0.0)

    def test_single_candidate_and_far_age(self):
        only = [_candidate("ONE", Domain.MOTOR, AgeRange.MONTHS_24_36, 0.2)]
        ranked = rank_candidates(only, self.evaluation(1.0, 1), 0.7)
        self.assertEqual(ranked[0].similarity_norm, 1.0)
        self.assertEqual(ranked[0].age_weight, FURTHER)
        self.assertAlmostEqual(ranked[0].score, FURTHER)
        self.assertLessEqual(SAME_BRACKET, 1.0)


class RecommendationConstraintTests(TestCase):
    def setUp(self):
        caregiver = User.objects.create_user(username="caregiver")
        self.child = ChildProfile.objects.create(
            caregiver=caregiver, name="Kim", date_of_birth="2026-01-01"
        )
        self.activity = DevelopmentalActivity.objects.create(
            **activity_fields(content_status=ContentStatus.PUBLISHED)
        )

    def save(self, **fields):
        values = dict(
            child=self.child,
            activity=self.activity,
            similarity_score=0.5,
            ranking_score=0.5,
        )
        values.update(fields)
        with transaction.atomic():
            return Recommendation.objects.create(**values)

    def test_ranking_score_bounds(self):
        self.save(ranking_score=0.0)
        self.save(ranking_score=1.0)
        for bad in (-1e-9, 1.0000001, 2.0):
            with self.subTest(score=bad), self.assertRaises(IntegrityError):
                self.save(ranking_score=bad)

    def test_other_bounds(self):
        for field, bad in (
            ("rule_priority", 1.5),
            ("age_weight", -0.1),
            ("alpha", 1.1),
            ("position", 6),
            ("position", 0),
            ("similarity_score", 1.01),
        ):
            with self.subTest(field=field), self.assertRaises(IntegrityError):
                self.save(**{field: bad})

    def test_unique_position_and_activity_per_batch(self):
        batch = uuid.uuid4()
        self.save(batch=batch, position=1)
        with self.assertRaises(IntegrityError):
            self.save(batch=batch, position=2)  # same activity
        other = DevelopmentalActivity.objects.create(
            **activity_fields(
                activity_id="ACT-0002",
                activity_name="Another Activity",
                content_status=ContentStatus.PUBLISHED,
            )
        )
        with self.assertRaises(IntegrityError):
            self.save(batch=batch, position=1, activity=other)


class HelperTests(SimpleTestCase):
    def test_ranking_version_matches_sprint5_eval_v1(self):
        self.assertEqual(
            generation.ranking_version(),
            generation.SPRINT5_EVAL_V1_RANKING_VERSION,
            "The ranking configuration differs from the one evaluated at "
            "sprint5-eval-v1. Re-evaluate before changing it deliberately.",
        )
        self.assertEqual(settings.RANKING_ALPHA, 0.7)

    @override_settings(RANKING_ALPHA=0.5)
    def test_ranking_version_changes_with_alpha(self):
        self.assertNotEqual(
            generation.ranking_version(), generation.SPRINT5_EVAL_V1_RANKING_VERSION
        )

    def test_short_description(self):
        self.assertEqual(generation.short_description("Short  text\n"), "Short text")
        long = "word " * 60
        cut = generation.short_description(long)
        self.assertLessEqual(len(cut), generation.SHORT_DESCRIPTION_LENGTH)
        self.assertTrue(cut.endswith("…"))
        self.assertFalse(cut[:-1].endswith(" "))


# API


class RecommendationAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_milestones", stdout=StringIO())

    def setUp(self):
        embeddings.set_encoder(FakeEncoder())
        self.addCleanup(embeddings.set_encoder, None)
        publish_catalogue()
        self.caregiver = User.objects.create_user(username="caregiver@example.com")
        self.client.force_authenticate(self.caregiver)
        self.child = heldout.create_child(heldout.HELDOUT_BY_ID["H03"], self.caregiver)

    def post(self, child=None):
        return self.client.post(url(child or self.child))

    def get(self, child=None):
        return self.client.get(url(child or self.child))


class AccessTests(RecommendationAPITestCase):
    def test_anonymous_gets_401(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.get().status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.post().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_administrator_gets_403(self):
        admin = User.objects.create_user(
            username="admin@example.com", role=User.Role.ADMINISTRATOR
        )
        self.client.force_authenticate(admin)
        self.assertEqual(self.get().status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.post().status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Recommendation.objects.exists())

    def test_another_caregivers_child_is_404(self):
        other = User.objects.create_user(username="other@example.com")
        self.client.force_authenticate(other)
        self.assertEqual(self.get().status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.post().status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Recommendation.objects.exists())

    def test_missing_child_is_404(self):
        missing = SimpleNamespace(pk=999999)
        self.assertEqual(self.post(missing).status_code, status.HTTP_404_NOT_FOUND)


class GenerateTests(RecommendationAPITestCase):
    def test_post_stores_top_5_and_returns_cards(self):
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        cards = body["recommendations"]
        self.assertEqual(len(cards), 5)
        self.assertEqual([c["position"] for c in cards], [1, 2, 3, 4, 5])
        for card in cards:
            self.assertEqual(set(card), CARD_FIELDS)
            self.assertEqual(card["explanation"], "")
            self.assertEqual(card["batch"], body["batch"])
            self.assertEqual(card["generated_at"], body["generated_at"])
        self.assertEqual(Recommendation.objects.count(), 5)
        self.assertEqual(len({str(r.batch) for r in Recommendation.objects.all()}), 1)

    def test_stored_scores_match_the_ranking(self):
        self.post()
        ranked = rank(self.child).ranked[:5]
        stored = list(Recommendation.objects.order_by("position"))
        for r, row in zip(ranked, stored):
            self.assertEqual(row.activity, r.activity)
            self.assertEqual(row.ranking_score, r.score)
            self.assertEqual(row.similarity_score, r.similarity)
            self.assertEqual(row.rule_priority, r.priority)
            self.assertEqual(row.age_weight, r.age_weight)
            self.assertEqual(row.alpha, 0.7)
            self.assertEqual(
                row.ranking_version, generation.SPRINT5_EVAL_V1_RANKING_VERSION
            )
            self.assertEqual(len(row.profile_fingerprint), 64)

    def test_order_equals_the_evaluation_harness(self):
        """Same rank() and settings as sprint5-eval-v1, for fixed children."""
        for child_id in ("H03", "H07", "H08", "H13", "H18", "H02"):
            child = heldout.create_child(
                heldout.HELDOUT_BY_ID[child_id], self.caregiver
            )
            with self.subTest(child=child_id):
                cards = self.post(child).json()["recommendations"]
                _, rankings = heldout.rankings_for(child)
                expected = rankings[settings.RANKING_ALPHA][:5]
                self.assertEqual([c["activity_id"] for c in cards], expected)

    def test_get_reads_only(self):
        self.assertEqual(
            self.get().json(),
            {"batch": None, "generated_at": None, "recommendations": []},
        )
        self.assertFalse(Recommendation.objects.exists())
        posted = self.post().json()
        self.assertEqual(self.get().json(), posted)
        self.assertEqual(Recommendation.objects.count(), 5)

    def test_repeat_post_returns_the_same_batch(self):
        first = self.post().json()
        again = self.post()
        self.assertEqual(again.status_code, status.HTTP_200_OK)
        self.assertEqual(again.json(), first)
        self.assertEqual(Recommendation.objects.count(), 5)

    def test_changed_profile_stores_a_new_batch_and_keeps_the_old(self):
        first = self.post().json()
        self.child.record_milestone(
            reference=ReferenceMilestone.objects.get(milestone_key="CDC-02M-SE-04"),
            status="not_yet",
        )
        second = self.post()
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(second.json()["batch"], first["batch"])
        self.assertEqual(Recommendation.objects.filter(batch=first["batch"]).count(), 5)
        self.assertEqual(self.get().json()["batch"], second.json()["batch"])

    def test_every_field_of_the_duplicate_check_matters(self):
        first = self.post().json()
        for target, value in (
            ("profile_fingerprint", "f" * 64),
            ("ranking_version", "v" * 64),
        ):
            with self.subTest(changed=target), mock.patch.object(
                generation, target, return_value=value
            ):
                response = self.post()
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertNotEqual(response.json()["batch"], first["batch"])
        with override_settings(RANKING_ALPHA=0.71):
            response = self.post()
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(Recommendation.objects.filter(alpha=0.71).count(), 5)
        self.assertEqual(Recommendation.objects.count(), 20)  # nothing deleted

    def test_completed_activities_are_excluded_partial_stay(self):
        cards = self.post().json()["recommendations"]
        done, partial = Recommendation.objects.order_by("position")[:2]
        CompletedActivity.objects.create(recommendation=done)
        CompletedActivity.objects.create(
            recommendation=partial,
            status=CompletedActivity.Status.PARTIALLY_COMPLETED,
        )
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ids = [c["activity_id"] for c in response.json()["recommendations"]]
        self.assertNotIn(cards[0]["activity_id"], ids)
        self.assertIn(cards[1]["activity_id"], ids)
        # The rest keep the evaluated order.
        evaluated = [r.activity.activity_id for r in rank(self.child).ranked]
        self.assertEqual(
            ids, [a for a in evaluated if a != cards[0]["activity_id"]][:5]
        )

    def test_fewer_eligible_activities_than_5(self):
        expecting = heldout.create_child(heldout.HELDOUT_BY_ID["H01"], self.caregiver)
        cards = self.post(expecting).json()["recommendations"]
        self.assertEqual(len(cards), 1)  # one prenatal activity in the catalogue
        self.assertEqual(cards[0]["position"], 1)
        self.assertEqual(cards[0]["age_range"], AgeRange.PRENATAL)

    def test_nothing_eligible_stores_nothing(self):
        DevelopmentalActivity.objects.update(content_status=ContentStatus.DRAFT)
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["recommendations"], [])
        self.assertFalse(Recommendation.objects.exists())


@unittest.skipUnless(
    connection.vendor == "postgresql",
    "Row locking needs PostgreSQL; SQLite serialises writes differently",
)
class ConcurrentPostTests(TransactionTestCase):
    def setUp(self):
        call_command("seed_milestones", stdout=StringIO())
        embeddings.set_encoder(FakeEncoder())
        self.addCleanup(embeddings.set_encoder, None)
        publish_catalogue()
        self.caregiver = User.objects.create_user(username="caregiver@example.com")
        self.child = heldout.create_child(heldout.HELDOUT_BY_ID["H03"], self.caregiver)

    def test_simultaneous_posts_store_one_batch(self):
        real_rank = generation.rank
        barrier = threading.Barrier(2)

        def slow_rank(child):
            # Hold the lock long enough for the other request to arrive.
            result = real_rank(child)
            threading.Event().wait(0.3)
            return result

        responses = []

        def request():
            try:
                client = APIClient()
                client.force_authenticate(self.caregiver)
                barrier.wait()
                responses.append(client.post(url(self.child)))
            finally:
                connection.close()

        with mock.patch.object(generation, "rank", side_effect=slow_rank):
            threads = [threading.Thread(target=request) for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        self.assertEqual(
            sorted(r.status_code for r in responses),
            [status.HTTP_200_OK, status.HTTP_201_CREATED],
        )
        self.assertEqual(Recommendation.objects.count(), 5)
        self.assertEqual(responses[0].json()["batch"], responses[1].json()["batch"])
