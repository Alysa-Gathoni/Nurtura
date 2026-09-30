"""Tests for the seed_activities management command (#5)."""

import csv
import tempfile
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from .choices import ContentStatus
from .management.commands.seed_activities import DEFAULT_FILE, FIELD_MAP
from .models import DevelopmentalActivity

COLUMNS = list(FIELD_MAP) + ["content_status"]


def csv_row(**overrides):
    row = {
        "activity_id": "ACT-0001",
        "activity_name": "Tummy Time",
        "developmental_domain": "Motor",
        "recommended_age_range": "0-3 months",
        "developmental_goal": "Build neck strength",
        "required_materials": "Blanket",
        "difficulty_level": "Beginner",
        "activity_description": "Supervised time on the tummy.",
        "cultural_relevance": "Can be done on a kanga.",
        "source": "Pathways.org",
        "source_url": "https://pathways.org/tummy-time",
        "content_status": "Draft",
    }
    row.update(overrides)
    return row


class SeedActivitiesTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write_csv(self, rows, columns=COLUMNS):
        path = Path(self.tmp.name) / "activities.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def seed(self, path=None, *extra):
        out, err = StringIO(), StringIO()
        args = ["seed_activities", *extra]
        if path is not None:
            args += ["--file", str(path)]
        call_command(*args, stdout=out, stderr=err)
        return out.getvalue()

    def test_loads_real_processed_dataset_as_draft(self):
        output = self.seed()
        self.assertIn("38 rows: 38 created, 0 updated, 0 unchanged", output)
        activities = DevelopmentalActivity.objects.all()
        self.assertEqual(activities.count(), 38)
        self.assertEqual(
            set(activities.values_list("content_status", flat=True)),
            {ContentStatus.DRAFT},
        )
        self.assertEqual(activities.exclude(source_url="").count(), 14)
        self.assertTrue(
            DevelopmentalActivity.objects.get(
                activity_id="ACT-0025"
            ).source_url.startswith("https://")
        )
        self.assertEqual(DevelopmentalActivity.objects.published().count(), 0)
        self.assertTrue(DEFAULT_FILE.exists())

    def test_rerun_does_not_duplicate(self):
        self.seed()
        output = self.seed()
        self.assertIn("38 rows: 0 created, 0 updated, 38 unchanged", output)
        self.assertEqual(DevelopmentalActivity.objects.count(), 38)

    def test_fields_mapped_from_csv_columns(self):
        self.seed(self.write_csv([csv_row()]))
        activity = DevelopmentalActivity.objects.get()
        self.assertEqual(activity.age_range, "0-3 months")
        self.assertEqual(activity.materials, "Blanket")
        self.assertEqual(activity.description, "Supervised time on the tummy.")
        self.assertEqual(activity.source_url, "https://pathways.org/tummy-time")

    def test_new_activities_always_draft(self):
        output = self.seed(self.write_csv([csv_row(content_status="Published")]))
        activity = DevelopmentalActivity.objects.get()
        self.assertEqual(activity.content_status, ContentStatus.DRAFT)
        self.assertIn("CSV status 'Published' ignored", output)

    def test_changed_rows_are_updated(self):
        self.seed(self.write_csv([csv_row()]))
        output = self.seed(
            self.write_csv([csv_row(activity_description="Updated wording.")])
        )
        self.assertIn("[UPDATED] ACT-0001 Tummy Time: description", output)
        activity = DevelopmentalActivity.objects.get()
        self.assertEqual(activity.description, "Updated wording.")

    def test_reseed_keeps_status_set_in_admin(self):
        self.seed(self.write_csv([csv_row()]))
        activity = DevelopmentalActivity.objects.get()
        activity.transition_to(ContentStatus.UNDER_REVIEW)
        activity.transition_to(ContentStatus.PUBLISHED)
        self.seed(self.write_csv([csv_row()]))
        activity.refresh_from_db()
        self.assertEqual(activity.content_status, ContentStatus.PUBLISHED)

    def test_changed_published_activity_returns_to_draft(self):
        self.seed(self.write_csv([csv_row()]))
        activity = DevelopmentalActivity.objects.get()
        activity.transition_to(ContentStatus.UNDER_REVIEW)
        activity.transition_to(ContentStatus.PUBLISHED)
        output = self.seed(
            self.write_csv([csv_row(activity_description="Updated wording.")])
        )
        activity.refresh_from_db()
        self.assertEqual(activity.content_status, ContentStatus.DRAFT)
        self.assertIn("returned to Draft for re-review", output)

    def test_invalid_row_means_nothing_is_written(self):
        path = self.write_csv(
            [
                csv_row(),
                csv_row(
                    activity_id="ACT-0002",
                    activity_name="Bubbles",
                    developmental_domain="Visual",
                ),
            ]
        )
        with self.assertRaisesMessage(CommandError, "nothing was written"):
            self.seed(path)
        self.assertFalse(DevelopmentalActivity.objects.exists())

    def test_duplicates_in_file_rejected(self):
        for duplicate in (
            csv_row(activity_name="Rolling"),
            csv_row(activity_id="ACT-0002", activity_name="TUMMY TIME"),
        ):
            with self.subTest(duplicate=duplicate["activity_name"]):
                with self.assertRaises(CommandError):
                    self.seed(self.write_csv([csv_row(), duplicate]))
                self.assertFalse(DevelopmentalActivity.objects.exists())

    def test_missing_file_or_column_rejected(self):
        with self.assertRaisesMessage(CommandError, "Cannot read"):
            self.seed(Path(self.tmp.name) / "missing.csv")
        path = self.write_csv(
            [csv_row()], columns=[c for c in COLUMNS if c != "source_url"]
        )
        with self.assertRaisesMessage(CommandError, "missing column(s): source_url"):
            self.seed(path)

    def test_dry_run_saves_nothing(self):
        output = self.seed(None, "--dry-run")
        self.assertIn("38 created", output)
        self.assertIn("dry run - nothing saved", output)
        self.assertFalse(DevelopmentalActivity.objects.exists())


class SourceLinkAdminTests(TestCase):
    def setUp(self):
        call_command("seed_activities", stdout=StringIO())
        admin = get_user_model().objects.create_superuser(
            username="admin", password="x-test-pass"
        )
        self.client.force_login(admin)
        self.url = reverse("admin:activities_developmentalactivity_changelist")

    def test_filter_by_source_link(self):
        with_link = self.client.get(self.url, {"has_source_url": "yes"})
        self.assertContains(with_link, "14 developmental activities")
        self.assertContains(with_link, 'target="_blank"')
        without_link = self.client.get(self.url, {"has_source_url": "no"})
        self.assertContains(without_link, "24 developmental activities")
