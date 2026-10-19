"""Tests for the admin operations overview (#120)."""

from datetime import timedelta
from pathlib import Path
from unittest import mock

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from activities.choices import ContentStatus
from activities.models import DevelopmentalActivity
from profiles.models import ChildProfile, LoginChallenge, ReferenceMilestone
from recommendations import embeddings
from recommendations.models import ActivityEmbedding

from . import overview
from .tests import DashboardTestCase, User


def embed(activity, current=True):
    text = embeddings.activity_text(activity) if current else "old text"
    ActivityEmbedding.objects.create(
        activity=activity,
        model_name=embeddings.MODEL_NAME,
        dimensions=3,
        text_hash=embeddings.text_hash(embeddings.MODEL_NAME, text),
        vector=embeddings.to_bytes([0.1, 0.2, 0.3]),
    )


def health(title_start):
    checks = overview.health_checks(timezone.now())
    return next(c for c in checks if c["title"].startswith(title_start))


class RangeAndSeriesTests(DashboardTestCase):
    def test_range_falls_back_to_30_days(self):
        self.assertEqual(overview.parse_range("7"), 7)
        self.assertEqual(overview.parse_range("90"), 90)
        for bad in (None, "", "abc", "45", "-1"):
            self.assertEqual(overview.parse_range(bad), overview.DEFAULT_RANGE)

    def test_daily_series_counts_todays_activity(self):
        dates, series = overview.daily_series(timezone.now(), 7)
        self.assertEqual(len(dates), 7)
        self.assertEqual(dates[-1], timezone.localdate())
        self.assertEqual(series["ideas"][-1], 2)  # two batches today
        self.assertEqual(series["milestones"][-1], 3)
        self.assertEqual(series["feedback"][-1], 3)
        self.assertEqual(series["signups"][-1], 2)  # caregivers only
        self.assertEqual(sum(series["ideas"][:-1]), 0)

    def test_trend_chart_geometry(self):
        dates, series = overview.daily_series(timezone.now(), 30)
        chart = overview.trend_chart(dates, series)
        self.assertEqual([t["value"] for t in chart["ticks"]], [0, 1, 2, 3, 4])
        self.assertEqual(len(chart["hover"]), 30)
        self.assertEqual(chart["hover"][-1]["values"]["milestones"], 3)
        for line in chart["lines"]:
            self.assertEqual(len(line["points"].split()), 30)

    def test_nice_axis_tops(self):
        self.assertEqual(
            [overview._nice_max(v) for v in (0, 5, 13, 55, 101)],
            [4, 8, 20, 80, 200],
        )

    def test_donut_shares(self):
        donut = overview.outcomes_donut(done=1, partly=1, recommended=4)
        self.assertEqual(
            [(a["key"], a["count"], a["share"]) for a in donut["arcs"]],
            [("done", 1, 25), ("partly", 1, 25), ("open", 2, 50)],
        )
        empty = overview.outcomes_donut(0, 0, 0)
        self.assertFalse(any(a["visible"] for a in empty["arcs"]))


class HealthTests(DashboardTestCase):
    def test_model_present_or_missing(self):
        with override_settings(SBERT_MODEL_PATH=Path(__file__)):
            self.assertEqual(health("AI model")["status"], "good")
        with override_settings(SBERT_MODEL_PATH=Path("no/such/model")):
            self.assertEqual(health("AI model")["status"], "alert")

    def test_search_index(self):
        # Three Published activities, none embedded yet.
        self.assertEqual(health("Search index")["status"], "warning")
        self.assertIn("3 Published activities", health("Search index")["detail"])
        embed(self.songs)
        embed(self.blocks)
        embed(self.ball, current=False)  # edited since it was embedded
        self.assertIn("1 Published activity ", health("Search index")["detail"])
        ActivityEmbedding.objects.filter(activity=self.ball).delete()
        embed(self.ball)
        self.assertEqual(health("Search index")["status"], "good")

    def test_email_mode(self):
        console = {
            "default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}
        }
        smtp = {"default": {"BACKEND": "django.core.mail.backends.smtp.EmailBackend"}}
        with override_settings(MAILERS=console):
            self.assertEqual(health("Sign-in emails")["status"], "warning")
        with override_settings(MAILERS=smtp):
            self.assertEqual(health("Sign-in emails")["status"], "good")

    def test_locked_codes(self):
        checks = overview.health_checks(timezone.now())
        self.assertEqual(
            next(c for c in checks if c["title"] == "Sign-in")["status"], "good"
        )
        LoginChallenge.objects.create(
            user=self.family,
            purpose=LoginChallenge.Purpose.LOGIN,
            code_hash="x",
            expires_at=timezone.now() + timedelta(minutes=10),
            last_sent_at=timezone.now(),
            attempts=5,
        )
        self.assertEqual(health("Sign-in codes locked")["status"], "warning")


