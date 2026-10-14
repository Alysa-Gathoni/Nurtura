"""Two-step verification by emailed code (#86)."""

import re
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from . import two_factor
from .models import LoginChallenge, TrustedDevice

User = get_user_model()
PASSWORD = "Str0ng-Passw0rd!"
DEVICE = "device-1234567890-abcdef"


def code_from(message):
    return re.search(r"\b(\d{6})\b", message.body).group(1)


class TwoFactorAPITestCase(APITestCase):
    def setUp(self):
        cache.clear()  # throttle counts live in the cache
        self.user = User.objects.create_user(
            username="wanjiru", email="wanjiru@example.com", password=PASSWORD
        )

    def login(self, password=PASSWORD, device_id=DEVICE):
        data = {"username": "wanjiru", "password": password}
        if device_id is not None:
            data["device_id"] = device_id
        return self.client.post(reverse("login"), data, format="json")

    def verify(self, challenge, code, **extra):
        return self.client.post(
            reverse("login-verify"),
            {"challenge": challenge, "code": code, **extra},
            format="json",
        )

    def resend(self, challenge):
        return self.client.post(
            reverse("login-resend"), {"challenge": challenge}, format="json"
        )

    def login_and_verify(self, **extra):
        # The app sends its device ID with both the login and the code.
        extra.setdefault("device_id", DEVICE)
        challenge = self.login().data["challenge"]
        return self.verify(challenge, code_from(mail.outbox[-1]), **extra)


class LoginChallengeTests(TwoFactorAPITestCase):
    def test_password_alone_gets_a_challenge_and_an_email(self):
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data["two_factor_required"])
        self.assertEqual(response.data["email_hint"], "w***@example.com")
        self.assertEqual(response.data["expires_in"], 600)
        self.assertNotIn("token", response.data)
        self.assertFalse(Token.objects.exists())

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["wanjiru@example.com"])
        code = code_from(email)
        self.assertIn(code, email.subject)
        self.assertIn("expires in 10 minutes", email.body)
        # Only a hash is stored, never the code.
        stored = LoginChallenge.objects.get()
        self.assertNotIn(code, stored.code_hash)

    def test_wrong_password_sends_nothing(self):
        response = self.login(password="wrong")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mail.outbox, [])
        self.assertFalse(LoginChallenge.objects.exists())

    def test_correct_code_returns_a_token_and_trusts_the_device(self):
        response = self.login_and_verify()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Token.objects.get(user=self.user).key, response.data["token"])
        self.assertEqual(response.data["user"]["username"], "wanjiru")
        self.assertIsNotNone(response.data["device_trusted_until"])
        device = TrustedDevice.objects.get(user=self.user)
        self.assertNotIn(DEVICE, device.device_hash)  # stored as a hash
        until = device.trusted_until - timezone.now()
        self.assertTrue(timedelta(days=29) < until <= timedelta(days=30))

    def test_trusted_device_skips_the_code_for_30_days(self):
        self.login_and_verify()
        mail.outbox.clear()
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(mail.outbox, [])

        TrustedDevice.objects.update(
            trusted_until=timezone.now() - timedelta(seconds=1)
        )
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_other_devices_and_other_users_still_need_a_code(self):
        self.login_and_verify()
        self.assertEqual(
            self.login(device_id="another-device-0000000").status_code,
            status.HTTP_202_ACCEPTED,
        )
        self.assertEqual(
            self.login(device_id=None).status_code, status.HTTP_202_ACCEPTED
        )
        User.objects.create_user(
            username="other", email="other@example.com", password=PASSWORD
        )
        response = self.client.post(
            reverse("login"),
            {"username": "other", "password": PASSWORD, "device_id": DEVICE},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_remember_device_false_does_not_trust(self):
        response = self.login_and_verify(remember_device=False)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["device_trusted_until"])
        self.assertFalse(TrustedDevice.objects.exists())

    def test_short_device_ids_are_never_trusted(self):
        response = self.login_and_verify(device_id="short")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(TrustedDevice.objects.exists())

    def test_wrong_codes_count_down_then_lock(self):
        challenge = self.login().data["challenge"]
        real = code_from(mail.outbox[-1])
        wrong = "000000" if real != "000000" else "111111"
        for left in (4, 3, 2, 1):
            response = self.verify(challenge, wrong)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn(f"{left} tr", response.data["code"][0])
        response = self.verify(challenge, wrong)
        self.assertIn("Too many wrong codes", response.data["code"][0])
        # Even the right code no longer works.
        response = self.verify(challenge, real)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Token.objects.exists())

    def test_codes_expire_after_10_minutes(self):
        challenge = self.login().data["challenge"]
        code = code_from(mail.outbox[-1])
        LoginChallenge.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.verify(challenge, code)
        self.assertIn("expired", response.data["code"][0])

    def test_a_code_works_once(self):
        challenge = self.login().data["challenge"]
        code = code_from(mail.outbox[-1])
        self.assertEqual(self.verify(challenge, code).status_code, status.HTTP_200_OK)
        response = self.verify(challenge, code)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been used", response.data["code"][0])

    def test_a_new_login_cancels_the_previous_code(self):
        first = self.login().data["challenge"]
        first_code = code_from(mail.outbox[-1])
        self.login()
        response = self.verify(first, first_code)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_spaces_in_the_code_are_ignored(self):
        challenge = self.login().data["challenge"]
        code = code_from(mail.outbox[-1])
        spaced = f"{code[:3]} {code[3:]}"
        self.assertEqual(self.verify(challenge, spaced).status_code, status.HTTP_200_OK)

    def test_unknown_or_malformed_challenge(self):
        for challenge in ("not-a-uuid", "00000000-0000-0000-0000-000000000000"):
            with self.subTest(challenge=challenge):
                response = self.verify(challenge, "123456")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(reverse("login-verify"), {}, format="json")
        self.assertIn("challenge", response.data)

    def test_account_without_email_is_told_plainly(self):
        User.objects.filter(pk=self.user.pk).update(email="")
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("no email address", response.data["non_field_errors"][0])


