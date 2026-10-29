"""Logging back in with a fingerprint: /api/auth/fingerprint/ (#150)."""

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import FingerprintKey
from .test_two_factor import code_from

User = get_user_model()
PASSWORD = "x-test-pass"
PHONE = "phone-1234567890-abcdef"
OTHER_PHONE = "phone-0987654321-fedcba"


class FingerprintTests(APITestCase):
    def setUp(self):
        cache.clear()  # throttle counts live in the cache
        self.user = User.objects.create_user(
            username="wanjiru@example.com",
            email="wanjiru@example.com",
            password=PASSWORD,
        )
        self.sign_in(self.user)

    def sign_in(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def turn_on(self, device_id=PHONE):
        response = self.client.post(
            reverse("fingerprint"), {"device_id": device_id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["key"]

    def fingerprint_login(self, key, device_id=PHONE):
        self.client.credentials()
        return self.client.post(
            reverse("fingerprint-login"),
            {"device_id": device_id, "key": key},
            format="json",
        )

    def test_turning_on_then_logging_in_after_log_out(self):
        key = self.turn_on()
        self.client.post(reverse("logout"))
        response = self.fingerprint_login(key)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "wanjiru@example.com")
        self.assertEqual(response.data["token"], Token.objects.get(user=self.user).key)
        self.assertIsNotNone(FingerprintKey.objects.get().last_used_at)

    def test_only_hashes_are_stored(self):
        key = self.turn_on()
        record = FingerprintKey.objects.get()
        self.assertNotIn(key, record.key_hash)
        self.assertNotIn(PHONE, record.device_hash)

    def test_a_wrong_key_or_another_phone_is_refused(self):
        key = self.turn_on()
        for bad_key, device in [
            ("not-the-key", PHONE),
            (key, OTHER_PHONE),
            (key, "short"),
            ("", PHONE),
        ]:
            with self.subTest(device=device):
                cache.clear()
                response = self.fingerprint_login(bad_key, device)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("password", response.data["key"][0])

    def test_turning_on_again_replaces_the_key(self):
        old = self.turn_on()
        new = self.turn_on()
        self.assertEqual(FingerprintKey.objects.count(), 1)
        self.assertEqual(
            self.fingerprint_login(old).status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertEqual(self.fingerprint_login(new).status_code, status.HTTP_200_OK)

    def test_one_phone_holds_one_account(self):
        self.turn_on()
        other = User.objects.create_user(
            username="otieno@example.com", email="otieno@example.com", password="x"
        )
        self.sign_in(other)
        key = self.turn_on()
        self.assertEqual(FingerprintKey.objects.get().user, other)
        response = self.fingerprint_login(key)
        self.assertEqual(response.data["user"]["email"], "otieno@example.com")

    def test_turning_off_revokes(self):
        key = self.turn_on()
        response = self.client.delete(
            reverse("fingerprint"), {"device_id": PHONE}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            self.fingerprint_login(key).status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_a_password_reset_revokes_every_phone(self):
        key = self.turn_on()
        self.client.credentials()
        challenge = self.client.post(
            reverse("password-reset"), {"email": "wanjiru@example.com"}, format="json"
        ).data["challenge"]
        token = self.client.post(
            reverse("password-reset-verify"),
            {"challenge": challenge, "code": code_from(mail.outbox[-1])},
            format="json",
        ).data["reset_token"]
        self.client.post(
            reverse("password-reset-confirm"),
            {"reset_token": token, "new_password": "mango tree in the shade"},
            format="json",
        )
        self.assertFalse(FingerprintKey.objects.exists())
        self.assertEqual(
            self.fingerprint_login(key).status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_a_password_change_keeps_only_this_phone(self):
        here = self.turn_on(PHONE)
        # The same account on a second phone (one key per phone).
        self.turn_on(OTHER_PHONE)
        response = self.client.post(
            reverse("change-password"),
            {
                "current_password": PASSWORD,
                "new_password": "mango tree in the shade",
                "device_id": PHONE,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(FingerprintKey.objects.count(), 1)
        self.assertEqual(self.fingerprint_login(here).status_code, status.HTTP_200_OK)

    def test_deleting_the_account_removes_the_key(self):
        self.turn_on()
        self.client.delete(reverse("me"), {"password": PASSWORD}, format="json")
        self.assertFalse(FingerprintKey.objects.exists())

    def test_a_switched_off_account_cannot_log_in(self):
        key = self.turn_on()
        self.user.is_active = False
        self.user.save()
        response = self.fingerprint_login(key)
        self.assertIn("can't sign in", response.data["key"][0])

    def test_turning_on_needs_sign_in_and_a_device_id(self):
        response = self.client.post(reverse("fingerprint"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.client.credentials()
        response = self.client.post(
            reverse("fingerprint"), {"device_id": PHONE}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guessing_keys_is_throttled(self):
        codes = [self.fingerprint_login(f"guess-{i}").status_code for i in range(6)]
        self.assertEqual(codes[5], status.HTTP_429_TOO_MANY_REQUESTS)
