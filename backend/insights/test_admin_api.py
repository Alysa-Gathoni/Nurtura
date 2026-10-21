"""Tests for the administrator API used by the app (#122)."""

import json

from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from activities.choices import ContentStatus, Domain
from activities.models import DevelopmentalActivity
from recommendations import embeddings
from recommendations.models import ActivityEmbedding
from recommendations.test_embeddings import FakeEncoder

from .tests import DashboardTestCase, User

NEW_ACTIVITY = {
    "activity_name": "Clapping Songs",
    "developmental_domain": "Language",
    "age_range": "6-12 months",
    "developmental_goal": "Rhythm and turn-taking with sounds",
    "materials": "None",
    "difficulty_level": "Beginner",
    "description": "Clap and sing a short song, then pause for your baby to join in.",
    "cultural_relevance": "Works with any local songs.",
    "plain_aim": "help your baby enjoy rhythm and taking turns",
    "source": "UNICEF",
    "source_url": "",
}


class AdminApiTestCase(DashboardTestCase):
    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.admin = User.objects.get(username="admin@example.com")
        self.api.force_authenticate(self.admin)


class AccessTests(AdminApiTestCase):
    ENDPOINTS = [
        ("get", "admin-api-overview", []),
        ("get", "admin-api-activities", []),
        ("get", "admin-api-choices", []),
        ("get", "admin-api-feedback", []),
        ("post", "admin-api-search-index", []),
    ]

    def test_caregivers_and_anonymous_are_kept_out(self):
        caregiver = APIClient()
        caregiver.force_authenticate(self.family)
        anonymous = APIClient()
        for method, name, args in self.ENDPOINTS:
            with self.subTest(endpoint=name):
                url = reverse(name, args=args)
                self.assertEqual(
                    getattr(caregiver, method)(url).status_code,
                    status.HTTP_403_FORBIDDEN,
                )
                self.assertEqual(
                    getattr(anonymous, method)(url).status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )

    def test_activity_detail_and_status_need_an_administrator(self):
        caregiver = APIClient()
        caregiver.force_authenticate(self.family)
        url = reverse("admin-api-activity", args=[self.songs.pk])
        self.assertEqual(caregiver.get(url).status_code, 403)
        self.assertEqual(caregiver.patch(url, {"activity_name": "X"}).status_code, 403)
        status_url = reverse("admin-api-activity-status", args=[self.songs.pk])
        self.assertEqual(
            caregiver.post(status_url, {"status": "draft"}).status_code, 403
        )
        self.songs.refresh_from_db()
        self.assertEqual(self.songs.activity_name, "Singing Together")


class OverviewTests(AdminApiTestCase):
    def test_overview_payload(self):
        body = self.api.get(reverse("admin-api-overview"), {"range": "7"}).json()
        self.assertEqual(body["range"], 7)
        self.assertEqual(body["ranges"], [7, 30, 90])
        self.assertEqual(len(body["trend"]["dates"]), 7)
        self.assertEqual(body["trend"]["series"]["milestones"][-1], 3)
        self.assertEqual(body["people"]["caregivers"], 2)
        self.assertEqual(
            body["outcomes"],
            {
                "recommended": 4,
                "done": 1,
                "partly": 1,
                "not_marked": 2,
                "tried_share": 50,
            },
        )
        self.assertEqual(body["ratings"]["by_star"], [1, 1, 0, 0, 1])
        self.assertEqual(body["ratings"]["average"], 2.7)
        self.assertEqual(len(body["spark"]["series"]["signups"]), 14)
        self.assertEqual(len(body["coverage"]["rows"]), 5)
        titles = {h["title"] for h in body["health"]}
        self.assertTrue({"AI model ready", "AI model missing"} & titles)
        self.assertNotIn("Debug mode on", titles)  # the test runner turns DEBUG off
        self.assertEqual(body["most_recommended"][0]["activity_id"], "ACT-9001")

    def test_overview_never_names_a_family(self):
        text = json.dumps(self.api.get(reverse("admin-api-overview")).json())
        self.assertNotIn("Secretname", text)
        self.assertNotIn("family@example.com", text)

    def test_bad_range_falls_back(self):
        body = self.api.get(reverse("admin-api-overview"), {"range": "nope"}).json()
        self.assertEqual(body["range"], 30)


