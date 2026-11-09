"""Tests for the milestone tracker and the weekly observation (#192)."""

import datetime

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from activities.choices import ContentStatus, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from feedback.models import CompletedActivity, Feedback
from recommendations.models import Recommendation

from . import observation, tracker
from .models import ChildProfile, DevelopmentalMilestone
from .test_guidelines import DOB, on_age, reference

User = get_user_model()
Status = DevelopmentalMilestone.Status
TODAY = on_age(10)  # a 10-month-old


class TrackerTestCase(APITestCase):
    def setUp(self):
        self.caregiver = User.objects.create_user(username="carer@example.com")
        self.child = ChildProfile.objects.create(
            caregiver=self.caregiver, name="Amani", date_of_birth=DOB
        )
        self.old = reference("CDC-02M-LA-01", 2, description="Coos")
        self.due = reference("CDC-09M-LA-01", 9, description="Babbles")
        self.soon = reference("CDC-12M-LA-01", 12, description="Waves")
        self.later = reference("CDC-18M-LA-01", 18, description="Says words")
        self.motor = reference("CDC-09M-MO-01", 9, Domain.MOTOR, description="Sits")

    def observe(self, ref, status_value, months_old):
        return self.child.record_milestone(
            reference=ref, status=status_value, observation_date=on_age(months_old)
        )


class TrackerTests(TrackerTestCase):
    def area(self, result, domain):
        return next(a for a in result["areas"] if a["domain"] == domain)

    def test_shows_recent_and_coming_milestones_by_area(self):
        result = tracker.tracker(self.child, TODAY)
        self.assertFalse(result["prenatal"])
        self.assertEqual(
            [a["domain"] for a in result["areas"]],
            ["Motor", "Socio-Emotional", "Language", "Cognitive"],
        )
        language = self.area(result, "Language")
        # 2 months is more than 6 months ago and unrecorded; 18 is too far ahead.
        self.assertEqual(
            [m["key"] for m in language["milestones"]],
            ["CDC-09M-LA-01", "CDC-12M-LA-01"],
        )
        due, soon = language["milestones"]
        self.assertTrue(due["due"])
        self.assertFalse(soon["due"])
        self.assertEqual(due["status"], "")

    def test_recorded_milestones_show_whatever_their_age(self):
        self.observe(self.old, Status.ACHIEVED, 3)
        self.observe(self.due, Status.NOT_YET, 9.5)
        self.observe(self.due, Status.EMERGING, 10)
        language = self.area(tracker.tracker(self.child, TODAY), "Language")
        by_key = {m["key"]: m for m in language["milestones"]}
        self.assertEqual(by_key["CDC-02M-LA-01"]["status"], "achieved")
        self.assertEqual(by_key["CDC-02M-LA-01"]["observed_at_months"], 3)
        self.assertEqual(by_key["CDC-09M-LA-01"]["status"], "emerging")  # latest

    def test_nothing_to_track_before_birth(self):
        result = tracker.tracker(self.child, DOB - datetime.timedelta(days=30))
        self.assertTrue(result["prenatal"])
        self.assertEqual(result["areas"], [])


class ObservationTests(TrackerTestCase):
    def recommend(self, n=1):
        recs = []
        for i in range(n):
            activity = DevelopmentalActivity.objects.create(
                **activity_fields(
                    activity_id=f"ACT-09{i:02d}",
                    activity_name=f"Talking game {i}",
                    developmental_domain=Domain.LANGUAGE,
                    content_status=ContentStatus.PUBLISHED,
                )
            )
            recs.append(
                Recommendation.objects.create(
                    child=self.child,
                    activity=activity,
                    similarity_score=0.5,
                    ranking_score=0.5,
                )
            )
        return recs

    def text(self):
        return observation.observation(self.child, TODAY)["text"]

    def test_nothing_this_week(self):
        self.assertIn("No activities were marked done this week", self.text())
        self.assertIn("Record a few milestones", self.text())

    def test_counts_activities_and_how_they_went(self):
        recs = self.recommend(3)
        for rec in recs:
            CompletedActivity.objects.create(recommendation=rec, completion_date=TODAY)
        Feedback.objects.create(recommendation=recs[0], outcome="went_well")
        Feedback.objects.create(recommendation=recs[1], interest="loved_it")
        Feedback.objects.create(recommendation=recs[2], outcome="didnt_work")
        text = self.text()
        self.assertIn("This week Amani tried 3 activities, and 2 went well.", text)
        self.assertIn("Talking ideas seem to suit Amani best", text)

    def test_last_weeks_activities_dont_count(self):
        (rec,) = self.recommend()
        CompletedActivity.objects.create(
            recommendation=rec, completion_date=TODAY - datetime.timedelta(days=8)
        )
        self.assertIn("No activities were marked done this week", self.text())

    def test_milestones_noted_and_what_to_focus_on(self):
        self.observe(self.motor, Status.ACHIEVED, 10)
        self.observe(self.due, Status.NOT_YET, 10)
        result = observation.observation(self.child, TODAY)
        self.assertIn("You noted “Sits”: lovely progress.", result["text"])
        self.assertIn(
            "Next, ideas for talking could help with “Babbles”.", result["text"]
        )
        self.assertEqual(result["focus_domain"], "Language")

    def test_never_comparative_or_diagnostic(self):
        self.observe(self.due, Status.NOT_YET, 10)
        text = self.text().lower()
        for word in (
            "most children",
            "behind",
            "delay",
            "diagnos",
            "worry",
            "other children",
        ):
            self.assertNotIn(word, text)

    def test_pregnancy(self):
        self.child.date_of_birth = TODAY + datetime.timedelta(days=60)
        self.child.save()
        self.assertIn("pregnancy ideas", self.text())


class EndpointTests(TrackerTestCase):
    def test_owner_gets_tracker_and_observation(self):
        self.client.force_authenticate(self.caregiver)
        for name in ("child-tracker", "child-observation"):
            response = self.client.get(reverse(name, args=[self.child.pk]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = self.client.get(reverse("child-tracker", args=[self.child.pk])).json()
        self.assertEqual(len(body["areas"]), 4)

    def test_other_caregivers_get_404(self):
        other = User.objects.create_user(username="other@example.com")
        self.client.force_authenticate(other)
        for name in ("child-tracker", "child-observation"):
            response = self.client.get(reverse(name, args=[self.child.pk]))
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
