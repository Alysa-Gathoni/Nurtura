"""Choose alpha on the held-out tune set and report it on the test set (#37).

Usage (from backend/):
    python manage.py evaluate_alpha_grid [--labels PATH] [--markdown]

1. Tune: the mean of every metric over the tune children for each alpha from
   0.0 to 1.0 (step 0.1), plus the SBERT-only baseline. Alpha is chosen by
   mean nDCG@5 on tune only: every alpha within 0.02 of the best qualifies,
   and the qualifying alpha nearest the middle of that range wins (the lower
   on a tie).
2. Test: per child and on average, the hybrid at the chosen alpha against
   SBERT-only, with the differences and the count of children improved, tied
   or worse on nDCG@5. No significance claims.
3. The content-gap child, reported separately in the same way.
4. Agreement between relevance and relevance_rater2, where both are filled.

The children are created in a transaction that is rolled back. See
data/evaluation/README.md for the protocol.
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from recommendations import heldout
from recommendations.evaluation import (
    METRICS,
    SELECTION_METRIC,
    LabelError,
    compare,
    load_heldout_labels,
    mean,
    rater_agreement,
    score_all,
    select_alpha,
)

DEFAULT_LABELS = (
    Path(settings.BASE_DIR).parent / "data" / "evaluation" / "heldout_labels.csv"
)
EVALUATION_USERNAME = "alpha-grid@nurtura.invalid"
TOLERANCE = 0.02
NAMES = [name for name, _ in METRICS]


def fmt(value):
    return "n/a" if value is None else f"{value:.3f}"


def fmt_diff(value):
    return "n/a" if value is None else f"{value:+.3f}"


def method_name(method):
    return "SBERT-only" if method == heldout.BASELINE else f"alpha {method:.1f}"


class Command(BaseCommand):
    help = "Grid-search alpha on the held-out tune set and report on the test set."

    def add_arguments(self, parser):
        parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
        parser.add_argument(
            "--markdown",
            action="store_true",
            help="Output Markdown headings, e.g. for the project report.",
        )

    def handle(self, *args, **options):
        self.markdown = options["markdown"]
        try:
            labels = load_heldout_labels(options["labels"])
        except LabelError as exc:
            raise CommandError(
                "Can't use the labels file:\n  " + "\n  ".join(exc.problems)
            ) from exc

        rankings = self._rankings()
        scores = {
            child.child_id: {
                method: score_all(ids, labels.relevance.get(child.child_id, {}))
                for method, ids in rankings[child.child_id].items()
            }
            for child in heldout.HELDOUT_CHILDREN
        }
        by_split = {
            split: [c.child_id for c in heldout.HELDOUT_CHILDREN if c.split == split]
            for split in heldout.SPLITS
        }

        self._labelling_status(labels, rankings)
        chosen = self._tune(scores, by_split["tune"])
        if chosen is None:
            self._line(
                "\nNo tune child has a relevant label yet, so alpha can't be "
                "chosen. Label the sheet, then run this again."
            )
            return
        self._compare_section(
            "Test set", scores, by_split["test"], chosen, with_counts=True
        )
        self._compare_section(
            "Content-gap child (reported separately)",
            scores,
            by_split["gap"],
            chosen,
            with_counts=False,
        )
        self._agreement(labels)

    def _rankings(self):
        rankings = {}
        with transaction.atomic():
            caregiver = get_user_model().objects.create_user(
                username=EVALUATION_USERNAME
            )
            for child in heldout.HELDOUT_CHILDREN:
                profile = heldout.create_child(child, caregiver)
                _, rankings[child.child_id] = heldout.rankings_for(profile)
            transaction.set_rollback(True)
        return rankings

    # Sections

    def _labelling_status(self, labels, rankings):
        self._heading("Labelling status")
        self._line(
            f"{labels.labelled_rows} of {labels.total_rows} rows labelled "
            f"({labels.total_rows - labels.labelled_rows} blank; blank rows count "
            "as not relevant)."
        )
        missing = sorted(
            {
                (child_id, activity_id)
                for child_id, methods in rankings.items()
                for ids in methods.values()
                for activity_id in ids[: heldout.POOL_DEPTH]
                if activity_id not in labels.rows.get(child_id, [])
            }
        )
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(missing)} activities now in a reported top "
                    f"{heldout.POOL_DEPTH} are not in the sheet (the catalogue or "
                    "rankings changed since it was generated); they count as not "
                    "relevant: " + ", ".join(f"{c}/{a}" for c, a in missing)
                )
            )

    def _tune(self, scores, tune_ids):
        self._heading(f"Tune set ({len(tune_ids)} children): mean of each metric")
        methods = [heldout.BASELINE, *heldout.ALPHAS]
        curve = {}
        rows = []
        for method in methods:
            means = {
                name: mean(scores[c][method][name] for c in tune_ids) for name in NAMES
            }
            if method != heldout.BASELINE:
                curve[method] = means[SELECTION_METRIC]
            rows.append([method_name(method), *(fmt(means[n]) for n in NAMES)])
        chosen, qualifying = select_alpha(curve, TOLERANCE)
        for row, method in zip(rows, methods):
            if method == chosen:
                row[0] = f"**{row[0]} (chosen)**" if self.markdown else f"{row[0]} *"
        self._table(["Ranking", *NAMES], rows)
        if chosen is None:
            return None
        best = max(v for v in curve.values() if v is not None)
        self._line("")
        self._line(
            f"Best mean {SELECTION_METRIC} on tune: {best:.3f}. Within {TOLERANCE} "
            f"of it: alpha {', '.join(f'{a:.1f}' for a in qualifying)}. "
            f"Chosen alpha (middle of that range): {chosen:.1f}."
        )
        return chosen

    def _compare_section(self, title, scores, child_ids, chosen, with_counts):
        self._heading(f"{title}: alpha {chosen:.1f} vs SBERT-only")
        rows = []
        for child_id in child_ids:
            for method in (chosen, heldout.BASELINE):
                rows.append(
                    [
                        child_id,
                        method_name(method),
                        *(fmt(scores[child_id][method][n]) for n in NAMES),
                    ]
                )
        if len(child_ids) > 1:
            for method in (chosen, heldout.BASELINE):
                rows.append(
                    [
                        "Mean",
                        method_name(method),
                        *(
                            fmt(mean(scores[c][method][n] for c in child_ids))
                            for n in NAMES
                        ),
                    ]
                )
        self._table(["Child", "Ranking", *NAMES], rows)

        self._line("")
        self._line("Difference (hybrid minus SBERT-only):")
        self._line("")
        rows, outcomes = [], {"improved": 0, "tied": 0, "worse": 0}
        for child_id in child_ids:
            hybrid, base = scores[child_id][chosen], scores[child_id][heldout.BASELINE]
            outcome = compare(hybrid[SELECTION_METRIC], base[SELECTION_METRIC])
            if outcome:
                outcomes[outcome] += 1
            rows.append(
                [
                    child_id,
                    *(fmt_diff(_diff(hybrid[n], base[n])) for n in NAMES),
                    outcome or "n/a (no relevant labels)",
                ]
            )
        self._table(["Child", *NAMES, f"On {SELECTION_METRIC}"], rows)
        if with_counts:
            unscored = len(child_ids) - sum(outcomes.values())
            self._line("")
            self._line(
                f"On {SELECTION_METRIC}: {outcomes['improved']} improved, "
                f"{outcomes['tied']} tied, {outcomes['worse']} worse"
                + (f", {unscored} without relevant labels" if unscored else "")
                + f" (of {len(child_ids)}). With this few children, no "
                "significance claims are made."
            )

    def _agreement(self, labels):
        self._heading("Agreement between raters")
        agreement = rater_agreement(labels.relevance, labels.rater2)
        if agreement is None:
            self._line("No rows have both relevance and relevance_rater2 filled in.")
            return
        self._line(
            f"{agreement['items']} rows rated by both: exact agreement "
            f"{agreement['exact']:.0%}; agreement on relevant (>= 1) "
            f"{agreement['relevant_at_1']:.0%}; on clearly relevant (>= 2) "
            f"{agreement['relevant_at_2']:.0%}."
        )

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


def _diff(hybrid, baseline):
    if hybrid is None or baseline is None:
        return None
    return hybrid - baseline
