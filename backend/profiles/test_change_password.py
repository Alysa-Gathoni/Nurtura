"""Changing the password while signed in: POST /api/auth/password/ (#142)."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

User = get_user_model()
PASSWORD = "x-test-pass"
NEW = "mango tree in the shade"
URL = reverse("change-password")


class ChangePasswordTests(APITestCase):
    def setUp(self):
        cache.clear()  # throttle counts live in the cache
        self.user = User.objects.create_user(
            username="wanjiru@example.com",
            email="wanjiru@example.com",
            password=PASSWORD,
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def change(self, current=PASSWORD, new=NEW):
        return self.client.post(
            URL, {"current_password": current, "new_password": new}, format="json"
        )

    def test_changes_the_password_and_returns_a_new_token(self):
        response = self.change()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW))
        body = response.json()
        self.assertEqual(body["user"]["email"], "wanjiru@example.com")
        self.assertTrue(body["user"]["has_password"])
        # The old token no longer works, so other phones are signed out;
        # the returned one does.
        self.assertNotEqual(body["token"], self.token.key)
        self.assertFalse(Token.objects.filter(key=self.token.key).exists())
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {body['token']}")
        self.assertEqual(self.client.get(reverse("me")).status_code, status.HTTP_200_OK)

    def test_wrong_current_password_changes_nothing(self):
        response = self.change(current="not-it")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("current_password", response.json())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))
        self.assertTrue(Token.objects.filter(key=self.token.key).exists())

    def test_the_password_rules_apply(self):
        for weak in ["abc", "12345678", "password", "wanjiru1"]:
            with self.subTest(weak=weak):
                response = self.change(new=weak)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("new_password", response.json())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_the_new_password_must_differ(self):
        response = self.change(new=PASSWORD)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.json())

    def test_an_account_without_a_password_is_sent_to_the_code(self):
        self.user.set_unusable_password()
        self.user.save()
        self.assertFalse(self.client.get(reverse("me")).json()["has_password"])
        response = self.change(current="")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("emailed code", response.json()["current_password"][0])

    def test_administrators_can_change_theirs(self):
        admin = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password=PASSWORD,
            role=User.Role.ADMINISTRATOR,
        )
        token = Token.objects.create(user=admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(self.change().status_code, status.HTTP_200_OK)
        admin.refresh_from_db()
        self.assertTrue(admin.check_password(NEW))

    def test_needs_sign_in(self):
        self.client.credentials()
        self.assertEqual(self.change().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guessing_the_current_password_is_throttled(self):
        codes = [self.change(current=f"guess-{i}").status_code for i in range(6)]
        self.assertEqual(codes[:5], [status.HTTP_400_BAD_REQUEST] * 5)
        self.assertEqual(codes[5], status.HTTP_429_TOO_MANY_REQUESTS)
