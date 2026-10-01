"""Load the guideline milestone catalogue into ReferenceMilestone.

Usage (from backend/):
    python manage.py seed_milestones [--file PATH] [--dry-run]

Rows are matched on milestone_key, so re-running updates entries instead of
duplicating them. Every row is validated before anything is written; if any
row is invalid, nothing is saved.

New entries start unverified. Re-seeding keeps the verified flag set in the
admin, except that an entry whose content changes is marked unverified again
so it is re-checked against its source.
"""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from profiles.models import ReferenceMilestone

DEFAULT_FILE = (
    Path(settings.BASE_DIR).parent
    / "data"
    / "reference"
    / "developmental_milestones.csv"
)
COLUMNS = [
    "milestone_key",
    "source",
    "expected_age_months",
    "domain",
    "description",
    "source_reference",
    "notes",
]


class Command(BaseCommand):
    help = "Load data/reference/developmental_milestones.csv into ReferenceMilestone."

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
        planned, errors = self.validate(self.read_rows(path))
        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(f"[INVALID] {error}"))
            raise CommandError(
                f"{len(errors)} invalid row(s) in {path}; nothing was written."
            )

        counts = {"created": 0, "updated": 0, "unchanged": 0, "unverified": 0}
        with transaction.atomic():
            for milestone, action, changed in planned:
                if action == "created":
                    milestone.save()
                elif action == "updated":
                    note = ""
                    if milestone.verified:
                        milestone.verified = False
                        counts["unverified"] += 1
                        note = " - content changed, marked unverified for re-checking"
                    milestone.save()
                    self.stdout.write(
                        f"[UPDATED] {milestone.milestone_key}: {', '.join(changed)}{note}"
                    )
                counts[action] += 1
            if options["dry_run"]:
                transaction.set_rollback(True)

        summary = (
            f"{len(planned)} milestones: {counts['created']} created, "
            f"{counts['updated']} updated, {counts['unchanged']} unchanged"
        )
        if counts["unverified"]:
            summary += f"; {counts['unverified']} marked unverified"
        if options["dry_run"]:
            summary += " (dry run - nothing saved)"
        self.stdout.write(self.style.SUCCESS(summary))

    def read_rows(self, path):
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

    def validate(self, rows):
        """Return ([(milestone, action, changed_fields)], [error messages])."""
        planned, errors, seen = [], [], set()
        for line, row in rows:
            values = {column: (row.get(column) or "").strip() for column in COLUMNS}
            key = values["milestone_key"] or "<no key>"
            where = f"line {line} ({key})"
            if key in seen:
                errors.append(f"{where}: duplicate milestone_key in file")
                continue
            seen.add(key)
            try:
                values["expected_age_months"] = Decimal(values["expected_age_months"])
            except InvalidOperation:
                errors.append(
                    f"{where}: expected_age_months "
                    f"'{values['expected_age_months']}' is not a number"
                )
                continue

            milestone = ReferenceMilestone.objects.filter(milestone_key=key).first()
            if milestone is None:
                milestone = ReferenceMilestone(verified=False, **values)
                action, changed = "created", []
            else:
                changed = [c for c, v in values.items() if getattr(milestone, c) != v]
                for column in changed:
                    setattr(milestone, column, values[column])
                action = "updated" if changed else "unchanged"

            try:
                milestone.full_clean()
            except ValidationError as exc:
                problems = "; ".join(
                    f"{field}: {' '.join(msgs)}"
                    for field, msgs in exc.message_dict.items()
                )
                errors.append(f"{where}: {problems}")
                continue
            planned.append((milestone, action, changed))
        return planned, errors
