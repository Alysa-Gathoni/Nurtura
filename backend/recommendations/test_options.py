"""Tests for the options offered after feedback (#177)."""

import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from activities.choices import AgeRange, ContentStatus, Difficulty, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from feedback.models import CompletedActivity, Feedback
from profiles.models import ChildProfile

from . import embeddings, generation
from .models import Recommendation
from .options import MAX_OPTIONS, UPSET_TIP, options_for
from .test_embeddings import FakeEncoder

User = get_user_model()

# A 7-month-old (6-12 months) and a small catalogue around one activity.
ACTIVITIES = [
    (
        "ACT-0901",
        "Naming Pictures Together",
        Domain.LANGUAGE,
        AgeRange.MONTHS_6_12,
        Difficulty.INTERMEDIATE,
        "Picture book",
        "Look at a picture book and name each picture, pointing as you talk.",
    ),
    (
        "ACT-0902",
        "Naming Toys Together",
        Domain.LANGUAGE,
        AgeRange.MONTHS_6_12,
        Difficulty.BEGINNER,
        "Toys",
        "Hold up a toy, name it, and wait for your baby to look or babble back.",
    ),
    (
        "ACT-0903",
        "Talk About Your Day",
        Domain.LANGUAGE,
        AgeRange.MONTHS_6_12,
        Difficulty.BEGINNER,
        "None",
        "Talk to your baby as you cook and clean, naming what you do.",
    ),
    (
        "ACT-0904",
        "Copy the Coos",
        Domain.LANGUAGE,
        AgeRange.MONTHS_3_6,
        Difficulty.BEGINNER,
        "None",
        "Copy your baby's coos and pause so they can answer you.",
    ),
    (
        "ACT-0905",
        "First Words Game",
        Domain.LANGUAGE,
        AgeRange.MONTHS_12_18,
        Difficulty.BEGINNER,
        "None",
        "Ask your toddler to name things you point to and cheer every try.",
    ),
    (
        "ACT-0906",
        "Calm Cuddle and Rocking",
        Domain.SOCIO_EMOTIONAL,
        AgeRange.MONTHS_6_12,
        Difficulty.BEGINNER,
        "None",
        "Hold your baby close, rock gently and hum to help them settle and calm.",
    ),
    (
        "ACT-0907",
        "Stack and Topple",
        Domain.COGNITIVE,
        AgeRange.MONTHS_6_12,
        Difficulty.BEGINNER,
        "Blocks",
        "Stack two soft blocks and knock them down together.",
    ),
    (
        "ACT-0908",
        "Talking to the Bump",
        Domain.LANGUAGE,
        AgeRange.PRENATAL,
        Difficulty.BEGINNER,
        "None",
        "Talk and sing to your baby before birth.",
    ),
]


class OptionsTestCase(TestCase):
    def setUp(self):
        embeddings.set_encoder(FakeEncoder())
        self.addCleanup(embeddings.set_encoder, None)
        self.caregiver = User.objects.create_user(username="carer@example.com")
        today = timezone.localdate()
        self.child = ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Amani",
            date_of_birth=today - datetime.timedelta(days=230),  # ~7.5 months
        )
        self.activities = {}
        for aid, name, domain, age, level, materials, text in ACTIVITIES:
            self.activities[aid] = DevelopmentalActivity.objects.create(
                **activity_fields(
                    activity_id=aid,
                    activity_name=name,
                    developmental_domain=domain,
                    age_range=age,
                    difficulty_level=level,
                    materials=materials,
                    description=text,
                    content_status=ContentStatus.PUBLISHED,
                )
            )
        call_command("embed_activities", stdout=StringIO())

    def recommend(self, aid):
        return Recommendation.objects.create(
            child=self.child,
            activity=self.activities[aid],
            similarity_score=0.5,
            ranking_score=0.5,
        )

    def feedback(self, recommendation, outcome, issues=()):
        return Feedback.objects.create(
            recommendation=recommendation,
            rating=3,
            outcome=outcome,
            issues=list(issues),
        )

    def options(self, aid, outcome, issues=(), exclude=()):
        rec = self.recommend(aid)
        fb = self.feedback(rec, outcome, issues)
        return options_for(rec, fb, {self.activities[a].pk for a in exclude})

    def ids(self, options):
        return [o.activity.activity_id for o in options]


