"""The administrator site carries Nurtura's theme and branding (#114)."""

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class AdminThemeTests(TestCase):
    def assert_branded(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "nurtura/admin.css")
        self.assertContains(response, 'class="nurtura-mark"')
        self.assertContains(response, "Nurtura")
        self.assertNotContains(response, "Django administration")

    def test_login_page_is_branded(self):
        self.assert_branded(self.client.get(reverse("admin:login")))

    def test_admin_pages_are_branded(self):
        User = get_user_model()
        admin = User.objects.create_user(
            username="admin@example.com",
            password="x-test-pass",
            role=User.Role.ADMINISTRATOR,
        )
        self.client.force_login(admin)
        index = self.client.get(reverse("admin:index"))
        self.assert_branded(index)
        self.assertContains(index, "Content, milestones and feedback")
        self.assert_branded(
            self.client.get(reverse("admin:feedback_feedback_changelist"))
        )

    def test_stylesheet_is_served_from_the_project(self):
        path = finders.find("nurtura/admin.css")
        self.assertIsNotNone(path)
        with open(path, encoding="utf-8") as css:
            text = css.read()
        # Both themes override the admin's own colour variables.
        self.assertIn('html[data-theme="dark"]', text)
        self.assertIn("--button-bg: var(--n-terracotta)", text)
