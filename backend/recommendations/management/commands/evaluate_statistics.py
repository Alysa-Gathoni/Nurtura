"""Paired statistics and age-weight sensitivity for held-out v2 (#196).

Usage (from backend/):
    python manage.py evaluate_statistics [--labels PATH] [--markdown]

Adds to evaluate_alpha_grid, on the same labels and rankings; it chooses
nothing:

1. Paired comparisons of per-child nDCG@5, alpha = settings.RANKING_ALPHA
   against SBERT-only, alpha = 0 and alpha = 1: mean difference, bootstrap
   95% interval (10,000 resamples of children, seed 2026) and a two-sided
   Wilcoxon signed-rank test. The test children are the primary result;
   tune and tune + test are shown for context (alpha was not chosen with
   them, but the tune curve was looked at).
2. Age-weight sensitivity: the hybrid at the same alpha with the age
   weights replaced by alternatives fixed before the first run. Mean
   nDCG@5 per split, plus the top-5 activities with no label, which count
   as not relevant (so a scenario with many is scored pessimistically).

The children are created in a transaction that is rolled back.
"""

from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recommendations import heldout, ranking
from recommendations.evaluation import (
    SELECTION_METRIC,
    LabelError,
    load_heldout_labels,
    mean,
    ndcg_at_k,
)
from recommendations.retrieval import retrieve
from recommendations.statistics import BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, paired

from .evaluate_alpha_grid import DEFAULT_LABELS

USERNAME = "statistics@nurtura.invalid"
K = 5

# Age weights by bracket distance: (same, one younger, one older, two away,
# further). Fixed before the first run (#196).
AGE_SCENARIOS = (
    ("Current (agreed in Sprint 5)", (1.0, 0.7, 0.5, 0.25, 0.1)),
    ("No age weighting", (1.0, 1.0, 1.0, 1.0, 1.0)),
    ("Weaker (square root)", (1.0, 0.837, 0.707, 0.5, 0.316)),
    ("Stronger (squared)", (1.0, 0.49, 0.25, 0.0625, 0.01)),
    ("Symmetric (0.7 either side)", (1.0, 0.7, 0.7, 0.25, 0.1)),
    ("Reversed (older favoured)", (1.0, 0.5, 0.7, 0.25, 0.1)),
)
WEIGHT_NAMES = ("SAME_BRACKET", "ONE_YOUNGER", "ONE_OLDER", "TWO_AWAY", "FURTHER")


def age_weights(weights):
    """Context manager replacing the ranking module's age weights."""
    stack = ExitStack()
    for name, value in zip(WEIGHT_NAMES, weights):
        stack.enter_context(mock.patch.object(ranking, name, value))
    return stack


def fmt_p(p):
    if p is None:
        return "n/a"
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def method_name(method):
    return "SBERT-only" if method == heldout.BASELINE else f"alpha {method:.1f}"