class ActivityTests(AdminApiTestCase):
    def url(self, pk=None):
        return (
            reverse("admin-api-activity", args=[pk])
            if pk
            else reverse("admin-api-activities")
        )

    def test_list_and_filters(self):
        rows = self.api.get(self.url()).json()
        self.assertEqual(
            [r["activity_id"] for r in rows],
            ["ACT-9001", "ACT-9002", "ACT-9003", "ACT-9004"],
        )
        songs = rows[0]
        self.assertEqual((songs["times_recommended"], songs["feedback_count"]), (2, 1))
        self.assertEqual(songs["average_rating"], 5.0)
        self.assertEqual(songs["status_label"], "Published")
        self.assertFalse(songs["searchable"])  # not embedded in this test
        drafts = self.api.get(self.url(), {"status": "draft"}).json()
        self.assertEqual([r["activity_id"] for r in drafts], ["ACT-9004"])
        motor = self.api.get(self.url(), {"domain": "Motor"}).json()
        self.assertEqual({r["activity_id"] for r in motor}, {"ACT-9003", "ACT-9004"})
        found = self.api.get(self.url(), {"search": "block"}).json()
        self.assertEqual([r["activity_id"] for r in found], ["ACT-9002"])

    def test_create_starts_as_draft_with_the_next_id(self):
        # The highest existing number is ACT-9004.
        response = self.api.post(self.url(), NEW_ACTIVITY, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        body = response.json()
        self.assertEqual(body["activity_id"], "ACT-9005")
        self.assertEqual(body["content_status"], ContentStatus.DRAFT)
        entry = LogEntry.objects.get(object_id=str(body["id"]))
        self.assertEqual((entry.action_flag, entry.user), (ADDITION, self.admin))

    def test_status_cannot_be_set_by_create_or_edit(self):
        response = self.api.post(
            self.url(), {**NEW_ACTIVITY, "content_status": "published"}, format="json"
        )
        self.assertEqual(response.json()["content_status"], "draft")

    def test_create_validation(self):
        bad = {**NEW_ACTIVITY, "plain_aim": "Help Your Baby.", "source": "Blog"}
        response = self.api.post(self.url(), bad, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("source", response.json())
        duplicate = {**NEW_ACTIVITY, "activity_name": "singing together"}
        response = self.api.post(self.url(), duplicate, format="json")
        self.assertEqual(response.status_code, 400)  # one name per area
        self.assertEqual(DevelopmentalActivity.objects.count(), 4)

    def test_editing_published_content_returns_it_to_draft(self):
        response = self.api.patch(
            self.url(self.songs.pk), {"description": "New wording."}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["content_status"], "draft")
        entry = LogEntry.objects.filter(object_id=str(self.songs.pk)).latest("id")
        self.assertEqual(entry.action_flag, CHANGE)
        self.assertIn("Returned to Draft", entry.get_change_message())

    def test_saving_without_changes_keeps_the_status(self):
        response = self.api.patch(
            self.url(self.songs.pk),
            {"activity_name": "Singing Together"},
            format="json",
        )
        self.assertEqual(response.json()["content_status"], "published")
        self.assertFalse(LogEntry.objects.exists())

    def test_editing_a_draft_keeps_it_a_draft(self):
        draft = DevelopmentalActivity.objects.get(activity_id="ACT-9004")
        response = self.api.patch(
            self.url(draft.pk), {"materials": "A ball"}, format="json"
        )
        self.assertEqual(response.json()["content_status"], "draft")


class StatusTests(AdminApiTestCase):
    def post(self, activity, target):
        return self.api.post(
            reverse("admin-api-activity-status", args=[activity.pk]),
            {"status": target},
            format="json",
        )

    def test_review_workflow(self):
        draft = DevelopmentalActivity.objects.get(activity_id="ACT-9004")
        self.assertEqual(
            self.post(draft, "under_review").json()["content_status"], "under_review"
        )
        self.assertEqual(
            self.post(draft, "published").json()["content_status"], "published"
        )
        self.assertEqual(self.post(draft, "draft").json()["content_status"], "draft")
        messages = [
            e.get_change_message()
            for e in LogEntry.objects.filter(object_id=str(draft.pk)).order_by("id")
        ]
        self.assertEqual(
            messages,
            [
                "Status changed to Under Review.",
                "Status changed to Published.",
                "Status changed to Draft.",
            ],
        )

    def test_skipping_review_is_refused(self):
        draft = DevelopmentalActivity.objects.get(activity_id="ACT-9004")
        response = self.post(draft, "published")
        self.assertEqual(response.status_code, 400)
        self.assertIn("status", response.json())
        draft.refresh_from_db()
        self.assertEqual(draft.content_status, ContentStatus.DRAFT)

    def test_unknown_status(self):
        self.assertEqual(self.post(self.songs, "archived").status_code, 400)

    def test_choices(self):
        body = self.api.get(reverse("admin-api-choices")).json()
        self.assertIn({"value": "Language", "label": "Language"}, body["domains"])
        self.assertEqual(body["transitions"]["draft"], ["under_review"])
        self.assertEqual(len(body["age_ranges"]), 7)


class FeedbackTests(AdminApiTestCase):
    def get(self, **params):
        return self.api.get(reverse("admin-api-feedback"), params).json()

    def test_rows_name_activities_not_families(self):
        body = self.get()
        self.assertEqual(body["count"], 3)
        first = body["results"][-1]
        self.assertEqual(first["activity"]["name"], "Singing Together")
        self.assertEqual((first["rating"], first["comment"]), (5, "She loved it"))
        self.assertEqual(first["completion"], "completed")
        text = json.dumps(body)
        self.assertNotIn("Secretname", text)
        self.assertNotIn("family@example.com", text)

    def test_filters_and_paging(self):
        self.assertEqual([r["rating"] for r in self.get(rating=2)["results"]], [2])
        self.assertEqual(self.get(domain="Motor")["count"], 1)
        self.assertEqual(self.get(activity=self.songs.pk)["count"], 1)
        page = self.get(limit=2, offset=0)
        self.assertEqual((page["count"], len(page["results"])), (3, 2))
        self.assertEqual(len(self.get(limit=2, offset=2)["results"]), 1)
        self.assertEqual(self.get(rating="x")["count"], 0)


class SearchIndexTests(AdminApiTestCase):
    def setUp(self):
        super().setUp()
        embeddings.set_encoder(FakeEncoder())
        self.addCleanup(embeddings.set_encoder, None)

    def test_rebuild_embeds_published_activities(self):
        response = self.api.post(reverse("admin-api-search-index"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("3 Published", response.json()["message"])
        self.assertEqual(ActivityEmbedding.objects.count(), 3)
        self.assertFalse(
            ActivityEmbedding.objects.filter(
                activity__content_status=ContentStatus.DRAFT
            ).exists()
        )


class AdministratorSignInTests(AdminApiTestCase):
    def test_administrators_sign_in_with_the_emailed_code(self):
        admin = User.objects.create_user(
            username="lead@example.com",
            email="lead@example.com",
            password="Str0ng-admin-pass!",
            role=User.Role.ADMINISTRATOR,
        )
        response = APIClient().post(
            reverse("login"),
            {
                "username": "lead@example.com",
                "password": "Str0ng-admin-pass!",
                "device_id": "admin-phone-0123456789",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.json()["two_factor_required"])
        self.assertNotIn("token", response.json())
        me = APIClient()
        me.force_authenticate(admin)
        self.assertEqual(me.get(reverse("me")).json()["role"], "administrator")
