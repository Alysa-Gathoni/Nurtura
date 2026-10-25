"""Continue with Google (#130). Google's token check is mocked: these tests
cover what the backend does with its answer, without the network."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from google.auth import exceptions as google_exceptions
from rest_framework import status
from rest_framework.authtoken.models import Token

from .models import TrustedDevice
from .test_two_factor import DEVICE, PASSWORD, TwoFactorAPITestCase

User = get_user_model()
CLIENT_ID = "test-web-client.apps.googleusercontent.com"
VERIFY = "profiles.google_sign_in.id_token.verify_oauth2_token"


def google_says(email="wanjiru@example.com", verified=True):
    return {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "email": email,
        "email_verified": verified,
        "name": "Not stored",
    }


@override_settings(GOOGLE_OAUTH_CLIENT_IDS=[CLIENT_ID])
class GoogleSignInTests(TwoFactorAPITestCase):
    def google(self, answer=None, token="google-id-token", **extra):
        with mock.patch(VERIFY, return_value=answer or google_says()) as verify:
            response = self.client.post(
                reverse("google-sign-in"),
                {"id_token": token, **extra},
                format="json",
            )
        self.verify_call = verify
        return response

    def test_signs_in_the_account_with_that_email_without_a_code(self):
        response = self.google(device_id=DEVICE)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["created"])
        self.assertEqual(response.data["user"]["username"], "wanjiru")
        self.assertEqual(response.data["token"], Token.objects.get(user=self.user).key)
        self.assertEqual(mail.outbox, [])
        # The token was checked for this app's client ID.
        _, kwargs = self.verify_call.call_args
        self.assertEqual(kwargs["audience"], [CLIENT_ID])
        self.assertEqual(self.verify_call.call_args.args[0], "google-id-token")

    def test_the_email_is_matched_ignoring_case(self):
        response = self.google(google_says("Wanjiru@Example.com"))
        self.assertEqual(response.data["user"]["username"], "wanjiru")

    def test_the_password_still_works_afterwards(self):
        self.google()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_a_new_email_creates_a_caregiver_with_no_password(self):
        response = self.google(google_says("New.Parent@Example.com"))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["created"])
        user = User.objects.get(email="new.parent@example.com")
        self.assertEqual(user.username, "new.parent@example.com")
        self.assertEqual(user.role, User.Role.CAREGIVER)
        self.assertFalse(user.has_usable_password())
        # Only the email is kept from Google.
        self.assertEqual((user.first_name, user.last_name), ("", ""))
        self.assertEqual(response.data["user"]["role"], "caregiver")

    def test_trusts_this_phone_unless_asked_not_to(self):
        self.assertIsNotNone(self.google(device_id=DEVICE).data["device_trusted_until"])
        TrustedDevice.objects.all().delete()
        response = self.google(device_id=DEVICE, remember_device=False)
        self.assertIsNone(response.data["device_trusted_until"])
        self.assertFalse(TrustedDevice.objects.exists())

    def test_an_unverified_google_email_is_refused(self):
        response = self.google(google_says(verified=False))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("isn't verified", response.data["non_field_errors"][0])
        self.assertFalse(Token.objects.exists())

    def test_a_token_google_rejects_is_refused(self):
        with mock.patch(VERIFY, side_effect=ValueError("Token expired")):
            response = self.client.post(
                reverse("google-sign-in"), {"id_token": "old"}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("didn't work", response.data["non_field_errors"][0])

    def test_a_missing_token_is_refused_without_asking_google(self):
        with mock.patch(VERIFY) as verify:
            response = self.client.post(reverse("google-sign-in"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        verify.assert_not_called()

    def test_google_unreachable_is_a_503(self):
        with mock.patch(
            VERIFY, side_effect=google_exceptions.TransportError("no network")
        ):
            response = self.client.post(
                reverse("google-sign-in"), {"id_token": "t"}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_administrators_must_use_email_and_password(self):
        User.objects.create_superuser(
            username="lead", email="lead@example.com", password=PASSWORD
        )
        response = self.google(google_says("lead@example.com"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Administrators", response.data["non_field_errors"][0])
        self.assertFalse(Token.objects.exists())

    def test_a_switched_off_account_is_refused(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        response = self.google()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Token.objects.exists())

    def test_an_email_used_as_another_username_is_refused(self):
        User.objects.create_user(
            username="taken@example.com",
            email="someone-else@example.com",
            password=PASSWORD,
        )
        response = self.google(google_says("taken@example.com"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.filter(email="taken@example.com").count(), 0)

    def test_a_google_account_can_set_a_password_with_forgot_password(self):
        self.google(google_says("new@example.com"))
        response = self.client.post(
            reverse("password-reset"), {"email": "new@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(mail.outbox[-1].to, ["new@example.com"])


@override_settings(GOOGLE_OAUTH_CLIENT_IDS=[])
class GoogleSignInOffTests(TwoFactorAPITestCase):
    def test_off_until_a_client_id_is_set(self):
        with mock.patch(VERIFY) as verify:
            response = self.client.post(
                reverse("google-sign-in"), {"id_token": "t"}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("isn't set up", response.data["detail"])
        verify.assert_not_called()
