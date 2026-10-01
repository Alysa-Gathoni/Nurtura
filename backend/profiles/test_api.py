"""Role-based authentication and access control tests (FR-01, FR-02)."""

import datetime

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from activities.choices import ContentStatus
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields

from .models import ChildProfile

User = get_user_model()


class UserRoleTests(TestCase):
    def test_new_users_are_caregivers_without_admin_access(self):
        user = User.objects.create_user(username="caregiver", password="x-test-pass")
        self.assertEqual(user.role, User.Role.CAREGIVER)
        self.assertTrue(user.is_caregiver)
        self.assertFalse(user.is_staff)

    def test_administrators_get_admin_site_access(self):
        user = User.objects.create_user(
            username="admin", password="x-test-pass", role=User.Role.ADMINISTRATOR
        )
        self.assertTrue(user.is_administrator)
        self.assertTrue(user.is_staff)

    def test_staff_flag_follows_role(self):
        user = User.objects.create_user(
            username="admin", password="x-test-pass", role=User.Role.ADMINISTRATOR
        )
        user.role = User.Role.CAREGIVER
        user.save()
        self.assertFalse(user.is_staff)
        user.is_staff = True
        user.save()
        self.assertFalse(user.is_staff)

    def test_superusers_are_administrators(self):
        user = User.objects.create_superuser(username="root", password="x-test-pass")
        self.assertTrue(user.is_administrator)
        self.assertTrue(user.is_staff)


