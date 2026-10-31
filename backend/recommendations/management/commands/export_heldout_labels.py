"""Write the held-out labelling sheet used to choose alpha (#37).

Usage (from backend/):
    python manage.py export_heldout_labels [--output PATH] [--force]
                                           [--carry-labels PATH]

For each held-out child (recommendations/heldout.py) the sheet holds the
pooled top 5 from the SBERT-only baseline and from the weighted ranking at
every alpha from 0.0 to 1.0, de-duplicated and shuffled with a fixed seed. No
scores, ranks, rule priorities or domains are written, so labelling stays
blind. The children are created in a transaction that is rolled back.

Alongside the sheet it writes a provenance sidecar (heldout_labels.provenance.json)
recording the Published activities, rule weights, catalogue version and
embedding model the pools were built from; evaluate_alpha_grid warns if any
of them have changed since. See data/evaluation/README.md.

--carry-labels copies relevance, notes and relevance_rater2 from an earlier
sheet for each (child, activity) pair whose activity name and description are
the same in both sheets (#168), so only new or changed pairs need labelling.
Labels were given blind in the earlier sheet, so carrying them reveals
nothing about the new rankings.
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
        parser.add_argument(
            "--carry-labels",
            type=Path,
            help="Earlier sheet to copy labels from where the activity is unchanged.",
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
        earlier = (
            read_labels(options["carry_labels"]) if options["carry_labels"] else {}
        )

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

        carried = sum(carry(row, earlier) for row in rows)

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
        if options["carry_labels"]:
            self.stdout.write(
                f"Carried {carried} labelled row(s) from {options['carry_labels']}; "
                f"{sum(1 for r in rows if not r['relevance'])} row(s) to label"
            )


LABEL_FIELDS = ("relevance", "notes", "relevance_rater2")


def read_labels(path):
    """Labelled rows of an earlier sheet, by (child_id, activity_id)."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            return {
                (r["child_id"], r["activity_id"]): r
                for r in csv.DictReader(f)
                if (r.get("relevance") or "").strip()
            }
    except OSError as exc:
        raise CommandError(f"Cannot read {path}: {exc}") from exc


def carry(row, earlier):
    """Copy the earlier label into row if the activity is unchanged."""
    old = earlier.get((row["child_id"], row["activity_id"]))
    if old is None or (old["activity_name"], old["activity_description"]) != (
        row["activity_name"],
        row["activity_description"],
    ):
        return False
    for field in LABEL_FIELDS:
        row[field] = (old.get(field) or "").strip()
    return True