class ResendTests(TwoFactorAPITestCase):
    def test_resend_waits_30_seconds_then_sends_a_new_code(self):
        challenge = self.login().data["challenge"]
        first = code_from(mail.outbox[-1])
        response = self.resend(challenge)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Please wait", response.data["code"][0])

        LoginChallenge.objects.update(
            last_sent_at=timezone.now() - two_factor.RESEND_AFTER
        )
        response = self.resend(challenge)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 2)
        second = code_from(mail.outbox[-1])
        # The new code works; with overwhelming likelihood the old one doesn't.
        if first != second:
            self.assertEqual(
                self.verify(challenge, first).status_code, status.HTTP_400_BAD_REQUEST
            )
        self.assertEqual(self.verify(challenge, second).status_code, status.HTTP_200_OK)

    def test_at_most_three_resends(self):
        challenge = self.login().data["challenge"]
        for _ in range(3):
            LoginChallenge.objects.update(
                last_sent_at=timezone.now() - two_factor.RESEND_AFTER
            )
            self.assertEqual(self.resend(challenge).status_code, status.HTTP_200_OK)
        LoginChallenge.objects.update(
            last_sent_at=timezone.now() - two_factor.RESEND_AFTER
        )
        response = self.resend(challenge)
        self.assertIn("No more codes", response.data["code"][0])
        self.assertEqual(len(mail.outbox), 4)


class RegistrationTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_registration_needs_the_emailed_code_before_a_token(self):
        response = self.client.post(
            reverse("register"),
            {"username": "amina", "email": "amina@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["two_factor_required"])
        self.assertNotIn("token", response.data)
        self.assertIn("finish creating your account", mail.outbox[-1].body)

        response = self.client.post(
            reverse("login-verify"),
            {
                "challenge": response.data["challenge"],
                "code": code_from(mail.outbox[-1]),
                "device_id": DEVICE,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(username="amina")
        self.assertEqual(Token.objects.get(user=user).key, response.data["token"])
        self.assertTrue(TrustedDevice.objects.filter(user=user).exists())

    def test_a_failed_email_creates_no_account(self):
        with mock.patch.object(
            two_factor, "send_mail", side_effect=OSError("smtp down")
        ):
            with self.assertRaises(OSError):
                self.client.post(
                    reverse("register"),
                    {
                        "username": "amina",
                        "email": "amina@example.com",
                        "password": PASSWORD,
                    },
                    format="json",
                )
        self.assertFalse(User.objects.filter(username="amina").exists())


class HelperTests(TestCase):
    def test_mask_email(self):
        self.assertEqual(
            two_factor.mask_email("wanjiru@example.com"), "w***@example.com"
        )
        self.assertEqual(two_factor.mask_email("x"), "your email address")

    def test_codes_are_six_digits(self):
        for _ in range(50):
            code = two_factor._new_code()
            self.assertRegex(code, r"^\d{6}$")
