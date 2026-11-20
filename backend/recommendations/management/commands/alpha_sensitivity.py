"""How sensitive the ranking is to alpha at the app's retrieval (#260).

Usage (from backend/):
    python manage.py alpha_sensitivity [--labels PATH] [--extra-labels PATH]
        [--markdown]

Alpha (0.7) was chosen on the v2 held-out labels with SBERT-only retrieval.
Since #250, retrieval mixes in TF-IDF (settings.RETRIEVAL_BETA = 0.25), which
changes the similarity scores. This scores every alpha in heldout.ALPHAS at
the current beta, on the tune and test children, using every graded pair:
the v2 sheet plus the extra TF-IDF pairs (tfidf_extra.csv).

It is a sensitivity check, not a retune. It reports what the v2 alpha rule
(evaluation.select_alpha: every alpha within TOLERANCE of the best tune mean
qualifies, and the middle of that range wins) would choose, and whether 0.7
is within TOLERANCE of the best. The app's alpha isn't changed.

Activities in a top 5 that nobody graded count as not relevant; they are
counted per alpha so the gaps are visible. The held-out children are created
inside a transaction that is rolled back, so nothing is stored.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from recommendations import heldout
from recommendations.evaluation import SELECTION_METRIC, mean, score_all, select_alpha

from .compare_tfidf import load_merged_labels
from .evaluate_alpha_grid import DEFAULT_LABELS, TOLERANCE

DEFAULT_EXTRA = DEFAULT_LABELS.with_name("tfidf_extra.csv")
USERNAME = "alpha-sensitivity@nurtura.invalid"
SPLITS = ("tune", "test")


def describe(curve, current, tolerance=TOLERANCE):
    """What the curve says about `current`: (chosen, qualifying, best, gap)."""
    chosen, qualifying = select_alpha(curve, tolerance)
    known = [v for v in curve.values() if v is not None]
    best = max(known) if known else None
    gap = None if best is None or curve.get(current) is None else best - curve[current]
    return chosen, qualifying, best, gap


class Command(BaseCommand):
    help = "Score every alpha at the app's retrieval beta (sensitivity check)."

    def add_arguments(self, parser):
        parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
        parser.add_argument("--extra-labels", type=Path, default=DEFAULT_EXTRA)
        parser.add_argument("--markdown", action="store_true")

    def handle(self, *args, **options):
        self.markdown = options["markdown"]
        paths = [options["labels"]]
        if options["extra_labels"] and options["extra_labels"].exists():
            paths.append(options["extra_labels"])
        relevance, _ = load_merged_labels(paths)
        beta = float(settings.RETRIEVAL_BETA)
        current = float(settings.RANKING_ALPHA)
        rankings = self._rankings()
        by_split = {
            split: [c.child_id for c in heldout.HELDOUT_CHILDREN if c.split == split]
            for split in SPLITS
        }

        self._heading("Setting")
        self._line(
            f"Retrieval beta {beta:g} (settings.RETRIEVAL_BETA); app alpha "
            f"{current:g}. Labels: " + ", ".join(p.name for p in paths) + "."
        )
        self._line("A sensitivity check: the app's alpha isn't changed by it.")

        methods = [heldout.BASELINE, *heldout.ALPHAS]
        means, missing = {}, {}
        for split in SPLITS:
            for method in methods:
                scores, gaps = [], 0
                for child_id in by_split[split]:
                    grades = relevance.get(child_id, {})
                    ranked = rankings[child_id][method]
                    scores.append(score_all(ranked, grades)[SELECTION_METRIC])
                    gaps += sum(
                        1 for a in ranked[: heldout.POOL_DEPTH] if a not in grades
                    )
                means[(split, method)] = mean(scores)
                missing[(split, method)] = gaps

        self._heading(f"Mean {SELECTION_METRIC} by alpha")
        rows = []
        for method in methods:
            name = "similarity-only" if method == heldout.BASELINE else f"{method:.1f}"
            if method == current:
                name = f"**{name} (app)**" if self.markdown else f"{name} (app)"
            rows.append(
                [
                    name,
                    *(self._fmt(means[(s, method)]) for s in SPLITS),
                    *(str(missing[(s, method)]) for s in SPLITS),
                ]
            )
        self._table(
            ["Alpha", "Tune", "Test", "Ungraded (tune)", "Ungraded (test)"], rows
        )

        curve = {a: means[("tune", a)] for a in heldout.ALPHAS}
        chosen, qualifying, best, gap = describe(curve, current)
        self._heading("What the v2 alpha rule would say")
        if chosen is None:
            self._line("No graded tune pairs, so no reading.")
            return
        self._line(
            f"Best tune mean: {best:.3f}. Within {TOLERANCE} of it: alpha "
            + ", ".join(f"{a:.1f}" for a in qualifying)
            + f". The rule's choice: {chosen:.1f}."
        )
        verdict = (
            f"alpha {current:g} is within {TOLERANCE} of the best "
            f"({gap:+.3f} below it), so the check supports keeping it."
            if gap is not None and gap <= TOLERANCE + 1e-9
            else f"alpha {current:g} is {gap:.3f} below the best, more than "
            f"{TOLERANCE}: record it as a limitation."
        )
        self._line(verdict)
        ungraded = sum(missing[(s, m)] for s in SPLITS for m in heldout.ALPHAS)
        if ungraded:
            self._line(
                f"{ungraded} ungraded top-{heldout.POOL_DEPTH} slots across the "
                "alphas count as not relevant (see the table)."
            )

    def _rankings(self):
        """{child_id: {method: [activity_id, ...]}} at the current settings."""
        rankings = {}
        with transaction.atomic():
            caregiver = get_user_model().objects.create_user(username=USERNAME)
            for child in heldout.HELDOUT_CHILDREN:
                if child.split not in SPLITS:
                    continue
                profile = heldout.create_child(child, caregiver)
                _, rankings[child.child_id] = heldout.rankings_for(profile)
            transaction.set_rollback(True)
        return rankings

    # Output

    def _fmt(self, value):
        return "n/a" if value is None else f"{value:.3f}"

    def _heading(self, text):
        self.stdout.write(("\n## " if self.markdown else "\n== ") + text)

    def _line(self, text):
        self.stdout.write(text)

    def _table(self, header, rows):
        if self.markdown:
            self.stdout.write("| " + " | ".join(header) + " |")
            self.stdout.write("|" + "---|" * len(header))
            for row in rows:
                self.stdout.write("| " + " | ".join(row) + " |")
        else:
            widths = [
                max(len(str(r[i])) for r in [header, *rows]) for i in range(len(header))
            ]
            for row in [header, *rows]:
                self.stdout.write(
                    "  ".join(str(c).ljust(w) for c, w in zip(row, widths))
                )
