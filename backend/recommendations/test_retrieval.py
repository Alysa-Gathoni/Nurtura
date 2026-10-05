"""Tests for profile-to-activity semantic retrieval (#30)."""

import datetime
import unittest
from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from activities.choices import AgeRange, ContentStatus, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from profiles.models import ChildProfile, ReferenceMilestone
from profiles.rules import build_profile

from . import embeddings
from .models import ActivityEmbedding
from .retrieval import DOMAIN_DESCRIPTIONS, profile_query, retrieve
from .test_embeddings import FakeEncoder

User = get_user_model()

LANGUAGE_ACTIVITY = dict(
    activity_id="ACT-0901",
    activity_name="Talk and Sing Together",
    developmental_domain=Domain.LANGUAGE,
    age_range=AgeRange.MONTHS_3_6,
    developmental_goal="Build early babbling and first words",
    description="Talk, sing and read together, naming things and listening "
    "for your baby's sounds and babbling.",
)
MOTOR_ACTIVITY = dict(
    activity_id="ACT-0902",
    activity_name="Tummy Time Rolling",
    developmental_domain=Domain.MOTOR,
    age_range=AgeRange.MONTHS_3_6,
    developmental_goal="Build strength for rolling and crawling",
    description="Place your baby on their tummy and encourage rolling and "
    "crawling towards a toy, building balance and movement.",
)
COGNITIVE_ACTIVITY = dict(
    activity_id="ACT-0903",
    activity_name="Hide the Toy",
    developmental_domain=Domain.COGNITIVE,
    age_range=AgeRange.MONTHS_6_12,
    developmental_goal="Understand that hidden objects still exist",
    description="Hide a toy under a cloth and help your baby find it, "
    "exploring cause and effect.",
)


def months_ago(months):
    return timezone.localdate() - datetime.timedelta(days=round(months * 30.4375))


class RetrievalTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_milestones", stdout=StringIO())
        cls.caregiver = User.objects.create_user(
            username="wanjiru@example.com", password="x-test-pass"
        )

    def setUp(self):
        super().setUp()
        self.encoder = FakeEncoder()
        embeddings.set_encoder(self.encoder)
        self.addCleanup(embeddings.set_encoder, None)

    def child(self, months_old, **fields):
        return ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Amani",
            date_of_birth=months_ago(months_old),
            **fields,
        )

    def observe(self, child, key, status_value="not_yet"):
        child.record_milestone(
            reference=ReferenceMilestone.objects.get(milestone_key=key),
            status=status_value,
        )

    def publish_and_embed(self, *activities):
        for fields in activities:
            DevelopmentalActivity.objects.create(
                **activity_fields(content_status=ContentStatus.PUBLISHED, **fields)
            )
        call_command("embed_activities", stdout=StringIO())


class ProfileQueryTests(RetrievalTestCase):
    def test_query_describes_priority_domain_milestone_and_interests(self):
        child = self.child(6, interests=["music"])
        self.observe(child, "CDC-04M-LA-01")  # cooing, due at 4 months
        query = profile_query(build_profile(child), child)

        self.assertIn("a 6-month-old baby", query)
        self.assertIn(DOMAIN_DESCRIPTIONS["Language"], query)
        self.assertNotIn(DOMAIN_DESCRIPTIONS["Motor"], query)
        # The music interest raises Sensory, but not into the focus domains.
        self.assertNotIn(DOMAIN_DESCRIPTIONS["Sensory"], query)
        self.assertIn('Still working on: Makes sounds like "oooo" or "aahh"', query)
        self.assertTrue(query.endswith("Enjoys music."))

    def test_no_evidence_gives_a_general_query(self):
        child = self.child(9)
        query = profile_query(build_profile(child), child)
        for description in DOMAIN_DESCRIPTIONS.values():
            self.assertIn(description, query)
        self.assertNotIn("Still working on", query)

    def test_prenatal_query(self):
        child = ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Baby",
            date_of_birth=timezone.localdate() + datetime.timedelta(days=60),
            concerns=["Sensory"],
        )
        query = profile_query(build_profile(child), child)
        self.assertIn("an expecting parent during pregnancy", query)
        self.assertIn(DOMAIN_DESCRIPTIONS["Sensory"], query)
        self.assertNotIn(DOMAIN_DESCRIPTIONS["Motor"], query)

    def test_achieved_milestones_are_not_listed_as_still_working_on(self):
        child = self.child(6)
        self.observe(child, "CDC-04M-LA-01", "achieved")
        self.assertNotIn("Still working on", profile_query(build_profile(child), child))


