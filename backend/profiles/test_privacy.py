"""The privacy notice and consent before adding a child's data (#136)."""

import datetime
import re
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from . import privacy
from .models import ChildProfile, ReferenceMilestone

User = get_user_model()
NOTICE_DOC = Path(settings.BASE_DIR).parent / "docs" / "privacy_notice.md"


class NoticeTests(APITestCase):
    @override_settings(PRIVACY_CONTACT="privacy@example.org")
    def test_public_and_complete(self):
        response = self.client.get(reverse("privacy-notice"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["version"], privacy.NOTICE_VERSION)
        self.assertEqual(response.data["title"], privacy.TITLE)
        headings = [s["heading"] for s in response.data["sections"]]
        self.assertEqual(headings, [h for h, _ in privacy.SECTIONS])
        text = " ".join(s["body"] for s in response.data["sections"])
        self.assertIn("contact privacy@example.org.", text)
        self.assertNotIn("{contact}", text)
        for promise in ("Until you delete it", "Data Protection Act, 2019"):
            with self.subTest(promise=promise):
                self.assertIn(promise, text)

    def test_doc_mirrors_the_notice_word_for_word(self):
        doc = NOTICE_DOC.read_text(encoding="utf-8")
        self.assertIn(f"**Version:** {privacy.NOTICE_VERSION}", doc)
        self.assertIn(f"# {privacy.TITLE}", doc)
        sections = re.findall(r"^## (.+)\n\n(.+)$", doc, flags=re.M)
        self.assertEqual(sections, list(privacy.SECTIONS))


class ConsentTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.caregiver = User.objects.create_user(
            username="wanjiru", email="wanjiru@example.com", password="x-test-pass"
        )
        self.client.force_authenticate(self.caregiver)

    def me(self):
        return self.client.get(reverse("me")).data

    def agree(self, version=privacy.NOTICE_VERSION):
        return self.client.post(
            reverse("privacy-consent"), {"version": version}, format="json"
        )

    def test_a_new_caregiver_must_agree(self):
        self.assertTrue(self.me()["privacy_consent_required"])
        self.assertIsNone(self.me()["privacy_agreed_at"])

    def test_registration_asks_for_agreement_next(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            reverse("register"),
            {
                "username": "amina",
                "email": "amina@example.com",
                "password": "Str0ng-Passw0rd!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["user"]["privacy_consent_required"])

    def test_agreeing_records_the_version_and_time(self):
        response = self.agree()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["privacy_consent_required"])
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.privacy_notice_version, privacy.NOTICE_VERSION)
        self.assertIsNotNone(self.caregiver.privacy_agreed_at)
        self.assertFalse(self.me()["privacy_consent_required"])

    def test_an_old_or_missing_version_is_refused(self):
        for version in ("2020-01-01", None, ""):
            with self.subTest(version=version):
                response = self.agree(version)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("version", response.data)
        self.caregiver.refresh_from_db()
        self.assertEqual(self.caregiver.privacy_notice_version, "")

    def test_a_new_notice_version_asks_again(self):
        self.agree()
        with mock.patch.object(privacy, "NOTICE_VERSION", "2099-01-01"):
            self.assertTrue(self.me()["privacy_consent_required"])

    def test_administrators_are_not_asked(self):
        admin = User.objects.create_user(
            username="admin", password="x-test-pass", role=User.Role.ADMINISTRATOR
        )
        self.client.force_authenticate(admin)
        self.assertFalse(self.me()["privacy_consent_required"])

    def test_agreeing_needs_sign_in(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.agree().status_code, status.HTTP_401_UNAUTHORIZED)


class ChildDataGateTests(APITestCase):
    """Adding or changing a child's data waits for agreement; reading and
    deleting don't."""

    def setUp(self):
        self.caregiver = User.objects.create_user(
            username="wanjiru", password="x-test-pass"
        )
        self.child = ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Amani",
            date_of_birth=datetime.date.today() - datetime.timedelta(days=400),
        )
        self.reference = ReferenceMilestone.objects.create(
            milestone_key="CDC-12M-LA-01",
            source="CDC",
            expected_age_months=12,
            domain="Language",
            description='Waves "bye-bye"',
            source_reference="CDC 2022",
        )
        self.client.force_authenticate(self.caregiver)
        self.detail = reverse("child-detail", args=[self.child.pk])

    def writes(self):
        return {
            "add a child": self.client.post(
                reverse("child-list"),
                {"name": "Baraka", "date_of_birth": "2025-06-01"},
                format="json",
            ),
            "edit a child": self.client.patch(
                self.detail, {"name": "Zawadi"}, format="json"
            ),
            "record a milestone": self.client.post(
                reverse("child-milestones", args=[self.child.pk]),
                {"reference": self.reference.pk, "status": "not_yet"},
                format="json",
            ),
        }

    def test_writes_are_refused_until_agreed(self):
        for action, response in self.writes().items():
            with self.subTest(action=action):
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                self.assertEqual(
                    str(response.data["detail"]),
                    "Please read and agree to the privacy notice first.",
                )
        self.assertEqual(self.caregiver.children.count(), 1)
        self.child.refresh_from_db()
        self.assertEqual(self.child.name, "Amani")
        self.assertFalse(self.child.milestones.exists())

    def test_reading_and_deleting_are_always_allowed(self):
        self.assertEqual(
            self.client.get(reverse("child-list")).status_code, status.HTTP_200_OK
        )
        self.assertEqual(self.client.get(self.detail).status_code, status.HTTP_200_OK)
        response = self.client.delete(self.detail)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_writes_work_once_agreed(self):
        privacy.record_consent(self.caregiver)
        for action, response in self.writes().items():
            with self.subTest(action=action):
                self.assertIn(response.status_code, (200, 201))
