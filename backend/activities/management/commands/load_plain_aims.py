"""Load reviewed plain_aim wording into activities (#76).

Usage (from backend/):
    python manage.py load_plain_aims [--file PATH] [--dry-run] [--all-drafts]

Reads data/review/plain_aims_draft.csv (#70). By default only rows marked
approved ("yes") are loaded; a reviewer_edit, when filled, replaces the
draft. --all-drafts loads every draft regardless of approval and is meant
for rehearsals in a rolled-back transaction or a scratch database.

plain_aim is caregiver-facing wording only: it is outside the embedding
text, the ranking and the evaluation's provenance hash. So, unlike
seed_activities, this command never changes content_status, never sends an
activity back to Draft and writes no status history; it updates the
plain_aim field and nothing else. Every row is validated first; if any row
is invalid, nothing is written. Re-running it changes nothing.
"""

import csv
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from activities.models import DevelopmentalActivity, validate_plain_aim

DEFAULT_FILE = (
    Path(settings.BASE_DIR).parent / "data" / "review" / "plain_aims_draft.csv"
)
COLUMNS = ("activity_id", "plain_aim_draft", "approved", "reviewer_edit")


class Command(BaseCommand):
    help = "Load reviewed plain_aim wording; never changes content status."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report what would change without saving.",
        )
        parser.add_argument(
            "--all-drafts",
            action="store_true",
            help="Load every draft, approved or not (rehearsals only).",
        )

    def handle(self, *args, **options):
        rows = self.read(options["file"])
        planned, errors = [], []
        for line, row in rows:
            activity_id = (row["activity_id"] or "").strip()
            approved = (row["approved"] or "").strip().lower() == "yes"
            if not approved and not options["all_drafts"]:
                continue
            text = (row["reviewer_edit"] or "").strip() or (
                row["plain_aim_draft"] or ""
            ).strip()
            activity = DevelopmentalActivity.objects.filter(
                activity_id=activity_id
            ).first()
            if activity is None:
                errors.append(f"line {line}: unknown activity_id '{activity_id}'")
                continue
            if not text:
                errors.append(f"line {line} ({activity_id}): no wording to load")
                continue
            try:
                validate_plain_aim(text)
            except ValidationError as exc:
                errors.append(f"line {line} ({activity_id}): {' '.join(exc.messages)}")
                continue
            planned.append((activity, text))

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(f"[INVALID] {error}"))
            raise CommandError(f"{len(errors)} invalid row(s); nothing was written.")

        updated = unchanged = 0
        with transaction.atomic():
            for activity, text in planned:
                if activity.plain_aim == text:
                    unchanged += 1
                    continue
                activity.plain_aim = text
                # Only this field: status and every other field are untouched.
                activity.save(update_fields=["plain_aim", "updated_at"])
                updated += 1
                self.stdout.write(f"[UPDATED] {activity.activity_id}: {text}")
            if options["dry_run"]:
                transaction.set_rollback(True)

        summary = (
            f"{len(planned)} plain_aim row(s): {updated} updated, "
            f"{unchanged} unchanged; content status untouched"
        )
        if not options["all_drafts"]:
            skipped = len(rows) - len(planned)
            summary += f"; {skipped} not approved, skipped"
        if options["dry_run"]:
            summary += " (dry run - nothing saved)"
        self.stdout.write(self.style.SUCCESS(summary))

    def read(self, path):
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
                if missing:
                    raise CommandError(
                        f"{path} is missing column(s): {', '.join(missing)}"
                    )
                return [(reader.line_num, row) for row in reader]
        except OSError as exc:
            raise CommandError(f"Cannot read {path}: {exc}") from exc