class RetrieveTests(RetrievalTestCase):
    def setUp(self):
        super().setUp()
        self.publish_and_embed(LANGUAGE_ACTIVITY, MOTOR_ACTIVITY, COGNITIVE_ACTIVITY)

    def ids(self, result):
        return [c.activity.activity_id for c in result.candidates]

    def test_language_delay_retrieves_language_activity_first(self):
        child = self.child(6)
        self.observe(child, "CDC-04M-LA-01")
        result = retrieve(child)
        self.assertEqual(self.ids(result)[0], "ACT-0901")
        sims = [c.similarity for c in result.candidates]
        self.assertEqual(sims, sorted(sims, reverse=True))
        self.assertTrue(all(-1.0 <= s <= 1.0 for s in sims))

    def test_motor_delay_retrieves_motor_activity_first(self):
        child = self.child(7)
        self.observe(child, "CDC-06M-MO-01")  # rolls from tummy to back
        self.assertEqual(self.ids(retrieve(child))[0], "ACT-0902")

    def test_limit(self):
        child = self.child(6)
        self.assertEqual(len(retrieve(child, limit=2).candidates), 2)

    def test_unpublished_activities_are_never_candidates(self):
        DevelopmentalActivity.objects.get(activity_id="ACT-0901").transition_to(
            ContentStatus.DRAFT
        )  # embedding still exists until embed_activities is re-run
        self.assertNotIn("ACT-0901", self.ids(retrieve(self.child(6))))

    def test_embeddings_from_another_model_are_ignored(self):
        ActivityEmbedding.objects.filter(activity__activity_id="ACT-0902").update(
            model_name="old-model"
        )
        self.assertNotIn("ACT-0902", self.ids(retrieve(self.child(6))))

    def test_pregnancy_activities_only_for_expecting_parents(self):
        self.publish_and_embed(
            dict(
                activity_id="ACT-0904",
                activity_name="Talk to Your Bump",
                developmental_domain=Domain.LANGUAGE,
                age_range=AgeRange.PRENATAL,
                developmental_goal="Familiarity with voices before birth",
                description="Talk, sing and read to your baby during pregnancy.",
            )
        )
        born = self.child(6)
        self.observe(born, "CDC-04M-LA-01")
        self.assertNotIn("ACT-0904", self.ids(retrieve(born)))

        expecting = ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Baby",
            date_of_birth=timezone.localdate() + datetime.timedelta(days=60),
        )
        self.assertEqual(self.ids(retrieve(expecting)), ["ACT-0904"])

    def test_nothing_embedded_gives_no_candidates(self):
        ActivityEmbedding.objects.all().delete()
        result = retrieve(self.child(6))
        self.assertEqual(result.candidates, [])
        self.assertTrue(result.query)


class CandidatesAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_milestones", stdout=StringIO())
        cls.caregiver = User.objects.create_user(
            username="wanjiru@example.com", password="x-test-pass"
        )

    def setUp(self):
        encoder = FakeEncoder()
        embeddings.set_encoder(encoder)
        self.addCleanup(embeddings.set_encoder, None)
        for fields in (LANGUAGE_ACTIVITY, MOTOR_ACTIVITY):
            DevelopmentalActivity.objects.create(
                **activity_fields(content_status=ContentStatus.PUBLISHED, **fields)
            )
        call_command("embed_activities", stdout=StringIO())
        self.child = ChildProfile.objects.create(
            caregiver=self.caregiver, name="Amani", date_of_birth=months_ago(6)
        )
        self.child.record_milestone(
            reference=ReferenceMilestone.objects.get(milestone_key="CDC-04M-LA-01"),
            status="not_yet",
        )
        self.url = reverse("child-candidates", args=[self.child.pk])

    def test_caregiver_gets_ranked_candidates(self):
        self.client.force_authenticate(self.caregiver)
        response = self.client.get(self.url, {"limit": 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["profile"]["ranked_domains"][0], "Language")
        self.assertIn("6-month-old", response.data["query"])
        first = response.data["candidates"][0]
        self.assertEqual(first["activity_id"], "ACT-0901")
        self.assertEqual(
            set(first),
            {
                "activity_id",
                "activity_name",
                "developmental_domain",
                "age_range",
                "similarity",
            },
        )

    def test_limit_validated(self):
        self.client.force_authenticate(self.caregiver)
        for bad in ("0", "51", "ten"):
            with self.subTest(limit=bad):
                response = self.client.get(self.url, {"limit": bad})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_access_is_limited_to_the_childs_caregiver(self):
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED
        )
        other = User.objects.create_user(username="otieno", password="x-test-pass")
        self.client.force_authenticate(other)
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_404_NOT_FOUND
        )
        admin = User.objects.create_user(
            username="admin", password="x-test-pass", role=User.Role.ADMINISTRATOR
        )
        self.client.force_authenticate(admin)
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN
        )


@unittest.skipUnless(
    settings.SBERT_MODEL_PATH.exists(),
    "SBERT model not downloaded (run setup_sbert.py); skipped in CI",
)
class RealModelRetrievalTests(RetrievalTestCase):
    """The same checks with the real all-MiniLM-L6-v2 model."""

    def setUp(self):
        super().setUp()
        embeddings.set_encoder(None)  # use the real model
        self.publish_and_embed(LANGUAGE_ACTIVITY, MOTOR_ACTIVITY, COGNITIVE_ACTIVITY)

    def test_real_model_matches_profiles_to_their_domain(self):
        language_child = self.child(6)
        self.observe(language_child, "CDC-04M-LA-01")
        self.assertEqual(
            retrieve(language_child).candidates[0].activity.activity_id, "ACT-0901"
        )

        motor_child = self.child(7)
        self.observe(motor_child, "CDC-06M-MO-01")
        self.assertEqual(
            retrieve(motor_child).candidates[0].activity.activity_id, "ACT-0902"
        )
