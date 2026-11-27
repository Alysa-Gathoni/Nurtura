"""Tests for the links between catalogue milestones (#289)."""

import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from activities.choices import ContentStatus, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from feedback import observations
from recommendations.models import Recommendation

from . import milestone_links
from .models import ChildProfile, DevelopmentalMilestone, ReferenceMilestone
from .tracker import tracker

User = get_user_model()
Status = DevelopmentalMilestone.Status
TODAY = datetime.date(2026, 11, 27)


class LinkTests(SimpleTestCase):
    def test_walking_with_help_settles_the_earlier_steps_only(self):
        implied = milestone_links.implied_keys(["WHO-MO-04"])
        self.assertEqual(
            implied,
            {
                "CDC-09M-MO-04",  # sits without support
                "WHO-MO-01",
                "WHO-MO-02",  # standing with assistance
                "CDC-12M-MO-01",  # pulls up to stand
                "CDC-12M-MO-02",  # its CDC twin, walks holding on
            },
        )
        # Crawling isn't in the sequence (not every child crawls), and later
        # steps aren't implied.
        self.assertNotIn("WHO-MO-03", implied)
        self.assertNotIn("WHO-MO-05", implied)

    def test_a_twin_settles_the_other(self):
        self.assertEqual(milestone_links.implied_keys(["WHO-MO-01"]), {"CDC-09M-MO-04"})
        self.assertEqual(milestone_links.implied_keys(["CDC-09M-MO-04"]), {"WHO-MO-01"})

    def test_other_skills_imply_nothing(self):
        self.assertEqual(milestone_links.implied_keys(["CDC-12M-MO-04"]), set())

    def test_the_who_wording_of_a_twin_is_hidden(self):
        self.assertTrue(milestone_links.is_hidden_twin("WHO-MO-01"))
        self.assertFalse(milestone_links.is_hidden_twin("CDC-09M-MO-04"))


class OfferedAndListedTests(TestCase):
    """Baby Amani from the phone test: 14 months, walks with help."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_milestones", stdout=StringIO())

    def setUp(self):
        caregiver = User.objects.create_user(username="carer@example.com")
        self.child = ChildProfile.objects.create(
            caregiver=caregiver, name="Amani", date_of_birth=datetime.date(2025, 9, 16)
        )
        self.child.record_milestone(
            reference=ReferenceMilestone.objects.get(milestone_key="WHO-MO-04"),
            status=Status.ACHIEVED,
            observation_date=datetime.date(2026, 11, 18),
        )
        activity = DevelopmentalActivity.objects.create(
            **activity_fields(
                developmental_domain=Domain.MOTOR,
                content_status=ContentStatus.PUBLISHED,
            )
        )
        self.rec = Recommendation.objects.create(
            child=self.child, activity=activity, similarity_score=0.5, ranking_score=0.5
        )

    def test_the_sheet_offers_nothing_settled_duplicated_or_too_early(self):
        keys = [
            ref.milestone_key
            for ref, _ in observations.observable(self.rec, on_date=TODAY)
        ]
        for settled in ("WHO-MO-02", "CDC-12M-MO-01", "CDC-12M-MO-02"):
            self.assertNotIn(settled, keys)
        for twin in ("WHO-MO-01", "WHO-MO-06"):
            self.assertNotIn(twin, keys)
        # Nothing from 9 months: more than 3 months before 14 months.
        self.assertFalse([k for k in keys if k.startswith("CDC-09M")])
        # What's near and not implied is still offered.
        self.assertIn("CDC-15M-MO-01", keys)  # a few steps on their own
        self.assertIn("CDC-12M-MO-04", keys)  # thumb and finger (fine motor)

    def test_the_tracker_leaves_out_settled_steps_but_keeps_records(self):
        motor = next(
            a
            for a in tracker(self.child, on_date=TODAY)["areas"]
            if a["domain"] == Domain.MOTOR
        )
        keys = [m["key"] for m in motor["milestones"]]
        self.assertIn("WHO-MO-04", keys)  # recorded: always listed
        for left_out in ("WHO-MO-02", "CDC-12M-MO-01", "CDC-09M-MO-04", "WHO-MO-01"):
            self.assertNotIn(left_out, keys)
        # Due skills that walking doesn't imply are still there to record.
        self.assertIn("CDC-09M-MO-03", keys)  # rakes food
