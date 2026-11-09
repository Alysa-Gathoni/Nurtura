"""Tests for Explore: browse, search, save and try (#194)."""

import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from activities.choices import AgeRange, ContentStatus, Difficulty, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from feedback.models import CompletedActivity
from profiles.models import ChildProfile

from . import browse, embeddings
from .models import Recommendation, SavedActivity
from .test_embeddings import FakeEncoder

User = get_user_model()

ACTIVITIES = [
    # id, name, domain, age, materials, difficulty, description
    (
        "ACT-0921",
        "Splashing in the Bath",
        Domain.SENSORY,
        AgeRange.MONTHS_6_12,
        "Basin of water",
        Difficulty.BEGINNER,
        "Splash water in the bath and pour it.",
    ),
    (
        "ACT-0922",
        "Naming Toys",
        Domain.LANGUAGE,
        AgeRange.MONTHS_6_12,
        "None",
        Difficulty.BEGINNER,
        "Name each toy as you hand it over.",
    ),
    (
        "ACT-0923",
        "Long Story Time",
        Domain.LANGUAGE,
        AgeRange.MONTHS_6_12,
        "Book",
        Difficulty.INTERMEDIATE,
        "Read a long story. " + "Talk about every page. " * 15,
    ),
    (
        "ACT-0924",
        "Stacking Cups",
        Domain.COGNITIVE,
        AgeRange.MONTHS_12_18,
        "Cups",
        Difficulty.BEGINNER,
        "Stack cups and knock them down.",
    ),
    (
        "ACT-0925",
        "Running Races",
        Domain.MOTOR,
        AgeRange.MONTHS_24_36,
        "None",
        Difficulty.BEGINNER,
        "Race across the yard.",
    ),  # two bands older
    (
        "ACT-0926",
        "Talking to the Bump",
        Domain.LANGUAGE,
        AgeRange.PRENATAL,
        "None",
        Difficulty.BEGINNER,
        "Talk to your baby before birth.",
    ),
]


class ExploreTestCase(APITestCase):
    def setUp(self):
        embeddings.set_encoder(FakeEncoder())
        self.addCleanup(embeddings.set_encoder, None)
        self.caregiver = User.objects.create_user(username="carer@example.com")
        self.child = ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Amani",
            date_of_birth=timezone.localdate() - datetime.timedelta(days=270),  # ~9m
            interests=["water"],
        )
        self.a = {}
        for aid, name, domain, age, materials, level, text in ACTIVITIES:
            self.a[aid] = DevelopmentalActivity.objects.create(
                **activity_fields(
                    activity_id=aid,
                    activity_name=name,
                    developmental_domain=domain,
                    age_range=age,
                    materials=materials,
                    difficulty_level=level,
                    description=text,
                    content_status=ContentStatus.PUBLISHED,
                )
            )
        call_command("embed_activities", stdout=StringIO())
        self.client.force_authenticate(self.caregiver)

    def ids(self, found):
        return [f.activity.activity_id for f in found]


class BrowseTests(ExploreTestCase):
    def test_pool_suits_the_childs_age(self):
        ids = self.ids(browse.browse(self.child))
        self.assertCountEqual(ids, ["ACT-0921", "ACT-0922", "ACT-0923", "ACT-0924"])

    def test_before_birth_only_pregnancy_activities(self):
        self.child.date_of_birth = timezone.localdate() + datetime.timedelta(days=60)
        self.child.save()
        self.assertEqual(self.ids(browse.browse(self.child)), ["ACT-0926"])

    def test_completed_activities_are_left_out(self):
        rec = Recommendation.objects.create(
            child=self.child,
            activity=self.a["ACT-0921"],
            similarity_score=0.5,
            ranking_score=0.5,
        )
        CompletedActivity.objects.create(recommendation=rec)
        self.assertNotIn("ACT-0921", self.ids(browse.browse(self.child)))

    def test_filters(self):
        self.assertEqual(
            self.ids(
                browse.browse(self.child, area=Domain.LANGUAGE, no_materials=True)
            ),
            ["ACT-0922"],
        )
        self.assertNotIn("ACT-0923", self.ids(browse.browse(self.child, quick=True)))
        SavedActivity.objects.create(child=self.child, activity=self.a["ACT-0924"])
        saved = browse.browse(self.child, saved_only=True)
        self.assertEqual(self.ids(saved), ["ACT-0924"])
        self.assertTrue(saved[0].saved)

    def test_search_ranks_by_meaning(self):
        found = browse.browse(self.child, query="splash water in the bath")
        self.assertEqual(found[0].activity.activity_id, "ACT-0921")

    def test_interests_query(self):
        self.assertIn("water", browse.interests_query(self.child))
        self.child.interests = []
        self.assertEqual(browse.interests_query(self.child), "")


class ExploreAPITests(ExploreTestCase):
    def list_url(self, **params):
        url = reverse("child-activities", args=[self.child.pk])
        return url + (
            "?" + "&".join(f"{k}={v}" for k, v in params.items()) if params else ""
        )

    def test_lists_activities_with_saved_flags(self):
        SavedActivity.objects.create(child=self.child, activity=self.a["ACT-0922"])
        body = self.client.get(self.list_url()).json()
        by_id = {r["activity_id"]: r for r in body["results"]}
        self.assertTrue(by_id["ACT-0922"]["saved"])
        self.assertFalse(by_id["ACT-0921"]["saved"])
        self.assertIn("description", by_id["ACT-0921"])

    def test_search_and_interests(self):
        body = self.client.get(self.list_url(q="splash water in the bath")).json()
        self.assertEqual(body["results"][0]["activity_id"], "ACT-0921")
        body = self.client.get(self.list_url(**{"for": "interests"})).json()
        self.assertIn("water", body["query"])
        self.assertEqual(body["results"][0]["activity_id"], "ACT-0921")

    def test_limit_is_checked(self):
        self.assertEqual(self.client.get(self.list_url(limit=0)).status_code, 400)
        self.assertEqual(self.client.get(self.list_url(limit="x")).status_code, 400)

    def test_save_and_unsave(self):
        url = reverse("child-saved-activity", args=[self.child.pk, "ACT-0921"])
        self.assertEqual(self.client.put(url).status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.client.put(url).status_code, status.HTTP_200_OK)
        self.assertEqual(SavedActivity.objects.count(), 1)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(SavedActivity.objects.exists())

    def test_try_pins_it_in_the_ideas(self):
        url = reverse("child-activity-try", args=[self.child.pk, "ACT-0924"])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        first = response.json()["recommendations"][0]
        self.assertEqual(first["activity_id"], "ACT-0924")
        self.assertTrue(first["pinned"])
        self.assertTrue(first["explanation"].startswith("You chose this for Amani"))

    def test_try_refuses_an_activity_for_another_stage(self):
        url = reverse("child-activity-try", args=[self.child.pk, "ACT-0926"])
        self.assertEqual(self.client.post(url).status_code, 400)

    def test_only_the_childs_caregiver(self):
        other = User.objects.create_user(username="other@example.com")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(self.list_url()).status_code, 404)
        url = reverse("child-saved-activity", args=[self.child.pk, "ACT-0921"])
        self.assertEqual(self.client.put(url).status_code, 404)
