"""Tests for the "Well done!" sheet: interest and observed skills (#185)."""

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from activities.choices import ContentStatus, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from profiles import privacy
from profiles.models import ChildProfile, DevelopmentalMilestone, ReferenceMilestone
from recommendations.models import Recommendation

from . import observations
from .manager import FeedbackManager
from .models import Feedback

User = get_user_model()
Status = DevelopmentalMilestone.Status


def reference(key, age, domain=Domain.LANGUAGE):
    return ReferenceMilestone.objects.create(
        milestone_key=key,
        source="CDC",
        expected_age_months=Decimal(str(age)),
        domain=domain,
        description=f"Milestone {key}",
        source_reference="Test",
    )


class ObservationTestCase(APITestCase):
    def setUp(self):
        self.caregiver = User.objects.create_user(username="carer@example.com")
        privacy.record_consent(self.caregiver)
        self.child = ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Amani",
            date_of_birth=timezone.localdate() - datetime.timedelta(days=305),  # ~10m
        )
        activity = DevelopmentalActivity.objects.create(
            **activity_fields(
                developmental_domain=Domain.LANGUAGE,
                content_status=ContentStatus.PUBLISHED,
            )
        )
        self.rec = Recommendation.objects.create(
            child=self.child, activity=activity, similarity_score=0.5, ranking_score=0.5
        )
        self.due = reference("CDC-09M-LA-01", 9)
        self.soon = reference("CDC-12M-LA-01", 12)
        self.old = reference("CDC-02M-LA-01", 2)  # more than 6 months ago
        self.later = reference("CDC-18M-LA-01", 18)  # more than 3 months ahead
        self.motor = reference("CDC-09M-MO-01", 9, Domain.MOTOR)  # other area
        self.client.force_authenticate(self.caregiver)

    def keys(self):
        return [ref.milestone_key for ref, _ in observations.observable(self.rec)]


class ObservableTests(ObservationTestCase):
    def test_offers_due_and_coming_milestones_of_the_activitys_area(self):
        self.assertEqual(self.keys(), ["CDC-09M-LA-01", "CDC-12M-LA-01"])

    def test_achieved_milestones_are_not_offered(self):
        self.child.record_milestone(reference=self.due, status=Status.ACHIEVED)
        self.assertEqual(self.keys(), ["CDC-12M-LA-01"])

    def test_nothing_before_birth(self):
        self.child.date_of_birth = timezone.localdate() + datetime.timedelta(days=60)
        self.child.save()
        self.assertEqual(self.keys(), [])

    def test_api_lists_them_with_status(self):
        self.child.record_milestone(reference=self.due, status=Status.NOT_YET)
        url = reverse("recommendation-observable", args=[self.rec.pk])
        skills = self.client.get(url).json()["skills"]
        self.assertEqual(
            [(s["key"], s["status"]) for s in skills],
            [("CDC-09M-LA-01", "not_yet"), ("CDC-12M-LA-01", "")],
        )


class RecordObservedTests(ObservationTestCase):
    def submit(self, **kwargs):
        return FeedbackManager.submit(
            self.caregiver, self.rec.pk, outcome="went_well", **kwargs
        )

    def test_ticked_skills_are_recorded_as_emerging(self):
        feedback, _ = self.submit(observed=["CDC-09M-LA-01"])
        self.assertEqual(feedback.recorded, ["Milestone CDC-09M-LA-01"])
        latest = self.child.milestones.get(reference=self.due)
        self.assertEqual(latest.status, Status.EMERGING)
        # The profile is refreshed: Emerging raises Language priority.
        self.assertIn("Language", self.child.developmental_profile.ranked_domains[:1])

    def test_already_emerging_is_left_alone(self):
        self.child.record_milestone(reference=self.due, status=Status.EMERGING)
        feedback, _ = self.submit(observed=["CDC-09M-LA-01"])
        self.assertEqual(feedback.recorded, [])
        self.assertEqual(self.child.milestones.filter(reference=self.due).count(), 1)

    def test_skills_not_offered_are_refused(self):
        from django.core.exceptions import ValidationError

        for key in ("CDC-09M-MO-01", "CDC-02M-LA-01", "nope"):
            with self.subTest(key=key), self.assertRaises(ValidationError) as caught:
                self.submit(observed=[key])
            self.assertIn("observed", caught.exception.message_dict)
        self.assertFalse(self.child.milestones.exists())

    def test_recording_needs_privacy_consent(self):
        from django.core.exceptions import ValidationError

        self.caregiver.privacy_notice_version = ""
        self.caregiver.save()
        with self.assertRaises(ValidationError) as caught:
            self.submit(observed=["CDC-09M-LA-01"])
        self.assertIn("observed", caught.exception.message_dict)


class InterestAndOptionalRatingTests(ObservationTestCase):
    def url(self):
        return reverse("recommendation-feedback", args=[self.rec.pk])

    def test_interest_without_a_rating(self):
        response = self.client.put(
            self.url(),
            {"outcome": "went_well", "interest": "loved_it", "observed": []},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual((body["interest"], body["rating"]), ("loved_it", None))
        self.assertEqual(body["recorded"], [])
        self.assertIsNone(Feedback.objects.get().rating)

    def test_unknown_interest_is_refused(self):
        response = self.client.put(
            self.url(), {"outcome": "went_well", "interest": "ecstatic"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("interest", response.json())

    def test_observed_skills_through_the_api(self):
        response = self.client.put(
            self.url(),
            {"outcome": "partly", "observed": ["CDC-12M-LA-01"]},
            format="json",
        )
        self.assertEqual(response.json()["recorded"], ["Milestone CDC-12M-LA-01"])
