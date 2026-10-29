"""Deleting your own account: DELETE /api/auth/me/ (#134)."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from activities.choices import ContentStatus
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from feedback.models import CompletedActivity, Feedback
from recommendations.models import Recommendation

from . import two_factor
from .models import (
    ChildProfile,
    DevelopmentalMilestone,
    LoginChallenge,
    TrustedDevice,
)

User = get_user_model()
PASSWORD = "x-test-pass"


class DeleteAccountTests(APITestCase):
    def setUp(self):
        cache.clear()  # throttle counts live in the cache
        self.caregiver = User.objects.create_user(
            username="wanjiru", email="Wanjiru@example.com", password=PASSWORD
        )
        self.other = User.objects.create_user(
            username="otieno", email="otieno@example.com", password=PASSWORD
        )
        self.activity = DevelopmentalActivity.objects.create(
            **activity_fields(content_status=ContentStatus.PUBLISHED)
        )
        self.child = self.family(self.caregiver, "Amani")
        self.others_child = self.family(self.other, "Baraka")
        two_factor.trust(self.caregiver, "device-0123456789abcdef")
        two_factor.start(self.caregiver)
        self.token = Token.objects.create(user=self.caregiver)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def family(self, caregiver, name):
        """A child with a milestone, a recommendation, a completion and a rating."""
        child = ChildProfile.objects.create(
            caregiver=caregiver, name=name, date_of_birth="2025-08-01"
        )
        DevelopmentalMilestone.objects.create(
            child=child, domain="Language", description="Coos", status="not_yet"
        )
        rec = Recommendation.objects.create(
            child=child, activity=self.activity, similarity_score=0.5, ranking_score=0.5
        )
        CompletedActivity.objects.create(recommendation=rec)
        Feedback.objects.create(recommendation=rec, rating=4)
        return child

    def delete_me(self, **data):
        return self.client.delete(reverse("me"), data, format="json")

    def test_deletes_the_account_and_everything_it_owns(self):
        response = self.delete_me(password=PASSWORD)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(username="wanjiru").exists())
        for model, owner in (
            (ChildProfile, {"caregiver__username": "wanjiru"}),
            (DevelopmentalMilestone, {"child__name": "Amani"}),
            (Recommendation, {"child__name": "Amani"}),
            (CompletedActivity, {"recommendation__child__name": "Amani"}),
            (Feedback, {"recommendation__child__name": "Amani"}),
            (LoginChallenge, {"user__username": "wanjiru"}),
            (TrustedDevice, {"user__username": "wanjiru"}),
            (Token, {"user__username": "wanjiru"}),
        ):
            with self.subTest(model=model.__name__):
                self.assertFalse(model.objects.filter(**owner).exists())

    def test_other_families_and_the_activity_are_kept(self):
        self.delete_me(password=PASSWORD)
        self.assertTrue(User.objects.filter(username="otieno").exists())
        self.assertEqual(self.others_child.recommendations.count(), 1)
        self.assertEqual(Feedback.objects.count(), 1)
        self.assertTrue(
            DevelopmentalActivity.objects.filter(pk=self.activity.pk).exists()
        )

    def test_the_token_stops_working(self):
        self.delete_me(password=PASSWORD)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_or_missing_password_deletes_nothing(self):
        for data in ({"password": "wrong-pass"}, {}, {"password": 123}):
            with self.subTest(data=data):
                response = self.delete_me(**data)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("password", response.data)
        self.assertTrue(User.objects.filter(pk=self.caregiver.pk).exists())
        self.assertEqual(self.child.recommendations.count(), 1)

    def test_account_without_a_password_confirms_with_its_email(self):
        self.caregiver.set_unusable_password()
        self.caregiver.save()
        response = self.delete_me(email="someone@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        response = self.delete_me(email="  wanjiru@EXAMPLE.com ")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=self.caregiver.pk).exists())

    def test_administrators_cannot_delete_themselves_here(self):
        admin = User.objects.create_user(
            username="admin", password=PASSWORD, role=User.Role.ADMINISTRATOR
        )
        self.client.force_authenticate(admin)
        response = self.delete_me(password=PASSWORD)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(User.objects.filter(pk=admin.pk).exists())

    def test_requires_sign_in(self):
        self.client.credentials()
        response = self.delete_me(password=PASSWORD)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(User.objects.filter(pk=self.caregiver.pk).exists())

    def test_password_guesses_are_throttled_but_reading_is_not(self):
        for _ in range(5):
            self.delete_me(password="wrong-pass")
        response = self.delete_me(password=PASSWORD)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertTrue(User.objects.filter(pk=self.caregiver.pk).exists())
        for _ in range(7):
            self.assertEqual(self.client.get(reverse("me")).status_code, 200)