class Command(BaseCommand):
    help = "Paired statistics and age-weight sensitivity on the held-out set."

    def add_arguments(self, parser):
        parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
        parser.add_argument("--markdown", action="store_true")

    def handle(self, *args, **options):
        self.markdown = options["markdown"]
        try:
            labels = load_heldout_labels(options["labels"])
        except LabelError as exc:
            raise CommandError(
                "Can't use the labels file:\n  " + "\n  ".join(exc.problems)
            ) from exc
        alpha = float(settings.RANKING_ALPHA)
        rankings = self._rankings(alpha)
        split = {
            s: [c.child_id for c in heldout.HELDOUT_CHILDREN if c.split == s]
            for s in heldout.SPLITS
        }

        def ndcg(child_id, ids):
            return ndcg_at_k(ids, labels.relevance.get(child_id, {}), K)

        # Withhold everything if the reported rankings have unlabelled top 5s.
        base = [heldout.BASELINE, 0.0, alpha, 1.0]
        unlabelled = sum(
            1
            for child_id, methods in rankings.items()
            for method in base
            for a in methods[method][:K]
            if a not in labels.relevance.get(child_id, {})
        )
        if unlabelled:
            raise CommandError(
                f"{unlabelled} top-{K} activities of the compared rankings have "
                "no label; label them first (see evaluate_alpha_grid)."
            )

        self._paired_section(alpha, rankings, split, ndcg)
        self._sensitivity_section(alpha, rankings, split, ndcg, labels)

    def _rankings(self, alpha):
        """{child_id: {method or scenario name: [activity_id, ...]}}."""
        rankings = {}
        self.age_ranges = {}
        with transaction.atomic():
            caregiver = get_user_model().objects.create_user(username=USERNAME)
            for child in heldout.HELDOUT_CHILDREN:
                profile = heldout.create_child(child, caregiver)
                retrieval = retrieve(profile, limit=None)
                for c in retrieval.candidates:
                    self.age_ranges[c.activity.activity_id] = c.activity.age_range
                methods = {
                    heldout.BASELINE: [
                        c.activity.activity_id for c in retrieval.candidates
                    ]
                }
                for a in sorted({0.0, alpha, 1.0}):
                    methods[a] = self._ranked(retrieval, a)
                for name, weights in AGE_SCENARIOS:
                    with age_weights(weights):
                        methods[name] = self._ranked(retrieval, alpha)
                rankings[child.child_id] = methods
            transaction.set_rollback(True)
        return rankings

    @staticmethod
    def _ranked(retrieval, alpha):
        ranked = ranking.rank_candidates(
            retrieval.candidates, retrieval.evaluation, alpha
        )
        return [r.activity.activity_id for r in ranked]

    # Sections

    def _paired_section(self, alpha, rankings, split, ndcg):
        groups = (
            ("Test (primary)", split["test"]),
            ("Tune", split["tune"]),
            ("Tune + test", split["tune"] + split["test"]),
        )
        self._heading(f"Paired {SELECTION_METRIC}: alpha {alpha:.1f} against each")
        self._line(
            f"Bootstrap: {BOOTSTRAP_RESAMPLES:,} resamples of children, seed "
            f"{BOOTSTRAP_SEED}, percentile 95% interval. Wilcoxon: two-sided "
            "signed-rank test, ties (zero differences) dropped."
        )
        self._line("")
        rows = []
        for other in (heldout.BASELINE, 0.0, 1.0):
            for group, ids in groups:
                r = paired(
                    [ndcg(c, rankings[c][alpha]) for c in ids],
                    [ndcg(c, rankings[c][other]) for c in ids],
                )
                rows.append(
                    [
                        method_name(other),
                        group,
                        str(r.n),
                        f"{r.mean_a:.3f}",
                        f"{r.mean_b:.3f}",
                        f"{r.mean_diff:+.3f}",
                        f"[{r.ci_low:+.3f}, {r.ci_high:+.3f}]",
                        f"{r.improved}/{r.tied}/{r.worse}",
                        str(r.wilcoxon_n),
                        "n/a" if r.wilcoxon_w is None else f"{r.wilcoxon_w:g}",
                        fmt_p(r.p_value),
                    ]
                )
        self._table(
            [
                "Against",
                "Children",
                "n",
                f"alpha {alpha:.1f}",
                "Other",
                "Difference",
                "95% CI",
                "Better/tied/worse",
                "Non-zero",
                "W",
                "p",
            ],
            rows,
        )

    def _sensitivity_section(self, alpha, rankings, split, ndcg, labels):
        self._heading(f"Age-weight sensitivity at alpha {alpha:.1f}")
        self._line(
            "Weights by bracket distance: same / one younger / one older / two "
            "away / further. Unlabelled top-5 activities count as not relevant."
        )
        self._line("")
        rows = []
        current = AGE_SCENARIOS[0][0]
        for name, weights in AGE_SCENARIOS:
            means = {
                s: mean(ndcg(c, rankings[c][name]) for c in split[s])
                for s in ("tune", "test")
            }
            test_ids = split["test"]
            r = paired(
                [ndcg(c, rankings[c][name]) for c in test_ids],
                [ndcg(c, rankings[c][current]) for c in test_ids],
            )
            missing = sum(
                1
                for c, methods in rankings.items()
                for a in methods[name][:K]
                if a not in labels.relevance.get(c, {})
            )
            changed = sum(
                1 for c in test_ids if rankings[c][name][:K] != rankings[c][current][:K]
            )
            outside = sum(
                1
                for c in test_ids
                for a in rankings[c][name][:K]
                if self._outside_bracket(c, a)
            )
            rows.append(
                [
                    name,
                    " / ".join(f"{w:g}" for w in weights),
                    f"{means['tune']:.3f}",
                    f"{means['test']:.3f}",
                    "-" if name == current else f"{r.mean_diff:+.3f}",
                    (
                        "-"
                        if name == current
                        else f"[{r.ci_low:+.3f}, {r.ci_high:+.3f}]"
                    ),
                    f"{changed}/{len(test_ids)}",
                    f"{outside}/{K * len(test_ids)}",
                    str(missing),
                ]
            )
        self._table(
            [
                "Scenario",
                "Weights",
                "Tune",
                "Test",
                "Test vs current",
                "95% CI",
                "Test top 5 changed",
                "Test top-5 slots outside the child's bracket",
                "Unlabelled top 5 (all)",
            ],
            rows,
        )

    def _outside_bracket(self, child_id, activity_id):
        """True if the activity is from another bracket than the child's.

        Prenatal children and prenatal activities have no distance, so they
        never count (the ranking gives them the same-bracket weight).
        """
        child = heldout.HELDOUT_BY_ID[child_id]
        age_range = self.age_ranges[activity_id]
        bracket = ranking.child_bracket(child.age_months)
        if bracket is None or age_range not in ranking.BRACKET_INDEX:
            return False
        return ranking.BRACKET_INDEX[age_range] != bracket

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
