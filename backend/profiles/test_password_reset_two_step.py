"""Resetting in two steps: check the code for a pass, then set the password
with the pass (#146)."""

from datetime import timedelta
from unittest import mock

from django.core import mail, signing
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

from . import password_reset
from .models import LoginChallenge, TrustedDevice
from .test_password_reset import NEW_PASSWORD, PasswordResetTestCase
from .test_two_factor import DEVICE, PASSWORD, code_from


class TwoStepResetTests(PasswordResetTestCase):
    def check_code(self, challenge, code):
        return self.client.post(
            reverse("password-reset-verify"),
            {"challenge": challenge, "code": code},
            format="json",
        )

    def set_password(self, token, password=NEW_PASSWORD, **extra):
        return self.client.post(
            reverse("password-reset-confirm"),
            {"reset_token": token, "new_password": password, **extra},
            format="json",
        )

    def get_pass(self):
        challenge = self.ask().data["challenge"]
        response = self.check_code(challenge, code_from(mail.outbox[-1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["expires_in"], 600)
        return response.data["reset_token"]

    def test_code_then_password_signs_in_and_trusts_the_phone(self):
        token = self.get_pass()
        # Checking the code changes nothing yet.
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

        old = Token.objects.create(user=self.user)
        response = self.set_password(token, device_id=DEVICE)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["token"], Token.objects.get(user=self.user).key)
        self.assertNotEqual(response.data["token"], old.key)
        self.assertIsNotNone(response.data["device_trusted_until"])
        self.assertTrue(TrustedDevice.objects.filter(user=self.user).exists())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_a_wrong_code_counts_down_and_gives_no_pass(self):
        challenge = self.ask().data["challenge"]
        if code_from(mail.outbox[-1]) == "000000":  # pragma: no cover
            self.skipTest("the random code happened to be 000000")
        response = self.check_code(challenge, "000000")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("4 tries left", response.data["code"][0])
        self.assertNotIn("reset_token", response.data)

    def test_the_code_is_used_up_by_the_check(self):
        challenge = self.ask().data["challenge"]
        code = code_from(mail.outbox[-1])
        self.assertEqual(self.check_code(challenge, code).status_code, 200)
        again = self.check_code(challenge, code)
        self.assertIn("already been used", again.data["code"][0])

    def test_a_weak_password_keeps_the_pass_usable(self):
        token = self.get_pass()
        response = self.set_password(token, password="12345678")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)
        self.assertEqual(self.set_password(token).status_code, status.HTTP_200_OK)

    def test_a_pass_works_once(self):
        token = self.get_pass()
        self.assertEqual(self.set_password(token).status_code, status.HTTP_200_OK)
        again = self.set_password(token, password="Another-Passw0rd-9")
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been used", again.data["reset_token"][0])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_a_pass_expires_after_ten_minutes(self):
        token = self.get_pass()
        later = password_reset.RESET_PASS_TTL + timedelta(seconds=1)
        real_loads = signing.loads

        def loads_later(value, **kwargs):
            kwargs["max_age"] = kwargs["max_age"] - later.total_seconds()
            return real_loads(value, **kwargs)

        with mock.patch.object(password_reset.signing, "loads", loads_later):
            response = self.set_password(token)
        self.assertIn("expired", response.data["reset_token"][0])

    def test_a_forged_pass_is_refused(self):
        forged = signing.dumps({"u": self.user.pk, "p": "x"}, salt="other")
        for token in [forged, "nonsense"]:
            with self.subTest(token=token):
                response = self.set_password(token)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("isn't valid", response.data["reset_token"][0])

    def test_needs_a_pass_or_a_code(self):
        response = self.client.post(
            reverse("password-reset-confirm"),
            {"new_password": NEW_PASSWORD},
            format="json",
        )
        self.assertIn("reset_token", response.data)
        self.assertEqual(LoginChallenge.objects.count(), 0)

    def test_an_account_without_a_password_can_set_one(self):
        # An account made with Google (#130) sets its first password (#142).
        self.user.set_unusable_password()
        self.user.save()
        response = self.set_password(self.get_pass())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
