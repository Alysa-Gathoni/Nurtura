"""Milestone catalogue, milestone recording and DevelopmentalProfile API (#25)."""

import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ChildProfile, DevelopmentalMilestone, DevelopmentalProfile
from .models import ReferenceMilestone

User = get_user_model()


def months_ago(months):
    return timezone.localdate() - datetime.timedelta(days=round(months * 30.4375))


class MilestoneAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_milestones", stdout=StringIO())
        cls.caregiver = User.objects.create_user(
            username="wanjiru@example.com", password="x-test-pass"
        )
        cls.waves = ReferenceMilestone.objects.get(milestone_key="CDC-12M-LA-01")

    def setUp(self):
        self.client.force_authenticate(self.caregiver)
        self.child = ChildProfile.objects.create(
            caregiver=self.caregiver, name="Amani", date_of_birth=months_ago(13)
        )

    def milestones_url(self, child=None):
        return reverse("child-milestones", args=[(child or self.child).pk])


class ReferenceMilestoneAPITests(MilestoneAPITestCase):
    url = reverse("reference-milestone-list")

    def test_lists_whole_catalogue(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 133)
        self.assertEqual(
            set(response.data[0]),
            {
                "id",
                "milestone_key",
                "domain",
                "description",
                "expected_age_months",
                "source",
            },
        )

    def test_search_matches_every_word(self):
        response = self.client.get(self.url, {"search": "waves bye"})
        self.assertEqual([m["milestone_key"] for m in response.data], ["CDC-12M-LA-01"])
        self.assertEqual(response.data[0]["expected_age_months"], 12.0)

    def test_filter_by_domain(self):
        response = self.client.get(self.url, {"domain": "Motor", "search": "walk"})
        self.assertTrue(response.data)
        self.assertEqual({m["domain"] for m in response.data}, {"Motor"})
        bad = self.client.get(self.url, {"domain": "Visual"})
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED
        )


class RecordMilestoneAPITests(MilestoneAPITestCase):
    def test_recording_a_milestone_creates_the_developmental_profile(self):
        response = self.client.post(
            self.milestones_url(),
            {"reference": self.waves.pk, "status": "not_yet"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["milestone"]["reference_key"], "CDC-12M-LA-01")
        self.assertEqual(response.data["milestone"]["domain"], "Language")
        self.assertEqual(response.data["profile"]["ranked_domains"][0], "Language")

        milestone = DevelopmentalMilestone.objects.get(child=self.child)
        self.assertEqual(milestone.reference, self.waves)
        self.assertEqual(milestone.status, "not_yet")
        self.assertEqual(milestone.observation_date, timezone.localdate())

        profile = DevelopmentalProfile.objects.get(child=self.child)
        self.assertEqual(profile.top_domain, "Language")
        self.assertEqual(profile.scores["Language"], 1.0)
        self.assertEqual(profile.reasons[0]["rule"], "due-milestone-not-yet")

    def test_recording_again_updates_the_same_profile(self):
        for status_value in ("not_yet", "achieved"):
            self.client.post(
                self.milestones_url(),
                {"reference": self.waves.pk, "status": status_value},
                format="json",
            )
        self.assertEqual(
            DevelopmentalProfile.objects.filter(child=self.child).count(), 1
        )
        profile = DevelopmentalProfile.objects.get(child=self.child)
        self.assertEqual(set(profile.scores.values()), {1.0})
        self.assertEqual(profile.reasons, [])

    def test_lists_recorded_milestones(self):
        self.child.record_milestone(reference=self.waves, status="emerging")
        response = self.client.get(self.milestones_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["status"], "emerging")

    def test_catalogue_entry_and_valid_status_required(self):
        cases = [
            ({"status": "not_yet"}, "reference"),
            ({"reference": 99999, "status": "not_yet"}, "reference"),
            ({"reference": self.waves.pk, "status": "done"}, "status"),
            (
                {"description": "Says first words", "status": "not_yet"},
                "reference",
            ),
        ]
        for data, field in cases:
            with self.subTest(data=data):
                response = self.client.post(self.milestones_url(), data, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.data)
        self.assertFalse(DevelopmentalMilestone.objects.exists())

    def test_observation_date_checked(self):
        future = timezone.localdate() + datetime.timedelta(days=1)
        before_birth = self.child.date_of_birth - datetime.timedelta(days=1)
        for day in (future, before_birth):
            with self.subTest(day=day):
                response = self.client.post(
                    self.milestones_url(),
                    {
                        "reference": self.waves.pk,
                        "status": "achieved",
                        "observation_date": day.isoformat(),
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("observation_date", response.data)

    def test_prenatal_profiles_cannot_record_milestones_yet(self):
        expecting = ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Baby",
            date_of_birth=timezone.localdate() + datetime.timedelta(days=60),
        )
        response = self.client.post(
            self.milestones_url(expecting),
            {"reference": self.waves.pk, "status": "not_yet"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["non_field_errors"],
            ["Milestones can be recorded once your baby is born."],
        )

    def test_other_caregivers_children_are_not_reachable(self):
        other = User.objects.create_user(username="otieno", password="x-test-pass")
        others_child = ChildProfile.objects.create(
            caregiver=other, name="Baraka", date_of_birth=months_ago(13)
        )
        response = self.client.post(
            self.milestones_url(others_child),
            {"reference": self.waves.pk, "status": "not_yet"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(DevelopmentalMilestone.objects.exists())


class DevelopmentalProfileAPITests(MilestoneAPITestCase):
    def test_creating_a_child_creates_its_profile_from_concerns(self):
        response = self.client.post(
            reverse("child-list"),
            {
                "name": "Baby",
                "date_of_birth": (
                    timezone.localdate() + datetime.timedelta(days=60)
                ).isoformat(),
                "concerns": ["Sensory"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        profile = DevelopmentalProfile.objects.get(child_id=response.data["id"])
        self.assertEqual(profile.top_domain, "Sensory")
        self.assertLess(profile.age_months, 0)

    def test_updating_concerns_regenerates_the_profile(self):
        self.child.refresh_developmental_profile()
        self.client.patch(
            reverse("child-detail", args=[self.child.pk]),
            {"concerns": ["Motor"]},
            format="json",
        )
        self.assertEqual(
            DevelopmentalProfile.objects.get(child=self.child).top_domain, "Motor"
        )

    def test_profile_endpoint_returns_current_profile(self):
        self.child.record_milestone(reference=self.waves, status="not_yet")
        response = self.client.get(reverse("child-profile", args=[self.child.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ranked_domains"][0], "Language")
        self.assertEqual(
            set(response.data),
            {"age_months", "scores", "ranked_domains", "reasons", "generated_at"},
        )

    def test_profile_visible_read_only_in_admin(self):
        self.child.refresh_developmental_profile()
        admin = User.objects.create_superuser(username="root", password="x-test-pass")
        self.client.force_login(admin)
        changelist = reverse("admin:profiles_developmentalprofile_changelist")
        self.assertContains(self.client.get(changelist), "Profile for Amani")
        add = self.client.get(reverse("admin:profiles_developmentalprofile_add"))
        self.assertEqual(add.status_code, 403)
