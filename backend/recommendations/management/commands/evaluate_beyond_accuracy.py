"""Diversity, novelty, coverage and personalisation of the rankings (#199).

Usage (from backend/):
    python manage.py evaluate_beyond_accuracy [--markdown]

For the 20 held-out children (tune, test and the content-gap child), takes
the top 5 of SBERT-only and of alpha = 0, settings.RANKING_ALPHA and 1, and
reports the measures in recommendations/beyond_accuracy.py. No labels are
used, so every child counts. Personalisation is reported over all pairs of
children and over pairs in the same age band, where similar lists are
expected. The children are created in a transaction that is rolled back.
"""

from collections import defaultdict

import numpy as np
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from activities.choices import ContentStatus
from recommendations import beyond_accuracy as ba
from recommendations import embeddings, heldout, ranking
from recommendations.evaluation import mean
from recommendations.models import ActivityEmbedding
from recommendations.retrieval import retrieve

USERNAME = "beyond-accuracy@nurtura.invalid"
K = 5


def method_name(method):
    return "SBERT-only" if method == heldout.BASELINE else f"alpha {method:.1f}"


class Command(BaseCommand):
    help = "Diversity, novelty, coverage and personalisation of the top 5."

    def add_arguments(self, parser):
        parser.add_argument("--markdown", action="store_true")

    def handle(self, *args, **options):
        self.markdown = options["markdown"]
        alpha = float(settings.RANKING_ALPHA)
        methods = [heldout.BASELINE, *sorted({0.0, alpha, 1.0})]
        vectors, areas = self._catalogue()
        top, bands = self._top_lists(methods)
        children = [c.child_id for c in heldout.HELDOUT_CHILDREN]

        self._heading(f"Top {K} of {len(children)} held-out children")
        self._line(
            f"{len(vectors)} Published activities with embeddings. Higher is more "
            "varied for every column."
        )
        self._line("")
        rows = []
        for method in methods:
            lists = [top[c][method] for c in children]
            same_band = defaultdict(list)
            for c in children:
                same_band[bands[c]].append(top[c][method])
            within = [
                ba.personalisation(group)
                for group in same_band.values()
                if len(group) > 1
            ]
            rows.append(
                [
                    method_name(method),
                    _fmt(mean(ba.intra_list_diversity(ids, vectors) for ids in lists)),
                    _fmt(mean(ba.area_diversity(ids, areas) for ids in lists)),
                    f"{len({a for ids in lists for a in ids})}",
                    _fmt(ba.catalogue_coverage(lists, len(vectors))),
                    _fmt(ba.novelty(lists)),
                    _fmt(ba.personalisation(lists)),
                    _fmt(mean(within)),
                ]
            )
        self._table(
            [
                "Ranking",
                "Intra-list diversity",
                "Area diversity",
                "Distinct activities",
                "Coverage",
                "Novelty (bits)",
                "Personalisation (all pairs)",
                "Personalisation (same age band)",
            ],
            rows,
        )
        self._line("")
        self._line(
            f"Novelty ranges from 0 (every child shown the activity) to "
            f"{np.log2(len(children)):.2f} bits (one child)."
        )

    def _catalogue(self):
        encoder = embeddings.get_encoder()
        rows = ActivityEmbedding.objects.filter(
            activity__content_status=ContentStatus.PUBLISHED,
            model_name=encoder.name,
        ).select_related("activity")
        vectors = {
            r.activity.activity_id: embeddings.from_bytes(r.vector) for r in rows
        }
        areas = {r.activity.activity_id: r.activity.developmental_domain for r in rows}
        return vectors, areas

    def _top_lists(self, methods):
        """({child_id: {method: top-K ids}}, {child_id: age band})."""
        top, bands = {}, {}
        with transaction.atomic():
            caregiver = get_user_model().objects.create_user(username=USERNAME)
            for child in heldout.HELDOUT_CHILDREN:
                profile = heldout.create_child(child, caregiver)
                retrieval = retrieve(profile, limit=None)
                lists = {}
                for method in methods:
                    if method == heldout.BASELINE:
                        ids = [c.activity.activity_id for c in retrieval.candidates]
                    else:
                        ranked = ranking.rank_candidates(
                            retrieval.candidates, retrieval.evaluation, method
                        )
                        ids = [r.activity.activity_id for r in ranked]
                    lists[method] = ids[:K]
                top[child.child_id] = lists
                bracket = ranking.child_bracket(child.age_months)
                bands[child.child_id] = "prenatal" if bracket is None else bracket
            transaction.set_rollback(True)
        return top, bands

    # Output helpers

    def _line(self, text):
        self.stdout.write(text)

    def _heading(self, text):
        self._line(f"\n## {text}\n" if self.markdown else f"\n== {text}")

    def _table(self, header, rows):
        self._line("| " + " | ".join(header) + " |")
        self._line("|" + "---|" * len(header))
        for row in rows:
            self._line("| " + " | ".join(row) + " |")


def _fmt(value):
    return "n/a" if value is None else f"{value:.3f}"
