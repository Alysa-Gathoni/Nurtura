"""Write the CSV template for hand-labelling retrieval relevance (#36).

Usage (from backend/):
    python manage.py export_relevance_template [--output PATH] [--force]

One row per (sample child, eligible activity): expecting-parent samples get
Prenatal activities, every other sample gets the post-natal ones. Activities
are included whatever their content status, so labelling can happen before
review. Fill in `relevance` with 0, 1 or 2; see data/evaluation/README.md.
"""

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from activities.choices import AgeRange
from activities.models import DevelopmentalActivity
from recommendations.samples import SAMPLE_PROFILES

DEFAULT_OUTPUT = (
    Path(settings.BASE_DIR).parent
    / "data"
    / "evaluation"
    / "relevance_labels_template.csv"
)
COLUMNS = [
    "sample_key",
    "sample_description",
    "expected_domains",
    "activity_id",
    "activity_name",
    "developmental_domain",
    "age_range",
    "developmental_goal",
    "activity_description",
    "content_status",
    "relevance",
    "notes",
]


class Command(BaseCommand):
    help = "Write the relevance-labelling CSV template for the sample children."

    def add_arguments(self, parser):
        parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite the output file if it exists.",
        )

    def handle(self, *args, **options):
        output = options["output"]
        if output.exists() and not options["force"]:
            raise CommandError(
                f"{output} already exists. Use --force to overwrite it (this "
                "would discard any labels filled in there)."
            )
        activities = list(DevelopmentalActivity.objects.order_by("activity_id"))
        prenatal = [a for a in activities if a.age_range == AgeRange.PRENATAL]
        postnatal = [a for a in activities if a.age_range != AgeRange.PRENATAL]

        rows = []
        for sample in SAMPLE_PROFILES:
            pool = prenatal if sample.age_months < 0 else postnatal
            for activity in pool:
                rows.append(
                    {
                        "sample_key": sample.key,
                        "sample_description": sample.note,
                        "expected_domains": " + ".join(sample.expected_domains),
                        "activity_id": activity.activity_id,
                        "activity_name": activity.activity_name,
                        "developmental_domain": activity.developmental_domain,
                        "age_range": activity.age_range,
                        "developmental_goal": activity.developmental_goal,
                        "activity_description": activity.description,
                        "content_status": activity.get_content_status_display(),
                        "relevance": "",
                        "notes": "",
                    }
                )

        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(rows)} rows ({len(SAMPLE_PROFILES)} sample children, "
                f"{len(postnatal)} post-natal and {len(prenatal)} prenatal "
                f"activities) to {output}"
            )
        )
