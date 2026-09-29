from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from recommendations.models import Recommendation
from recommendations.tests import make_child

from .models import CompletedActivity, Feedback


class FeedbackTestCase(TestCase):
    def setUp(self):
        activity = DevelopmentalActivity.objects.create(**activity_fields())
        self.recommendation = Recommendation.objects.create(
            child=make_child(),
            activity=activity,
            similarity_score=0.82,
            ranking_score=0.75,
        )


class CompletedActivityTests(FeedbackTestCase):
    def test_defaults(self):
        completion = CompletedActivity.objects.create(
            recommendation=self.recommendation
        )
        completion.full_clean()
        self.assertEqual(completion.status, CompletedActivity.Status.COMPLETED)
        self.assertEqual(completion.completion_date, timezone.localdate())
        self.assertEqual(self.recommendation.completion, completion)

    def test_no_row_means_not_completed(self):
        self.assertFalse(hasattr(self.recommendation, "completion"))

    def test_at_most_one_completion_per_recommendation(self):
        CompletedActivity.objects.create(recommendation=self.recommendation)
        with self.assertRaises(IntegrityError):
            CompletedActivity.objects.create(
                recommendation=self.recommendation,
                status=CompletedActivity.Status.PARTIALLY_COMPLETED,
            )

    def test_status_values(self):
        self.assertEqual(
            CompletedActivity.Status.labels, ["Completed", "Partially Completed"]
        )
        completion = CompletedActivity(
            recommendation=self.recommendation, status="skipped"
        )
        with self.assertRaises(ValidationError) as ctx:
            completion.full_clean()
        self.assertIn("status", ctx.exception.message_dict)


class FeedbackTests(FeedbackTestCase):
    def test_multiple_feedback_per_recommendation(self):
        Feedback.objects.create(recommendation=self.recommendation, rating=4)
        Feedback.objects.create(
            recommendation=self.recommendation, rating=5, comment="Loved it"
        )
        self.assertEqual(self.recommendation.feedback.count(), 2)

    def test_comment_optional(self):
        feedback = Feedback.objects.create(recommendation=self.recommendation, rating=3)
        feedback.full_clean()
        self.assertEqual(str(feedback), "3/5 on Tummy Time for Amani")

    def test_rating_validated(self):
        for bad in (0, 6):
            with self.subTest(rating=bad):
                feedback = Feedback(recommendation=self.recommendation, rating=bad)
                with self.assertRaises(ValidationError) as ctx:
                    feedback.full_clean()
                self.assertIn("rating", ctx.exception.message_dict)

    def test_rating_enforced_by_database(self):
        for bad in (0, 6):
            with self.subTest(rating=bad):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Feedback.objects.create(
                        recommendation=self.recommendation, rating=bad
                    )

    def test_deleting_recommendation_deletes_completion_and_feedback(self):
        CompletedActivity.objects.create(recommendation=self.recommendation)
        Feedback.objects.create(recommendation=self.recommendation, rating=4)
        self.recommendation.delete()
        self.assertEqual(CompletedActivity.objects.count(), 0)
        self.assertEqual(Feedback.objects.count(), 0)
