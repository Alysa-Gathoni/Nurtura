"""Tests for marking recommendations complete (FR-14)."""

import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from activities.choices import ContentStatus
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from recommendations.models import Recommendation
from recommendations.tests import make_child

from .models import CompletedActivity

User = get_user_model()


class OwnRecommendationTestCase(APITestCase):
    """One caregiver's child with a stored recommendation."""

    def setUp(self):
        self.child = make_child()
        self.caregiver = self.child.caregiver
        activity = DevelopmentalActivity.objects.create(
            **activity_fields(content_status=ContentStatus.PUBLISHED)
        )
        self.recommendation = Recommendation.objects.create(
            child=self.child,
            activity=activity,
            similarity_score=0.8,
            ranking_score=0.7,
        )
        self.client.force_authenticate(self.caregiver)

    def card(self):
        url = reverse("child-recommendations", args=[self.child.pk])
        return self.client.get(url).json()["recommendations"][0]

    def as_others(self, call):
        """call() as another caregiver (404) and as an administrator (403)."""
        other, _ = User.objects.get_or_create(username="other@example.com")
        admin, _ = User.objects.get_or_create(
            username="admin@example.com", role=User.Role.ADMINISTRATOR
        )
        self.client.force_authenticate(other)
        self.assertEqual(call().status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(admin)
        self.assertEqual(call().status_code, status.HTTP_403_FORBIDDEN)
        self.client.logout()
        self.assertEqual(call().status_code, status.HTTP_401_UNAUTHORIZED)


class CompletionAPITests(OwnRecommendationTestCase):
    def url(self, pk=None):
        return reverse("recommendation-completion", args=[pk or self.recommendation.pk])

    def put(self, data=None, pk=None):
        return self.client.put(self.url(pk), data or {}, format="json")

    def test_card_shows_no_completion_until_marked(self):
        self.assertIsNone(self.card()["completion"])

    @mock.patch(
        "django.utils.timezone.localdate", return_value=datetime.date(2026, 10, 14)
    )
    def test_mark_completed_then_shown_on_the_card(self, _):
        response = self.put()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        expected = {"status": "completed", "completion_date": "2026-10-14"}
        self.assertEqual(response.json(), expected)
        self.assertEqual(self.card()["completion"], expected)

    def test_change_to_partly_done_updates_the_same_record(self):
        self.put()
        response = self.put({"status": "partially_completed"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "partially_completed")
        self.assertEqual(CompletedActivity.objects.count(), 1)

    def test_unknown_status_is_rejected(self):
        response = self.put({"status": "skipped"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.json())
        self.assertFalse(CompletedActivity.objects.exists())

    def test_delete_undoes_and_is_safe_to_repeat(self):
        self.put()
        for _ in range(2):
            response = self.client.delete(self.url())
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CompletedActivity.objects.exists())
        self.assertIsNone(self.card()["completion"])

    def test_missing_recommendation_is_404(self):
        self.assertEqual(self.put(pk=999999).status_code, status.HTTP_404_NOT_FOUND)

    def test_only_the_childs_caregiver_may_mark_or_undo(self):
        self.as_others(self.put)
        self.as_others(lambda: self.client.delete(self.url()))
        self.assertFalse(CompletedActivity.objects.exists())