class OptionsForTests(OptionsTestCase):
    def test_no_feedback_or_no_outcome_gives_nothing(self):
        rec = self.recommend("ACT-0901")
        self.assertEqual(options_for(rec, None), [])
        self.assertEqual(options_for(rec, self.feedback(rec, "")), [])

    def test_too_hard_offers_an_easier_one_in_the_same_band(self):
        first, *_ = self.options("ACT-0901", "didnt_work", ["too_hard"])
        self.assertEqual(first.reason, "too_hard")
        self.assertEqual(first.title, "An easier one")
        self.assertEqual(first.activity.age_range, AgeRange.MONTHS_6_12)
        self.assertEqual(first.activity.difficulty_level, Difficulty.BEGINNER)
        self.assertIn("“Naming Pictures Together” was too hard", first.why)

    def test_too_hard_falls_back_to_the_band_below(self):
        first, *_ = self.options("ACT-0902", "didnt_work", ["too_hard"])
        self.assertEqual(first.activity.activity_id, "ACT-0904")

    def test_too_easy_offers_a_step_up(self):
        first, *_ = self.options("ACT-0902", "partly", ["too_easy"])
        self.assertEqual(first.activity.activity_id, "ACT-0901")  # harder, same band

    def test_no_materials_needs_nothing(self):
        first, *_ = self.options("ACT-0901", "didnt_work", ["no_materials"])
        self.assertEqual(first.activity.activity_id, "ACT-0903")

    def test_upset_offers_a_calm_one_with_a_tip(self):
        first, *_ = self.options("ACT-0901", "didnt_work", ["child_upset"])
        self.assertEqual(first.activity.activity_id, "ACT-0906")
        self.assertEqual(first.tip, UPSET_TIP)

    def test_went_well_offers_more_like_this(self):
        options = self.options("ACT-0901", "went_well")
        self.assertEqual(options[0].reason, "more_like_this")
        self.assertEqual(options[0].activity.developmental_domain, Domain.LANGUAGE)

    def test_at_most_three_distinct_and_never_prenatal_or_itself(self):
        options = self.options(
            "ACT-0901",
            "didnt_work",
            ["too_hard", "not_interested", "no_materials", "no_time"],
        )
        ids = self.ids(options)
        self.assertLessEqual(len(ids), MAX_OPTIONS)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn("ACT-0901", ids)
        self.assertNotIn("ACT-0908", ids)

    def test_excluded_activities_are_never_offered(self):
        options = self.options(
            "ACT-0901", "didnt_work", ["no_materials"], exclude=["ACT-0903"]
        )
        self.assertNotIn("ACT-0903", self.ids(options))


class OptionsAPITests(OptionsTestCase, APITestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.caregiver)
        self.rec = self.recommend("ACT-0901")

    def url(self):
        return reverse("recommendation-options", args=[self.rec.pk])

    def test_empty_until_there_is_feedback(self):
        self.assertEqual(self.client.get(self.url()).json(), {"options": []})

    def test_lists_options_with_why_and_the_activity(self):
        self.feedback(self.rec, "didnt_work", ["no_materials"])
        body = self.client.get(self.url()).json()
        first = body["options"][0]
        self.assertEqual(set(first), {"reason", "title", "why", "tip", "activity"})
        self.assertEqual(first["activity"]["activity_id"], "ACT-0903")
        self.assertEqual(first["activity"]["materials"], "None")

    def test_only_the_childs_caregiver(self):
        other = User.objects.create_user(username="other@example.com")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        admin = User.objects.create_user(
            username="admin@example.com", role=User.Role.ADMINISTRATOR
        )
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get(self.url()).status_code, 403)

    def test_post_pins_the_choice_first_and_keeps_it_until_done(self):
        self.feedback(self.rec, "didnt_work", ["no_materials"])
        response = self.client.post(
            self.url(), {"activity_id": "ACT-0903"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        first = response.json()["recommendations"][0]
        self.assertEqual(first["activity_id"], "ACT-0903")
        self.assertTrue(first["pinned"])
        self.assertTrue(first["explanation"].startswith("You didn't have the"))

        # Still first in a later batch...
        again = generation.generate(self.child.pk, self.caregiver)
        self.assertEqual(again.recommendations[0].activity.activity_id, "ACT-0903")
        self.assertTrue(again.recommendations[0].pinned)

        # ...until it is done.
        CompletedActivity.objects.create(recommendation=again.recommendations[0])
        later = generation.generate(self.child.pk, self.caregiver)
        self.assertNotIn(
            "ACT-0903", [r.activity.activity_id for r in later.recommendations]
        )

    def test_post_refuses_anything_not_offered(self):
        self.feedback(self.rec, "didnt_work", ["no_materials"])
        response = self.client.post(
            self.url(), {"activity_id": "ACT-0907"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("activity_id", response.json())
