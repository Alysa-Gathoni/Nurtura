"""Load the cleaned activity dataset into the database.

Usage (from backend/):
    python manage.py seed_activities [--file PATH] [--dry-run]

Rows are matched on activity_id, so re-running updates activities instead of
duplicating them. Every row is validated before anything is written; if any
row is invalid, nothing is saved.

Content status (FR-13, DR-12): new activities are always created as Draft so
they go through admin review before they can be recommended. Re-seeding keeps
the status set in the admin, except that an Under Review or Published activity
whose content changes is returned to Draft for re-review.
"""

import csv
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from activities.choices import ContentStatus
from activities.models import DevelopmentalActivity

DEFAULT_FILE = (
    Path(settings.BASE_DIR).parent / "data" / "processed" / "activities_clean.csv"
)

# CSV column -> model field
FIELD_MAP = {
    "activity_id": "activity_id",
    "activity_name": "activity_name",
    "developmental_domain": "developmental_domain",
    "recommended_age_range": "age_range",
    "developmental_goal": "developmental_goal",
    "required_materials": "materials",
    "difficulty_level": "difficulty_level",
    "activity_description": "description",
    "cultural_relevance": "cultural_relevance",
    "source": "source",
    "source_url": "source_url",
}


class Command(BaseCommand):
    help = "Load data/processed/activities_clean.csv into DevelopmentalActivity."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=Path,
            default=DEFAULT_FILE,
            help=f"CSV to load (default: {DEFAULT_FILE}).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report what would change without saving.",
        )

    def handle(self, *args, **options):
        path = options["file"]
        rows = self.read_rows(path)
        planned, errors = self.validate(rows)

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(f"[INVALID] {error}"))
            raise CommandError(
                f"{len(errors)} invalid row(s) in {path}; nothing was written."
            )

        counts = {"created": 0, "updated": 0, "unchanged": 0, "returned": 0}
        with transaction.atomic():
            for activity, action, changed in planned:
                label = f"{activity.activity_id} {activity.activity_name}"
                if action == "created":
                    activity.save()
                    self.stdout.write(f"[CREATED] {label} (Draft)")
                elif action == "updated":
                    note = ""
                    if activity.content_status != ContentStatus.DRAFT:
                        activity.content_status = ContentStatus.DRAFT
                        counts["returned"] += 1
                        note = " - content changed, returned to Draft for re-review"
                    activity.save()
                    self.stdout.write(f"[UPDATED] {label}: {', '.join(changed)}{note}")
                else:
                    self.stdout.write(f"[UNCHANGED] {label}")
                counts[action] += 1
            if options["dry_run"]:
                transaction.set_rollback(True)

        summary = (
            f"{len(planned)} rows: {counts['created']} created, "
            f"{counts['updated']} updated, {counts['unchanged']} unchanged"
        )
        if counts["returned"]:
            summary += f"; {counts['returned']} returned to Draft for re-review"
        if options["dry_run"]:
            summary += " (dry run - nothing saved)"
        self.stdout.write(self.style.SUCCESS(summary))

    def read_rows(self, path):
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                missing = [c for c in FIELD_MAP if c not in (reader.fieldnames or [])]
                if missing:
                    raise CommandError(
                        f"{path} is missing column(s): {', '.join(missing)}"
                    )
                return [(reader.line_num, row) for row in reader]
        except OSError as exc:
            raise CommandError(f"Cannot read {path}: {exc}") from exc

    def validate(self, rows):
        """Return ([(activity, action, changed_fields)], [error messages])."""
        planned, errors = [], []
        seen_ids, seen_names = set(), set()

        for line, row in rows:
            values = {
                field: (row.get(column) or "").strip()
                for column, field in FIELD_MAP.items()
            }
            activity_id = values["activity_id"] or "<no id>"
            where = f"line {line} ({activity_id})"

            name_key = (
                values["activity_name"].lower(),
                values["developmental_domain"],
            )
            if values["activity_id"] in seen_ids:
                errors.append(f"{where}: duplicate activity_id in file")
                continue
            if name_key in seen_names:
                errors.append(f"{where}: duplicate activity name in the same domain")
                continue
            seen_ids.add(values["activity_id"])
            seen_names.add(name_key)

            csv_status = (row.get("content_status") or "").strip()
            if csv_status and csv_status.lower() != "draft":
                self.stdout.write(
                    self.style.WARNING(
                        f"[NOTE] {where}: CSV status '{csv_status}' ignored; "
                        "status is managed in the admin review workflow"
                    )
                )

            activity = DevelopmentalActivity.objects.filter(
                activity_id=values["activity_id"]
            ).first()
            if activity is None:
                activity = DevelopmentalActivity(
                    content_status=ContentStatus.DRAFT, **values
                )
                action, changed = "created", []
            else:
                changed = [f for f, v in values.items() if getattr(activity, f) != v]
                for field in changed:
                    setattr(activity, field, values[field])
                action = "updated" if changed else "unchanged"

            try:
                activity.full_clean()
            except ValidationError as exc:
                problems = "; ".join(
                    f"{field}: {' '.join(msgs)}"
                    for field, msgs in exc.message_dict.items()
                )
                errors.append(f"{where}: {problems}")
                continue
            planned.append((activity, action, changed))

        return planned, errors