class WorkAndCoverageTests(DashboardTestCase):
    def test_work_waiting(self):
        ReferenceMilestone.objects.create(
            milestone_key="CDC-02M-SE-99",
            source="CDC",
            expected_age_months=2,
            domain="Socio-Emotional",
            description="x",
        )
        waiting = overview.work_waiting()
        self.assertEqual((waiting["drafts"], waiting["under_review"]), (1, 0))
        self.assertGreaterEqual(waiting["unverified"], 1)

    def test_coverage_grid_marks_gaps(self):
        grid = overview.coverage_grid()
        self.assertEqual(len(grid["rows"]), 5)
        self.assertEqual(len(grid["ages"]), 6)  # postnatal brackets
        counted = sum(c["count"] for r in grid["rows"] for c in r["cells"])
        self.assertEqual(counted, 3)  # the three Published activities
        self.assertEqual(grid["gaps"], 30 - 3)


class EventsAndTableTests(DashboardTestCase):
    def test_events_name_activities_not_families(self):
        LogEntry.objects.log_actions(
            user_id=User.objects.get(username="admin@example.com").pk,
            queryset=ChildProfile.objects.filter(pk=self.child.pk),
            action_flag=CHANGE,
        )
        events = overview.recent_events(limit=50)
        kinds = {e["kind"] for e in events}
        self.assertTrue({"signup", "ideas", "milestone", "done", "feedback"} <= kinds)
        text = " ".join(f"{e['title']} {e['detail']}" for e in events)
        self.assertNotIn("Secretname", text)  # the child-profile log entry is left out
        self.assertNotIn("family@example.com", text)
        self.assertIn("Rated 5★", text)

    def test_admin_content_changes_appear(self):
        LogEntry.objects.log_actions(
            user_id=User.objects.get(username="admin@example.com").pk,
            queryset=DevelopmentalActivity.objects.filter(pk=self.songs.pk),
            action_flag=CHANGE,
        )
        events = overview.recent_events(limit=50)
        self.assertTrue(any(e["kind"] == "admin" for e in events))

    def test_most_recommended_table(self):
        table = overview.most_recommended()
        first = table[0]
        self.assertEqual((first["activity_id"], first["times"]), ("ACT-9001", 2))
        self.assertEqual(first["done_share"], 50)  # 1 of its 2 recommendations
        self.assertEqual(first["average"], 5.0)
        self.assertEqual(first["status_key"], ContentStatus.PUBLISHED)


class OverviewPageTests(DashboardTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(User.objects.get(username="admin@example.com"))

    def test_range_tabs(self):
        page = self.client.get(reverse("admin:index"), {"range": "7"})
        self.assertContains(page, "in the last 7 days")
        self.assertContains(
            page,
            'class="od-tab od-tab-on" aria-selected="true" href="?range=7"',
            html=False,
        )
        bad = self.client.get(reverse("admin:index"), {"range": "999"})
        self.assertContains(bad, "in the last 30 days")

    def test_sidebar_lists_only_permitted_sections(self):
        caregiver = User.objects.get(username="family@example.com")
        self.client.force_login(caregiver)
        self.assertNotEqual(self.client.get(reverse("admin:index")).status_code, 200)
