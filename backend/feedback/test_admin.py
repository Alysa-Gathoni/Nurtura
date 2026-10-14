"""Tests for the administrator feedback review (FR-16)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from activities.choices import ContentStatus, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from recommendations.models import Recommendation
from recommendations.tests import make_child

from .models import CompletedActivity, Feedback

User = get_user_model()
FEEDBACK_LIST = reverse("admin:feedback_feedback_changelist")
COMPLETED_LIST = reverse("admin:feedback_completedactivity_changelist")
ACTIVITY_LIST = reverse("admin:activities_developmentalactivity_changelist")


class FeedbackReviewTests(TestCase):
    def setUp(self):
        self.child = make_child(name="Zawadi Secretname")
        self.child.caregiver.email = "family@example.com"
        self.child.caregiver.save()

        def recommend(activity_id, name, domain):
            activity = DevelopmentalActivity.objects.create(
                **activity_fields(
                    activity_id=activity_id,
                    activity_name=name,
                    developmental_domain=domain,
                    content_status=ContentStatus.PUBLISHED,
                )
            )
            return Recommendation.objects.create(
                child=self.child,
                activity=activity,
                similarity_score=0.8,
                ranking_score=0.7,
            )

        self.songs = recommend("ACT-9001", "Singing Together", Domain.LANGUAGE)
        self.blocks = recommend("ACT-9002", "Block Tower", Domain.COGNITIVE)
        self.unrated = recommend("ACT-9003", "Rolling Ball", Domain.MOTOR)
        Feedback.objects.create(
            recommendation=self.songs, rating=5, comment="She loved the songs"
        )
        Feedback.objects.create(
            recommendation=self.blocks, rating=2, comment="Too hard for now"
        )
        CompletedActivity.objects.create(recommendation=self.songs)

        self.admin = User.objects.create_user(
            username="admin@example.com",
            password="x-test-pass",
            role=User.Role.ADMINISTRATOR,
        )
        self.client.force_login(self.admin)

    def test_feedback_is_listed_against_its_activity(self):
        page = self.client.get(FEEDBACK_LIST).content.decode()
        for text in (
            "ACT-9001",
            "Singing Together",
            "She loved the songs",
            "★★★★★ (5/5)",
            "Completed",
            "ACT-9002",
            "Too hard for now",
            "★★☆☆☆ (2/5)",
            "Not marked",
        ):
            self.assertIn(text, page)
        activity_url = reverse(
            "admin:activities_developmentalactivity_change",
            args=[self.songs.activity.pk],
        )
        self.assertIn(activity_url, page)

    def test_the_family_is_not_shown(self):
        for url in (
            FEEDBACK_LIST,
            reverse(
                "admin:feedback_feedback_change",
                args=[Feedback.objects.get(rating=5).pk],
            ),
            COMPLETED_LIST,
        ):
            with self.subTest(url=url):
                page = self.client.get(url).content.decode()
                self.assertNotIn("Secretname", page)
                self.assertNotIn("family@example.com", page)

    def test_filter_by_rating_and_area_and_search(self):
        def listed(query):
            response = self.client.get(FEEDBACK_LIST, query)
            return {f.rating for f in response.context["cl"].result_list}

        self.assertEqual(listed({"rating": 2}), {2})
        self.assertEqual(
            listed({"recommendation__activity__developmental_domain": "Language"}),
            {5},
        )
        self.assertEqual(listed({"q": "ACT-9002"}), {2})
        self.assertEqual(listed({"q": "loved"}), {5})

    def test_review_only(self):
        feedback = Feedback.objects.get(rating=5)
        self.assertEqual(
            self.client.get(reverse("admin:feedback_feedback_add")).status_code, 403
        )
        change = reverse("admin:feedback_feedback_change", args=[feedback.pk])
        page = self.client.get(change)
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'name="rating"')
        self.client.post(change, {"rating": 1, "comment": "edited"})
        feedback.refresh_from_db()
        self.assertEqual(
            (feedback.rating, feedback.comment), (5, "She loved the songs")
        )
        delete = reverse("admin:feedback_feedback_delete", args=[feedback.pk])
        self.assertEqual(self.client.post(delete, {"post": "yes"}).status_code, 403)
        self.assertEqual(Feedback.objects.count(), 2)

    def test_caregivers_cannot_open_the_review(self):
        self.client.force_login(self.child.caregiver)
        for url in (FEEDBACK_LIST, COMPLETED_LIST):
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 200)

    def test_completions_are_listed_against_the_activity(self):
        page = self.client.get(COMPLETED_LIST).content.decode()
        self.assertIn("Singing Together", page)
        self.assertIn("Completed", page)

    def test_activity_list_shows_feedback_count_and_average(self):
        Feedback.objects.create(recommendation=self.songs, rating=4)
        response = self.client.get(ACTIVITY_LIST)
        rows = {a.activity_id: a for a in response.context["cl"].result_list}
        self.assertEqual(rows["ACT-9001"]._feedback_count, 2)
        self.assertEqual(rows["ACT-9001"]._average_rating, 4.5)
        self.assertEqual(rows["ACT-9003"]._feedback_count, 0)
        page = response.content.decode()
        self.assertIn("4.5/5", page)
        self.assertIn(f"{FEEDBACK_LIST}?q=ACT-9001", page)
