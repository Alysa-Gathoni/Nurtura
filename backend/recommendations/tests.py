import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from activities.choices import ContentStatus
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from profiles.models import ChildProfile

from .models import Recommendation


def make_child(username="caregiver", name="Amani"):
    caregiver = get_user_model().objects.create_user(
        username=username, password="x-test-pass"
    )
    return ChildProfile.objects.create(
        caregiver=caregiver, name=name, date_of_birth=datetime.date(2025, 6, 1)
    )


class RecommendationTests(TestCase):
    def setUp(self):
        self.child = make_child()
        self.activity = DevelopmentalActivity.objects.create(
            **activity_fields(content_status=ContentStatus.PUBLISHED)
        )

    def recommend(self, **kwargs):
        fields = {
            "child": self.child,
            "activity": self.activity,
            "similarity_score": 0.82,
            "ranking_score": 0.75,
        }
        fields.update(kwargs)
        return Recommendation.objects.create(**fields)

    def test_create_links_child_and_activity(self):
        rec = self.recommend()
        rec.full_clean()
        self.assertEqual(self.child.recommendations.get(), rec)
        self.assertEqual(self.activity.recommendations.get(), rec)
        self.assertEqual(rec.explanation, "")
        self.assertEqual(str(rec), "Tummy Time for Amani")

    def test_only_published_activities_can_be_recommended(self):
        for status in (ContentStatus.DRAFT, ContentStatus.UNDER_REVIEW):
            with self.subTest(status=status):
                activity = DevelopmentalActivity.objects.create(
                    **activity_fields(
                        activity_id=f"ACT-{status}",
                        activity_name=f"Activity {status}",
                        content_status=status,
                    )
                )
                rec = Recommendation(
                    child=self.child,
                    activity=activity,
                    similarity_score=0.5,
                    ranking_score=0.5,
                )
                with self.assertRaises(ValidationError) as ctx:
                    rec.full_clean()
                self.assertIn("activity", ctx.exception.message_dict)

    def test_similarity_score_validated(self):
        for bad in (-1.5, 1.01):
            with self.subTest(score=bad):
                rec = Recommendation(
                    child=self.child,
                    activity=self.activity,
                    similarity_score=bad,
                    ranking_score=0.5,
                )
                with self.assertRaises(ValidationError) as ctx:
                    rec.full_clean()
                self.assertIn("similarity_score", ctx.exception.message_dict)

    def test_similarity_score_enforced_by_database(self):
        with self.assertRaises(IntegrityError):
            self.recommend(similarity_score=1.5)

    def test_activity_with_recommendations_cannot_be_deleted(self):
        self.recommend()
        with self.assertRaises(ProtectedError):
            self.activity.delete()

    def test_deleting_child_deletes_recommendations(self):
        self.recommend()
        self.child.delete()
        self.assertEqual(Recommendation.objects.count(), 0)

    def test_ordered_newest_first_then_by_ranking(self):
        earlier = timezone.now() - datetime.timedelta(days=1)
        now = timezone.now()
        self.recommend(ranking_score=0.9, date_generated=earlier)
        self.recommend(ranking_score=0.4, date_generated=now)
        self.recommend(ranking_score=0.8, date_generated=now)
        scores = [r.ranking_score for r in Recommendation.objects.all()]
        self.assertEqual(scores, [0.8, 0.4, 0.9])
