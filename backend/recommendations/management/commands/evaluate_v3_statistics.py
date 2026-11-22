"""Paired significance tests for the v3 configuration (#268).

Usage (from backend/):
    python manage.py evaluate_v3_statistics [--labels PATH]
        [--extra-labels PATH] [--markdown]

v3 is what the app ranks with since #250: retrieval mixes SBERT and TF-IDF
at settings.RETRIEVAL_BETA (0.25) and the ranking uses settings.RANKING_ALPHA
(0.7). The plan, fixed in issue #268 before the run, compares it with two
rankings on the same children and labels:

1. SBERT only (beta = 1, similarity only): the v2 baseline.
2. The v2 system (beta = 1, alpha 0.7): v3 without TF-IDF.

Method as evaluate_statistics (#196): per-child nDCG@5 differences, a
bootstrap 95% interval (10,000 resamples of children, seed 2026) and a
two-sided Wilcoxon signed-rank test with ties dropped. The 8 test children
are the primary result; tune and tune + test are context. It is repeated on
the second rater's grades. Labels are the v2 sheet plus tfidf_extra.csv, so
every compared top 5 is graded; the command refuses to report otherwise.

It changes nothing in the app: the children are created inside a
transaction that is rolled back.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings

from recommendations import heldout
from recommendations.evaluation import (
    SELECTION_METRIC,
    LabelError,
    load_heldout_labels,
    ndcg_at_k,
)
from recommendations.statistics import BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, paired

from .alpha_sensitivity import DEFAULT_EXTRA
from .evaluate_alpha_grid import DEFAULT_LABELS
from .evaluate_statistics import fmt_p

USERNAME = "v3-statistics@nurtura.invalid"
K = 5
SBERT_ONLY = "SBERT only (beta 1, similarity only)"
V2_SYSTEM = "v2 system (beta 1, alpha {alpha:g})"
RATERS = (("Researcher", "relevance"), ("Nurse", "rater2"))


def merge_grades(sheets, attribute):
    """{child_id: {activity_id: grade}} for one rater across several sheets.

    A pair graded differently in two sheets is an error.
    """
    merged = {}
    for name, labels in sheets:
        for child_id, grades in getattr(labels, attribute).items():
            for activity_id, grade in grades.items():
                known = merged.get(child_id, {}).get(activity_id)
                if known is not None and known != grade:
                    raise CommandError(
                        f"{child_id} / {activity_id} ({attribute}) is graded "
                        f"{known} in one sheet and {grade} in {name}."
                    )
                merged.setdefault(child_id, {})[activity_id] = grade
    return merged


def ungraded(rankings, grades, methods, k=K):
    """How many top-k slots of the given methods have no grade."""
    return sum(
        1
        for child_id, by_method in rankings.items()
        for method in methods
        for activity_id in by_method[method][:k]
        if activity_id not in grades.get(child_id, {})
    )


class Command(BaseCommand):
    help = "Paired significance tests for the v3 configuration (SBERT + TF-IDF)."

    def add_arguments(self, parser):
        parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
        parser.add_argument("--extra-labels", type=Path, default=DEFAULT_EXTRA)
        parser.add_argument("--markdown", action="store_true")

    def handle(self, *args, **options):
        self.markdown = options["markdown"]
        paths = [options["labels"]]
        if options["extra_labels"] and options["extra_labels"].exists():
            paths.append(options["extra_labels"])
        sheets = []
        for path in paths:
            try:
                sheets.append((path.name, load_heldout_labels(path)))
            except LabelError as exc:
                raise CommandError(
                    f"Can't use {path}:\n  " + "\n  ".join(exc.problems)
                ) from exc
        grades = {name: merge_grades(sheets, attr) for name, attr in RATERS}

        beta = float(settings.RETRIEVAL_BETA)
        alpha = float(settings.RANKING_ALPHA)
        if beta == 1.0:
            raise CommandError(
                "RETRIEVAL_BETA is 1, so v3 and the v2 system are the same "
                "ranking; run it at the app's beta."
            )
        v3 = f"v3 (beta {beta:g}, alpha {alpha:g})"
        v2 = V2_SYSTEM.format(alpha=alpha)
        rankings = self._rankings(beta, alpha, v3, v2)
        methods = (v3, SBERT_ONLY, v2)

        missing = ungraded(rankings, grades["Researcher"], methods)
        if missing:
            raise CommandError(
                f"{missing} top-{K} activities of the compared rankings have no "
                "label; grade them first (see compare_tfidf)."
            )

        self._heading("Setting")
        self._line(
            f"v3: retrieval beta {beta:g} (settings.RETRIEVAL_BETA), alpha "
            f"{alpha:g}. Labels: " + ", ".join(p.name for p in paths) + "."
        )
        self._line(
            f"Bootstrap: {BOOTSTRAP_RESAMPLES:,} resamples of children, seed "
            f"{BOOTSTRAP_SEED}, percentile 95% interval. Wilcoxon: two-sided "
            "signed-rank test, ties (zero differences) dropped."
        )
        self._line("A check: the app's settings aren't changed by it.")

        split = {
            s: [c.child_id for c in heldout.HELDOUT_CHILDREN if c.split == s]
            for s in heldout.SPLITS
        }
        groups = (
            ("Test (primary)", split["test"]),
            ("Tune", split["tune"]),
            ("Tune + test", split["tune"] + split["test"]),
        )
        for rater, _ in RATERS:
            rater_grades = grades[rater]
            self._heading(f"Paired {SELECTION_METRIC}, {rater.lower()}'s grades")
            gaps = ungraded(rankings, rater_grades, methods)
            if gaps:
                self._line(
                    f"{gaps} top-{K} activities of the compared rankings have no "
                    f"grade from the {rater.lower()}, so these results aren't "
                    "reported."
                )
                continue

            def ndcg(child_id, method):
                return ndcg_at_k(
                    rankings[child_id][method], rater_grades.get(child_id, {}), K
                )

            rows = []
            for other in (SBERT_ONLY, v2):
                for group, ids in groups:
                    r = paired(
                        [ndcg(c, v3) for c in ids], [ndcg(c, other) for c in ids]
                    )
                    rows.append(
                        [
                            other,
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
                    "v3",
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

    def _rankings(self, beta, alpha, v3, v2):
        """{child_id: {method: [activity_id, ...]}} for the three rankings."""
        rankings = {}
        with transaction.atomic():
            caregiver = get_user_model().objects.create_user(username=USERNAME)
            for child in heldout.HELDOUT_CHILDREN:
                profile = heldout.create_child(child, caregiver)
                _, at_beta = heldout.rankings_for(profile, alphas=(alpha,))
                with override_settings(RETRIEVAL_BETA=1.0):
                    _, sbert = heldout.rankings_for(profile, alphas=(alpha,))
                rankings[child.child_id] = {
                    v3: at_beta[alpha],
                    SBERT_ONLY: sbert[heldout.BASELINE],
                    v2: sbert[alpha],
                }
            transaction.set_rollback(True)
        return rankings

    # Output

    def _line(self, text):
        self.stdout.write(text)

    def _heading(self, text):
        self._line(f"\n## {text}\n" if self.markdown else f"\n== {text}")

    def _table(self, header, rows):
        self._line("| " + " | ".join(header) + " |")
        self._line("|" + "---|" * len(header))
        for row in rows:
            self._line("| " + " | ".join(row) + " |")
