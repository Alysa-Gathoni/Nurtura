"""Loading plain_aim never changes content status (#76)."""

import csv
import tempfile
from io import StringIO
from pathlib import Path

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.forms.models import model_to_dict
from django.test import TestCase
from django.urls import reverse

from .choices import ContentStatus
from .models import DevelopmentalActivity

COLUMNS = ["activity_id", "plain_aim_draft", "approved", "reviewer_edit"]


def aim_for(activity_id):
    return f"help your child enjoy activity {activity_id[-2:]}"


class PlainAimLoadingTestCase(TestCase):
    """The real 54-activity dataset, all Published through the admin workflow."""

    def setUp(self):
        call_command("seed_activities", stdout=StringIO())
        self.admin_user = get_user_model().objects.create_superuser(
            username="admin", password="x-test-pass"
        )
        self.client.force_login(self.admin_user)
        changelist = reverse("admin:activities_developmentalactivity_changelist")
        ids = list(DevelopmentalActivity.objects.values_list("pk", flat=True))
        for action in ("submit_for_review", "publish"):
            self.client.post(changelist, {"action": action, "_selected_action": ids})
        self.total = DevelopmentalActivity.objects.count()
        self.assertEqual(DevelopmentalActivity.objects.published().count(), self.total)
        self.log_entries = LogEntry.objects.count()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "aims.csv"

    def write(self, rows):
        with open(self.path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow({c: "" for c in COLUMNS} | row)

    def all_drafts(self, approved=""):
        self.write(
            [
                {"activity_id": a, "plain_aim_draft": aim_for(a), "approved": approved}
                for a in DevelopmentalActivity.objects.values_list(
                    "activity_id", flat=True
                )
            ]
        )

    def load(self, *args):
        out = StringIO()
        call_command("load_plain_aims", "--file", str(self.path), *args, stdout=out)
        return out.getvalue()

    def assert_status_untouched(self):
        self.assertEqual(DevelopmentalActivity.objects.published().count(), self.total)
        self.assertEqual(LogEntry.objects.count(), self.log_entries)


class LoadPlainAimsTests(PlainAimLoadingTestCase):
    def test_loading_twice_keeps_every_activity_published(self):
        self.all_drafts()
        first = self.load("--all-drafts")
        self.assertIn(f"{self.total} updated, 0 unchanged", first)
        self.assert_status_untouched()
        second = self.load("--all-drafts")
        self.assertIn(f"0 updated, {self.total} unchanged", second)
        self.assert_status_untouched()
        self.assertFalse(DevelopmentalActivity.objects.filter(plain_aim="").exists())

    def test_only_approved_rows_by_default_and_reviewer_edit_wins(self):
        self.write(
            [
                {
                    "activity_id": "ACT-0001",
                    "plain_aim_draft": aim_for("ACT-0001"),
                    "approved": "yes",
                    "reviewer_edit": "help your baby get stronger",
                },
                {
                    "activity_id": "ACT-0002",
                    "plain_aim_draft": aim_for("ACT-0002"),
                    "approved": "Yes",
                },
                {"activity_id": "ACT-0003", "plain_aim_draft": aim_for("ACT-0003")},
            ]
        )
        output = self.load()
        self.assertIn("2 plain_aim row(s): 2 updated", output)
        self.assertIn("1 not approved, skipped", output)
        aims = dict(
            DevelopmentalActivity.objects.values_list("activity_id", "plain_aim")
        )
        self.assertEqual(aims["ACT-0001"], "help your baby get stronger")
        self.assertEqual(aims["ACT-0002"], aim_for("ACT-0002"))
        self.assertEqual(aims["ACT-0003"], "")
        self.assert_status_untouched()

    def test_invalid_rows_write_nothing(self):
        self.write(
            [
                {
                    "activity_id": "ACT-0001",
                    "plain_aim_draft": aim_for("ACT-0001"),
                    "approved": "yes",
                },
                {
                    "activity_id": "ACT-0002",
                    "plain_aim_draft": "Too capitalised.",
                    "approved": "yes",
                },
                {
                    "activity_id": "ACT-9999",
                    "plain_aim_draft": "help",
                    "approved": "yes",
                },
            ]
        )
        with self.assertRaisesMessage(CommandError, "2 invalid row(s)"):
            call_command(
                "load_plain_aims",
                "--file",
                str(self.path),
                stdout=StringIO(),
                stderr=StringIO(),
            )
        self.assertFalse(DevelopmentalActivity.objects.exclude(plain_aim="").exists())

    def test_dry_run(self):
        self.all_drafts(approved="yes")
        self.assertIn("dry run", self.load("--dry-run"))
        self.assertFalse(DevelopmentalActivity.objects.exclude(plain_aim="").exists())


class PlainAimNeverReturnsToDraftTests(PlainAimLoadingTestCase):
    def test_reseeding_after_loading_keeps_aims_and_status(self):
        """seed_activities doesn't read plain_aim, so it can't count it as a
        content change: re-seeding leaves the aims alone and returns nothing
        to Draft."""
        self.all_drafts()
        self.load("--all-drafts")
        out = StringIO()
        call_command("seed_activities", stdout=out)
        self.assertNotIn("returned to Draft", out.getvalue())
        self.assertIn(f"{self.total} unchanged", out.getvalue())
        self.assert_status_untouched()
        self.assertFalse(DevelopmentalActivity.objects.filter(plain_aim="").exists())

    def test_admin_form_edit_of_plain_aim_keeps_published(self):
        activity = DevelopmentalActivity.objects.get(activity_id="ACT-0001")
        data = {
            k: v
            for k, v in model_to_dict(activity).items()
            if k not in ("id", "content_status") and v is not None
        }
        data["plain_aim"] = "help your baby build strength for rolling and sitting"
        response = self.client.post(
            reverse(
                "admin:activities_developmentalactivity_change", args=[activity.pk]
            ),
            data,
        )
        self.assertEqual(response.status_code, 302)
        activity.refresh_from_db()
        self.assertEqual(activity.plain_aim, data["plain_aim"])
        self.assertEqual(DevelopmentalActivity.objects.published().count(), self.total)
        # One ordinary "changed" entry, and no status change.
        new = LogEntry.objects.order_by("-pk").first()
        self.assertEqual(LogEntry.objects.count(), self.log_entries + 1)
        self.assertIn("Plain aim", new.get_change_message())
        self.assertNotIn("Status", new.get_change_message())

    def test_admin_form_rejects_an_invalid_aim(self):
        activity = DevelopmentalActivity.objects.get(activity_id="ACT-0001")
        data = {
            k: v
            for k, v in model_to_dict(activity).items()
            if k not in ("id", "content_status") and v is not None
        }
        data["plain_aim"] = "Help your baby."
        response = self.client.post(
            reverse(
                "admin:activities_developmentalactivity_change", args=[activity.pk]
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)  # form shown again with errors
        activity.refresh_from_db()
        self.assertEqual(activity.plain_aim, "")
        self.assert_status_untouched()