class AuthAPITests(APITestCase):
    def setUp(self):
        cache.clear()  # login throttle counts live in the cache

    def register(self, **overrides):
        data = {
            "username": "wanjiru",
            "email": "wanjiru@example.com",
            "password": "Str0ng-Passw0rd!",
        }
        data.update(overrides)
        return self.client.post(reverse("register"), data, format="json")

    def login(self, password="Str0ng-Passw0rd!"):
        return self.client.post(
            reverse("login"),
            {"username": "wanjiru", "password": password},
            format="json",
        )

    def test_register_creates_caregiver_and_returns_token(self):
        response = self.register()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["role"], "caregiver")
        self.assertNotIn("password", response.data["user"])
        user = User.objects.get(username="wanjiru")
        self.assertTrue(user.check_password("Str0ng-Passw0rd!"))
        self.assertEqual(Token.objects.get(user=user).key, response.data["token"])

    def test_cannot_self_register_as_administrator(self):
        response = self.register(role="administrator", is_staff=True)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="wanjiru")
        self.assertTrue(user.is_caregiver)
        self.assertFalse(user.is_staff)

    def test_weak_passwords_rejected(self):
        for password in ("short", "12345678", "wanjiru123"):
            with self.subTest(password=password):
                response = self.register(password=password)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("password", response.data)
        self.assertFalse(User.objects.exists())

    def test_email_required_and_username_unique(self):
        response = self.register(email="")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.register().status_code, status.HTTP_201_CREATED)
        response = self.register(email="other@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_login_me_and_logout(self):
        self.register()
        response = self.login()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["role"], "caregiver")

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        me = self.client.get(reverse("me"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["username"], "wanjiru")

        logout = self.client.post(reverse("logout"))
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)
        me = self.client.get(reverse("me"))
        self.assertEqual(me.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_wrong_password_fails(self):
        self.register()
        response = self.login(password="wrong-password")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn("token", response.data)


class ChildProfileAPITests(APITestCase):
    def setUp(self):
        self.caregiver = User.objects.create_user(
            username="wanjiru", password="x-test-pass"
        )
        self.other_caregiver = User.objects.create_user(
            username="otieno", password="x-test-pass"
        )
        self.administrator = User.objects.create_user(
            username="admin", password="x-test-pass", role=User.Role.ADMINISTRATOR
        )
        self.others_child = ChildProfile.objects.create(
            caregiver=self.other_caregiver,
            name="Baraka",
            date_of_birth=datetime.date(2025, 1, 1),
        )
        self.list_url = reverse("child-list")

    def detail_url(self, child):
        return reverse("child-detail", args=[child.pk])

    def test_unauthenticated_requests_rejected(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_caregiver_creates_child_owned_by_them(self):
        self.client.force_authenticate(self.caregiver)
        response = self.client.post(
            self.list_url,
            {
                "name": "Amani",
                "date_of_birth": "2027-01-15",
                "interests": ["music"],
                "caregiver": self.other_caregiver.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        child = ChildProfile.objects.get(pk=response.data["id"])
        self.assertEqual(child.caregiver, self.caregiver)
        self.assertEqual(child.date_of_birth, datetime.date(2027, 1, 15))

    def test_caregiver_lists_only_their_own_children(self):
        ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Amani",
            date_of_birth=datetime.date(2025, 6, 1),
        )
        self.client.force_authenticate(self.caregiver)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([c["name"] for c in response.data], ["Amani"])

    def test_caregiver_cannot_access_another_caregivers_child(self):
        self.client.force_authenticate(self.caregiver)
        url = self.detail_url(self.others_child)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.patch(url, {"name": "Changed"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)
        self.others_child.refresh_from_db()
        self.assertEqual(self.others_child.name, "Baraka")

    def test_caregiver_updates_and_deletes_own_child(self):
        child = ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Amani",
            date_of_birth=datetime.date(2025, 6, 1),
        )
        self.client.force_authenticate(self.caregiver)
        url = self.detail_url(child)
        response = self.client.patch(url, {"gender": "female"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["gender"], "female")
        self.assertEqual(
            self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT
        )
        self.assertFalse(ChildProfile.objects.filter(pk=child.pk).exists())

    def test_administrators_cannot_use_child_profile_api(self):
        self.client.force_authenticate(self.administrator)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminSiteAccessTests(TestCase):
    def setUp(self):
        self.caregiver = User.objects.create_user(
            username="wanjiru", password="x-test-pass"
        )
        self.administrator = User.objects.create_user(
            username="admin", password="x-test-pass", role=User.Role.ADMINISTRATOR
        )
        self.activities_url = reverse(
            "admin:activities_developmentalactivity_changelist"
        )

    def test_caregiver_cannot_use_admin_site(self):
        self.client.force_login(self.caregiver)
        response = self.client.get(self.activities_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response.url)

    def test_administrator_manages_activities_without_model_permissions(self):
        self.assertFalse(self.administrator.user_permissions.exists())
        self.client.force_login(self.administrator)
        self.assertEqual(self.client.get(self.activities_url).status_code, 200)

        response = self.client.post(
            reverse("admin:activities_developmentalactivity_add"), activity_fields()
        )
        self.assertEqual(response.status_code, 302)
        activity = DevelopmentalActivity.objects.get()
        for action in ("submit_for_review", "publish"):
            self.client.post(
                self.activities_url,
                {"action": action, "_selected_action": [activity.pk]},
            )
        activity.refresh_from_db()
        self.assertEqual(activity.content_status, ContentStatus.PUBLISHED)


class EmailUniquenessTests(APITestCase):
    def register(self, username, email):
        return self.client.post(
            reverse("register"),
            {"username": username, "email": email, "password": "Str0ng-Passw0rd!"},
            format="json",
        )

    def test_register_rejects_email_in_use_ignoring_case(self):
        self.assertEqual(
            self.register("wanjiru", "wanjiru@example.com").status_code,
            status.HTTP_201_CREATED,
        )
        response = self.register("wanjiru2", "Wanjiru@Example.COM")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_database_enforces_unique_email_ignoring_case(self):
        User.objects.create_user(username="a", email="parent@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username="b", email="PARENT@example.com")

    def test_model_validation_reports_duplicate_email(self):
        User.objects.create_user(username="a", email="parent@example.com")
        user = User(username="b", email="Parent@Example.com")
        with self.assertRaises(ValidationError) as ctx:
            user.validate_constraints()
        self.assertIn("A user with this email already exists.", ctx.exception.messages)

    def test_blank_emails_allowed_more_than_once(self):
        User.objects.create_superuser(username="root1", password="x-test-pass")
        User.objects.create_superuser(username="root2", password="x-test-pass")
        self.assertEqual(User.objects.filter(email="").count(), 2)


class LoginThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user(username="wanjiru", password="Str0ng-Passw0rd!")

    def login(self, password):
        return self.client.post(
            reverse("login"),
            {"username": "wanjiru", "password": password},
            format="json",
        )

    def test_login_throttled_after_five_attempts_per_minute(self):
        for _ in range(5):
            self.assertEqual(
                self.login("wrong-password").status_code, status.HTTP_400_BAD_REQUEST
            )
        # Even the correct password is refused once the limit is reached.
        response = self.login("Str0ng-Passw0rd!")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertNotIn("token", response.data)

    def test_other_endpoints_not_throttled_by_login_limit(self):
        for _ in range(5):
            self.login("wrong-password")
        response = self.client.post(
            reverse("register"),
            {
                "username": "otieno",
                "email": "otieno@example.com",
                "password": "Str0ng-Passw0rd!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class CorsTests(APITestCase):
    """The Flutter web app (served on a random localhost port) can call the API."""

    def preflight(self, origin):
        return self.client.options(
            reverse("login"),
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )

    def test_local_flutter_web_origin_allowed(self):
        response = self.preflight("http://localhost:61234")
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:61234",
        )
        self.assertIn(
            "authorization", response.headers.get("access-control-allow-headers", "")
        )

    def test_other_origins_not_allowed(self):
        response = self.preflight("https://example.com")
        self.assertNotIn("access-control-allow-origin", response.headers)
