"""Tests for completion (FR-14) and feedback (FR-15) on recommendations."""

import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from activities.choices import ContentStatus
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from recommendations.models import Recommendation
from recommendations.tests import make_child

from .manager import MAX_COMMENT_LENGTH, FeedbackManager
from .models import CompletedActivity, Feedback

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


class FeedbackManagerTests(OwnRecommendationTestCase):
    def submit(self, rating=4, comment="", caregiver=None):
        return FeedbackManager.submit(
            caregiver or self.caregiver, self.recommendation.pk, rating, comment
        )

    def test_records_then_replaces_one_entry(self):
        feedback, created = self.submit(4, "  Loved it  ")
        self.assertTrue(created)
        self.assertEqual((feedback.rating, feedback.comment), (4, "Loved it"))
        feedback, created = self.submit(2, "Too hard for now")
        self.assertFalse(created)
        self.assertEqual(Feedback.objects.count(), 1)
        self.assertEqual(Feedback.objects.get().rating, 2)

    def test_rating_must_be_a_whole_number_from_1_to_5(self):
        for rating in (0, 6, -1, 3.5, True, "4", None):
            with self.subTest(rating=rating):
                with self.assertRaises(ValidationError) as caught:
                    self.submit(rating)
                self.assertIn("rating", caught.exception.message_dict)
        self.assertFalse(Feedback.objects.exists())

    def test_comment_length_is_limited(self):
        self.submit(3, "x" * MAX_COMMENT_LENGTH)
        with self.assertRaises(ValidationError) as caught:
            self.submit(3, "x" * (MAX_COMMENT_LENGTH + 1))
        self.assertIn("comment", caught.exception.message_dict)

    def test_only_the_childs_caregiver(self):
        other = User.objects.create_user(username="other@example.com")
        with self.assertRaises(Recommendation.DoesNotExist):
            self.submit(caregiver=other)
        with self.assertRaises(Recommendation.DoesNotExist):
            FeedbackManager.for_caregiver(other, self.recommendation.pk)
        self.assertFalse(Feedback.objects.exists())

    def test_completion_is_not_required(self):
        self.assertFalse(CompletedActivity.objects.exists())
        _, created = self.submit(1, "Not suitable for us")
        self.assertTrue(created)


class FeedbackAPITests(OwnRecommendationTestCase):
    def url(self, pk=None):
        return reverse("recommendation-feedback", args=[pk or self.recommendation.pk])

    def put(self, data=None, pk=None):
        return self.client.put(
            self.url(pk), data or {"rating": 5, "comment": "Great"}, format="json"
        )

    def test_submit_read_back_and_show_on_the_card(self):
        self.assertIsNone(self.card()["feedback"])
        self.assertEqual(self.client.get(self.url()).status_code, 404)

        response = self.put()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(set(body), {"rating", "comment", "date_submitted"})
        self.assertEqual((body["rating"], body["comment"]), (5, "Great"))
        self.assertEqual(self.client.get(self.url()).json(), body)
        self.assertEqual(self.card()["feedback"], body)

        again = self.put({"rating": 3})
        self.assertEqual(again.status_code, status.HTTP_200_OK)
        self.assertEqual((again.json()["rating"], again.json()["comment"]), (3, ""))
        self.assertEqual(self.card()["feedback"]["rating"], 3)

    def test_invalid_input_is_a_400_with_field_messages(self):
        for data, field in (
            ({"rating": 9}, "rating"),
            ({"rating": "great"}, "rating"),
            ({"comment": "no rating"}, "rating"),
            ({"rating": 3, "comment": "x" * (MAX_COMMENT_LENGTH + 1)}, "comment"),
        ):
            with self.subTest(data=data):
                response = self.put(data)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.json())
        self.assertFalse(Feedback.objects.exists())

    def test_missing_recommendation_is_404(self):
        self.assertEqual(self.put(pk=999999).status_code, status.HTTP_404_NOT_FOUND)

    def test_only_the_childs_caregiver_may_submit_or_read(self):
        self.put()
        self.as_others(self.put)
        self.as_others(lambda: self.client.get(self.url()))
        self.assertEqual(Feedback.objects.get().rating, 5)
