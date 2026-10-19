"""Tests for the admin dashboard figures and page (#116)."""

import datetime
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from activities.choices import ContentStatus, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from feedback.models import CompletedActivity, Feedback
from profiles.models import ChildProfile, DevelopmentalMilestone
from recommendations.models import Recommendation

from .metrics import dashboard

User = get_user_model()


class DashboardTestCase(TestCase):
    def setUp(self):
        today = timezone.localdate()
        self.family = User.objects.create_user(
            username="family@example.com", email="family@example.com"
        )
        self.quiet = User.objects.create_user(username="quiet@example.com")
        self.child = ChildProfile.objects.create(
            caregiver=self.family,
            name="Zawadi Secretname",
            date_of_birth=today - timedelta(days=200),
        )
        ChildProfile.objects.create(
            caregiver=self.quiet,
            name="Baby",
            date_of_birth=today + timedelta(days=60),
        )
        User.objects.create_user(
            username="admin@example.com", role=User.Role.ADMINISTRATOR
        )

        def activity(activity_id, name, domain, status=ContentStatus.PUBLISHED):
            return DevelopmentalActivity.objects.create(
                **activity_fields(
                    activity_id=activity_id,
                    activity_name=name,
                    developmental_domain=domain,
                    content_status=status,
                )
            )

        self.songs = activity("ACT-9001", "Singing Together", Domain.LANGUAGE)
        self.blocks = activity("ACT-9002", "Block Tower", Domain.COGNITIVE)
        self.ball = activity("ACT-9003", "Rolling Ball", Domain.MOTOR)
        activity("ACT-9004", "Draft Idea", Domain.MOTOR, ContentStatus.DRAFT)

        batch = uuid.uuid4()

        def recommend(a, position, in_batch=batch):
            return Recommendation.objects.create(
                child=self.child,
                activity=a,
                batch=in_batch,
                position=position,
                similarity_score=0.8,
                ranking_score=0.7,
            )

        self.rec_songs = recommend(self.songs, 1)
        self.rec_blocks = recommend(self.blocks, 2)
        self.rec_ball = recommend(self.ball, 3)
        recommend(self.songs, 1, in_batch=uuid.uuid4())  # a second batch

        CompletedActivity.objects.create(recommendation=self.rec_songs)
        CompletedActivity.objects.create(
            recommendation=self.rec_blocks,
            status=CompletedActivity.Status.PARTIALLY_COMPLETED,
        )
        Feedback.objects.create(
            recommendation=self.rec_songs, rating=5, comment="She loved it"
        )
        Feedback.objects.create(recommendation=self.rec_blocks, rating=2)
        Feedback.objects.create(recommendation=self.rec_ball, rating=1)

        for status in ("achieved", "achieved", "not_yet"):
            DevelopmentalMilestone.objects.create(
                child=self.child,
                domain=Domain.LANGUAGE,
                description="x",
                status=status,
                observation_date=datetime.date(2026, 10, 1),
            )


class DashboardFiguresTests(DashboardTestCase):
    def test_people_and_activity(self):
        d = dashboard()
        self.assertEqual(d["caregivers"], 2)  # the administrator isn't counted
        self.assertEqual(d["active_caregivers"], 1)  # only the family did things
        self.assertEqual(
            (d["children"], d["children_born"], d["children_expecting"]), (2, 1, 1)
        )
        self.assertEqual(d["batches"], 2)
        self.assertEqual(d["batches_recent"], 2)
        self.assertEqual(d["recommended"], 4)
        self.assertEqual((d["done"], d["partly"], d["tried_share"]), (1, 1, 50))

    def test_ratings(self):
        d = dashboard()
        self.assertEqual(d["ratings_count"], 3)
        self.assertEqual(d["ratings_average"], 2.7)
        self.assertEqual(
            [(b["rating"], b["count"], b["width"]) for b in d["rating_bars"]],
            [(1, 1, 100), (2, 1, 100), (3, 0, 0), (4, 0, 0), (5, 1, 100)],
        )
        self.assertEqual(
            [a["activity_id"] for a in d["top_rated"]],
            ["ACT-9001", "ACT-9002", "ACT-9003"],
        )
        self.assertEqual(
            [a["activity_id"] for a in d["needs_attention"]],
            ["ACT-9003", "ACT-9002"],  # lowest first; 5 stars isn't included
        )
        self.assertEqual(d["recent_feedback"][-1]["comment"], "She loved it")

    def test_library_pipeline_and_milestones(self):
        d = dashboard()
        self.assertEqual(d["library_total"], 3)  # the draft isn't published
        library = {b["label"]: b["count"] for b in d["library_bars"]}
        self.assertEqual(library["Motor"], 1)
        self.assertEqual(library["Sensory"], 0)
        self.assertEqual(
            {p["label"]: p["count"] for p in d["pipeline"]},
            {"Draft": 1, "Under Review": 0, "Published": 3},
        )
        self.assertEqual(d["milestones_total"], 3)
        self.assertEqual(
            [(m["key"], m["count"], m["share"]) for m in d["milestone_parts"]],
            [("achieved", 2, 67), ("emerging", 0, 0), ("not_yet", 1, 33)],
        )

    def test_old_activity_is_not_active(self):
        later = timezone.now() + timedelta(days=30)
        self.assertEqual(dashboard(now=later)["active_caregivers"], 0)
        self.assertEqual(dashboard(now=later)["batches_recent"], 0)


class DashboardPageTests(DashboardTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(User.objects.get(username="admin@example.com"))

    def test_admin_home_shows_the_dashboard_and_sections(self):
        page = self.client.get(reverse("admin:index"))
        self.assertEqual(page.status_code, 200)
        for text in (
            "Overview",
            "Recommended activities",
            "Recent activity",
            "Most recommended activities",
            "System health",
            "Work waiting",
            "Library coverage",
            "Average 2.7 from 3 ratings",
            "Milestones recorded",
            "Needs attention",
            "Singing Together",
            "Developmental activities",  # the admin's sections, in the sidebar
            "nurtura/dashboard.js",
        ):
            self.assertContains(page, text)

    def test_no_child_or_caregiver_is_shown(self):
        page = self.client.get(reverse("admin:index")).content.decode()
        self.assertNotIn("Secretname", page)
        self.assertNotIn("family@example.com", page)

    def test_empty_database_shows_friendly_states(self):
        Feedback.objects.all().delete()
        DevelopmentalMilestone.objects.all().delete()
        page = self.client.get(reverse("admin:index"))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "No ratings yet")
        self.assertContains(page, "No milestones recorded yet.")
