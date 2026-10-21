"""Resetting a forgotten password with an emailed code, and signing in with
an email that isn't the username (#126)."""

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token

from .models import LoginChallenge, TrustedDevice
from .test_two_factor import DEVICE, PASSWORD, TwoFactorAPITestCase, code_from

User = get_user_model()
NEW_PASSWORD = "Fresh-Passw0rd-2026"


class PasswordResetTestCase(TwoFactorAPITestCase):
    def ask(self, email="wanjiru@example.com"):
        return self.client.post(
            reverse("password-reset"), {"email": email}, format="json"
        )

    def confirm(self, challenge, code, password=NEW_PASSWORD, **extra):
        return self.client.post(
            reverse("password-reset-confirm"),
            {"challenge": challenge, "code": code, "new_password": password, **extra},
            format="json",
        )

    def reset(self, **extra):
        challenge = self.ask().data["challenge"]
        return self.confirm(challenge, code_from(mail.outbox[-1]), **extra)


class RequestCodeTests(PasswordResetTestCase):
    def test_emails_a_reset_code(self):
        response = self.ask()
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["email_hint"], "w***@example.com")
        self.assertEqual(response.data["expires_in"], 600)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["wanjiru@example.com"])
        self.assertIn("choose a new password", email.body)
        self.assertIn("your password hasn't changed", email.body)
        challenge = LoginChallenge.objects.get()
        self.assertEqual(challenge.purpose, LoginChallenge.Purpose.RESET)
        self.assertNotIn(code_from(email), challenge.code_hash)

    def test_email_is_matched_ignoring_case_and_spaces(self):
        self.ask("  Wanjiru@Example.COM ")
        self.assertEqual(mail.outbox[0].to, ["wanjiru@example.com"])

    def test_an_unknown_email_gets_the_same_reply_and_no_email(self):
        known = self.ask().data
        mail.outbox.clear()
        unknown = self.client.post(
            reverse("password-reset"), {"email": "nobody@example.com"}, format="json"
        )
        self.assertEqual(unknown.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(set(unknown.data), set(known))
        self.assertEqual(unknown.data["email_hint"], "n***@example.com")
        self.assertEqual(mail.outbox, [])
        self.assertFalse(
            LoginChallenge.objects.filter(pk=unknown.data["challenge"]).exists()
        )

    def test_an_inactive_account_gets_no_email(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.ask().status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(mail.outbox, [])

    def test_needs_an_email(self):
        response = self.ask("wanjiru")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_asking_is_rate_limited(self):
        for _ in range(5):
            self.ask()
        self.assertEqual(self.ask().status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class ConfirmTests(PasswordResetTestCase):
    def test_sets_the_password_and_signs_in(self):
        response = self.reset(device_id=DEVICE)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["username"], "wanjiru")
        self.assertEqual(response.data["token"], Token.objects.get(user=self.user).key)
        self.assertIsNotNone(response.data["device_trusted_until"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertFalse(self.user.check_password(PASSWORD))
        # This phone is now trusted, so the new password logs straight in.
        login = self.client.post(
            reverse("login"),
            {"username": "wanjiru", "password": NEW_PASSWORD, "device_id": DEVICE},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

    def test_signs_out_other_phones(self):
        old = Token.objects.create(user=self.user)
        response = self.reset()
        self.assertFalse(Token.objects.filter(key=old.key).exists())
        self.assertNotEqual(response.data["token"], old.key)

    def test_remember_device_off_trusts_nothing(self):
        response = self.reset(device_id=DEVICE, remember_device=False)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["device_trusted_until"])
        self.assertFalse(TrustedDevice.objects.exists())

    def test_a_weak_password_is_refused_without_using_a_try(self):
        challenge = self.ask().data["challenge"]
        code = code_from(mail.outbox[-1])
        response = self.confirm(challenge, code, password="12345678")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)
        self.assertEqual(LoginChallenge.objects.get().attempts, 0)
        # The same code still works with a better password.
        self.assertEqual(self.confirm(challenge, code).status_code, 200)

    def test_the_password_cannot_be_like_the_username(self):
        challenge = self.ask().data["challenge"]
        response = self.confirm(
            challenge, code_from(mail.outbox[-1]), password="wanjiru123"
        )
        self.assertIn("new_password", response.data)

    def test_a_wrong_code_counts_down_and_changes_nothing(self):
        challenge = self.ask().data["challenge"]
        response = self.confirm(challenge, "000000")
        if code_from(mail.outbox[-1]) == "000000":  # pragma: no cover
            self.skipTest("the random code happened to be 000000")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("4 tries left", response.data["code"][0])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_a_code_works_once(self):
        challenge = self.ask().data["challenge"]
        code = code_from(mail.outbox[-1])
        self.assertEqual(self.confirm(challenge, code).status_code, 200)
        again = self.confirm(challenge, code, password="Another-Passw0rd-9")
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been used", again.data["code"][0])
        self.assertIn("new reset code", again.data["code"][0])

    def test_an_expired_code_is_refused(self):
        challenge = self.ask().data["challenge"]
        LoginChallenge.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.confirm(challenge, code_from(mail.outbox[-1]))
        self.assertIn("expired", response.data["code"][0])

    def test_an_unknown_or_malformed_challenge_is_refused(self):
        for challenge in [str(uuid.uuid4()), "not-a-uuid"]:
            response = self.confirm(challenge, "123456")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("already been used", response.data["code"][0])

    def test_needs_a_new_password(self):
        challenge = self.ask().data["challenge"]
        response = self.confirm(challenge, code_from(mail.outbox[-1]), password="")
        self.assertIn("new_password", response.data)


class CodesStaySeparateTests(PasswordResetTestCase):
    def test_a_reset_code_does_not_log_in(self):
        challenge = self.ask().data["challenge"]
        response = self.verify(challenge, code_from(mail.outbox[-1]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Token.objects.exists())

    def test_a_login_code_does_not_reset_the_password(self):
        challenge = self.login().data["challenge"]
        response = self.confirm(challenge, code_from(mail.outbox[-1]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_the_login_resend_does_not_send_reset_codes(self):
        challenge = self.ask().data["challenge"]
        self.assertEqual(self.resend(challenge).status_code, 400)


class ResendTests(PasswordResetTestCase):
    def resend_reset(self, challenge):
        return self.client.post(
            reverse("password-reset-resend"), {"challenge": challenge}, format="json"
        )

    def test_sends_a_fresh_code_after_the_wait(self):
        challenge = self.ask().data["challenge"]
        first = code_from(mail.outbox[-1])
        self.assertIn("wait", self.resend_reset(challenge).data["code"][0])
        LoginChallenge.objects.update(
            last_sent_at=timezone.now() - timedelta(seconds=31)
        )
        response = self.resend_reset(challenge)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email_hint"], "w***@example.com")
        self.assertEqual(len(mail.outbox), 2)
        second = code_from(mail.outbox[-1])
        if first != second:
            self.assertEqual(self.confirm(challenge, first).status_code, 400)
        self.assertEqual(self.confirm(challenge, second).status_code, 200)

    def test_a_login_challenge_is_not_resent_here(self):
        challenge = self.login().data["challenge"]
        self.assertEqual(self.resend_reset(challenge).status_code, 400)


class LoginWithEmailTests(TwoFactorAPITestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(
            username="lead", email="Lead@Example.com", password=PASSWORD
        )

    def login_as(self, username, password=PASSWORD):
        return self.client.post(
            reverse("login"),
            {"username": username, "password": password, "device_id": DEVICE},
            format="json",
        )

    def test_an_account_whose_username_is_not_its_email_can_use_the_email(self):
        response = self.login_as("lead@example.com")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(mail.outbox[-1].to, ["Lead@example.com"])

    def test_the_username_still_works(self):
        self.assertEqual(self.login_as("lead").status_code, 202)

    def test_the_email_still_needs_the_right_password(self):
        response = self.login_as("lead@example.com", password="wrong-password")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mail.outbox, [])

    def test_a_username_that_is_an_email_wins(self):
        # A caregiver's username is their email; another account can't take
        # over that login by having the same text as its email.
        User.objects.create_user(
            username="lead@example.com",
            email="other@example.com",
            password="Other-Passw0rd-1",
        )
        self.assertEqual(self.login_as("lead@example.com").status_code, 400)
        self.assertEqual(
            self.login_as("lead@example.com", "Other-Passw0rd-1").status_code, 202
        )
