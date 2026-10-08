"""Write the held-out labelling sheet used to choose alpha (#37).

Usage (from backend/):
    python manage.py export_heldout_labels [--output PATH] [--force]

For each held-out child (recommendations/heldout.py) the sheet holds the
pooled top 5 from the SBERT-only baseline and from the weighted ranking at
every alpha from 0.0 to 1.0, de-duplicated and shuffled with a fixed seed. No
scores, ranks, rule priorities or domains are written, so labelling stays
blind. The children are created in a transaction that is rolled back.

Alongside the sheet it writes a provenance sidecar (heldout_labels.provenance.json)
recording the Published activities, rule weights, catalogue version and
embedding model the pools were built from; evaluate_alpha_grid warns if any
of them have changed since. See data/evaluation/README.md.
"""

import csv
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from activities.models import DevelopmentalActivity
from recommendations import heldout, provenance

DEFAULT_OUTPUT = (
    Path(settings.BASE_DIR).parent / "data" / "evaluation" / "heldout_labels.csv"
)
COLUMNS = [
    "child_id",
    "split",
    "child_profile",
    "activity_id",
    "activity_name",
    "activity_description",
    "age_range",
    "relevance",
    "notes",
    "relevance_rater2",
]
HELDOUT_USERNAME = "heldout@nurtura.invalid"


class Command(BaseCommand):
    help = "Write the pooled, shuffled held-out labelling sheet."

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
        if not DevelopmentalActivity.objects.published().exists():
            raise CommandError("No Published activities, so there is nothing to pool.")

        rows, pooled = [], {}
        with transaction.atomic():
            caregiver = get_user_model().objects.create_user(username=HELDOUT_USERNAME)
            for child in heldout.HELDOUT_CHILDREN:
                profile = heldout.create_child(child, caregiver)
                activities, rankings = heldout.rankings_for(profile)
                ids = heldout.shuffled(heldout.pool(rankings), child.child_id)
                pooled[child.child_id] = ids
                for activity_id in ids:
                    activity = activities[activity_id]
                    rows.append(
                        {
                            "child_id": child.child_id,
                            "split": child.split,
                            "child_profile": child.profile,
                            "activity_id": activity_id,
                            "activity_name": activity.activity_name,
                            "activity_description": activity.description,
                            "age_range": activity.age_range,
                            "relevance": "",
                            "notes": "",
                            "relevance_rater2": "",
                        }
                    )
            transaction.set_rollback(True)

        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        sidecar = provenance.sidecar_path(output)
        provenance.write(sidecar, provenance.snapshot(rows=pooled))

        for child in heldout.HELDOUT_CHILDREN:
            self.stdout.write(
                f"{child.child_id} ({child.split}): {len(pooled[child.child_id])} rows"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(rows)} rows for {len(pooled)} children (pool depth "
                f"{heldout.POOL_DEPTH}, SBERT-only plus {len(heldout.ALPHAS)} "
                f"alpha values) to {output}"
            )
        )
        self.stdout.write(f"Wrote the provenance sidecar to {sidecar}")
