"""Precompute SBERT embeddings for Published activities.

Usage (from backend/):
    python manage.py embed_activities [--force] [--dry-run]

Only Published activities are embedded, since only they can be recommended.
Activities whose embedded text (or the model) hasn't changed are skipped;
embeddings of activities that are no longer Published are removed.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from activities.models import DevelopmentalActivity
from recommendations import embeddings
from recommendations.models import ActivityEmbedding


class Command(BaseCommand):
    help = "Embed Published activities with SBERT for semantic retrieval."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-embed every Published activity, even if unchanged.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without encoding or saving.",
        )

    def handle(self, *args, **options):
        published = list(
            DevelopmentalActivity.objects.published().select_related("embedding")
        )
        stale = ActivityEmbedding.objects.exclude(
            activity__in=[a.pk for a in published]
        )
        removed = stale.count()

        if not published:
            self.stdout.write(
                self.style.WARNING(
                    "No Published activities to embed. Review and publish "
                    "activities in the admin first."
                )
            )

        encoder = (
            None if options["dry_run"] or not published else embeddings.get_encoder()
        )
        model_name = encoder.name if encoder else embeddings.MODEL_NAME

        to_embed, up_to_date = [], 0
        for activity in published:
            text = embeddings.activity_text(activity)
            digest = embeddings.text_hash(model_name, text)
            current = getattr(activity, "embedding", None)
            if not options["force"] and current and current.text_hash == digest:
                up_to_date += 1
            else:
                to_embed.append((activity, text, digest))

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{len(published)} Published: {len(to_embed)} would be "
                    f"embedded, {up_to_date} up to date, {removed} would be "
                    "removed (no longer Published) (dry run - nothing saved)"
                )
            )
            return

        vectors = encoder.encode([text for _, text, _ in to_embed]) if to_embed else []
        with transaction.atomic():
            for (activity, _, digest), vector in zip(to_embed, vectors):
                ActivityEmbedding.objects.update_or_create(
                    activity=activity,
                    defaults={
                        "model_name": model_name,
                        "dimensions": len(vector),
                        "text_hash": digest,
                        "vector": embeddings.to_bytes(vector),
                    },
                )
                self.stdout.write(
                    f"[EMBEDDED] {activity.activity_id} {activity.activity_name}"
                )
            stale.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(published)} Published: {len(to_embed)} embedded, "
                f"{up_to_date} up to date, {removed} removed (no longer Published)"
            )
        )
