"""Log-in tokens expire (#162)."""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from . import two_factor
from .authentication import EXPIRED_MESSAGE, is_expired, issue_token

User = get_user_model()
PASSWORD = "Str0ng-Passw0rd!"
DEVICE = "device-1234567890-abcdef"


def age(token, by):
    """Make token look issued `by` ago."""
    Token.objects.filter(pk=token.pk).update(created=timezone.now() - by)
    token.refresh_from_db()
    return token


class IssueTokenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="wanjiru", password=PASSWORD)

    def test_default_lifetime_is_30_days(self):
        self.assertEqual(settings.TOKEN_LIFETIME, timedelta(days=30))

    def test_reuses_a_token_that_still_works(self):
        first = issue_token(self.user)
        age(first, timedelta(days=29))
        self.assertEqual(issue_token(self.user).key, first.key)

    def test_replaces_an_expired_token(self):
        old = age(issue_token(self.user), settings.TOKEN_LIFETIME)
        self.assertTrue(is_expired(old))
        new = issue_token(self.user)
        self.assertNotEqual(new.key, old.key)
        self.assertFalse(is_expired(new))
        self.assertEqual(Token.objects.filter(user=self.user).count(), 1)


class ExpiringTokenAuthenticationTests(APITestCase):
    def setUp(self):
        cache.clear()  # throttle counts live in the cache
        self.user = User.objects.create_user(
            username="wanjiru", email="wanjiru@example.com", password=PASSWORD
        )
        self.token = issue_token(self.user)

    def me(self, key=None):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {key or self.token.key}")
        return self.client.get(reverse("me"))

    def test_token_works_within_its_lifetime(self):
        age(self.token, settings.TOKEN_LIFETIME - timedelta(minutes=1))
        self.assertEqual(self.me().status_code, status.HTTP_200_OK)

    def test_expired_token_is_refused_and_deleted(self):
        age(self.token, settings.TOKEN_LIFETIME)
        response = self.me()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], EXPIRED_MESSAGE)
        self.assertFalse(Token.objects.filter(key=self.token.key).exists())

    @override_settings(TOKEN_LIFETIME=timedelta(days=1))
    def test_lifetime_comes_from_settings(self):
        age(self.token, timedelta(days=2))
        self.assertEqual(self.me().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logging_in_again_gives_a_new_working_token(self):
        age(self.token, settings.TOKEN_LIFETIME)
        two_factor.trust(self.user, DEVICE)  # skip the emailed code
        self.client.credentials()
        response = self.client.post(
            reverse("login"),
            {"username": "wanjiru", "password": PASSWORD, "device_id": DEVICE},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        key = response.data["token"]
        self.assertNotEqual(key, self.token.key)
        self.assertEqual(self.me(key).status_code, status.HTTP_200_OK)
