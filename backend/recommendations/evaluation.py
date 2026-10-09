"""Evaluate rankings against hand-labelled relevance judgments (#36).

The objective is never the similarity or the final score (alpha = 0 would
trivially win): rankings are compared with a caregiver-expert's labels of how
relevant each activity is for each sample child.

Labels are graded: 0 = not relevant, 1 = partly relevant, 2 = highly relevant.
- precision@k: share of the top k with relevance >= 1. Unlabelled items count
  as not relevant, and how many there were is reported.
- nDCG@k: discounted cumulative gain with gain 2^rel - 1 (so a 2 is worth
  three times a 1) and discount log2(rank + 1), divided by the best possible
  DCG@k from that sample's labels. Samples with no relevant labels have no
  nDCG and are left out of its average.
"""

import csv
import math
from dataclasses import dataclass

from .heldout import HELDOUT_BY_ID
from .samples import SAMPLES_BY_KEY

RELEVANCE_VALUES = {0, 1, 2}
RELEVANT_AT = 1
LABEL_COLUMNS = ("sample_key", "activity_id", "relevance")
HELDOUT_COLUMNS = ("child_id", "split", "activity_id", "relevance", "relevance_rater2")


class LabelError(Exception):
    """The labels file can't be used; .problems lists every issue found."""

    def __init__(self, problems):
        self.problems = problems
        super().__init__(f"{len(problems)} problem(s) in the labels file")


def load_labels(path):
    """Read labels as {sample_key: {activity_id: relevance}}.

    Rows with an empty relevance are unlabelled and skipped. Every problem in
    the file is collected before raising LabelError.
    """
    labels, problems, seen = {}, [], {}
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            missing = [c for c in LABEL_COLUMNS if c not in (reader.fieldnames or [])]
            if missing:
                raise LabelError([f"missing column(s): {', '.join(missing)}"])
            for row in reader:
                line = reader.line_num
                sample_key = (row.get("sample_key") or "").strip()
                activity_id = (row.get("activity_id") or "").strip()
                raw = (row.get("relevance") or "").strip()
                if sample_key not in SAMPLES_BY_KEY:
                    problems.append(f"line {line}: unknown sample_key '{sample_key}'")
                    continue
                if not activity_id:
                    problems.append(f"line {line}: missing activity_id")
                    continue
                pair = (sample_key, activity_id)
                if pair in seen:
                    problems.append(
                        f"line {line}: duplicate label for {sample_key} / "
                        f"{activity_id} (first on line {seen[pair]})"
                    )
                    continue
                seen[pair] = line
                if raw == "":
                    continue  # not labelled yet
                if raw not in {str(v) for v in RELEVANCE_VALUES}:
                    problems.append(
                        f"line {line}: relevance '{raw}' must be 0, 1 or 2 (or empty)"
                    )
                    continue
                labels.setdefault(sample_key, {})[activity_id] = int(raw)
    except OSError as exc:
        raise LabelError([f"cannot read {path}: {exc}"]) from exc
    if problems:
        raise LabelError(problems)
    return labels


def precision_at_k(ranked_ids, relevance, k, threshold=RELEVANT_AT):
    """Share of the top k whose relevance is at least `threshold`."""
    top = ranked_ids[:k]
    hits = sum(1 for a in top if relevance.get(a, 0) >= threshold)
    return hits / k


def _dcg(gains):
    return sum((2**rel - 1) / math.log2(i + 2) for i, rel in enumerate(gains))


def ndcg_at_k(ranked_ids, relevance, k):
    """nDCG@k, or None when the sample has no relevant labels."""
    ideal = _dcg(sorted(relevance.values(), reverse=True)[:k])
    if ideal == 0:
        return None
    return _dcg([relevance.get(a, 0) for a in ranked_ids[:k]]) / ideal


@dataclass(frozen=True)
class SampleScore:
    sample_key: str
    precision: float
    ndcg: float | None
    unlabelled_in_top_k: int


@dataclass(frozen=True)
class EvaluationResult:
    k: int
    samples: list
    mean_precision: float
    mean_ndcg: float | None
    unlabelled_in_top_k: int
    unlabelled_samples: list  # samples ranked but with no labels at all


def evaluate(rankings, labels, k=5):
    """Score rankings ({sample_key: [activity_id, ...]}) against labels."""
    if k < 1:
        raise ValueError("k must be at least 1")
    scores, unlabelled_samples = [], []
    for sample_key, ranked_ids in rankings.items():
        relevance = labels.get(sample_key, {})
        if not relevance:
            unlabelled_samples.append(sample_key)
        scores.append(
            SampleScore(
                sample_key=sample_key,
                precision=precision_at_k(ranked_ids, relevance, k),
                ndcg=ndcg_at_k(ranked_ids, relevance, k),
                unlabelled_in_top_k=sum(
                    1 for a in ranked_ids[:k] if a not in relevance
                ),
            )
        )
    ndcgs = [s.ndcg for s in scores if s.ndcg is not None]
    return EvaluationResult(
        k=k,
        samples=scores,
        mean_precision=(
            sum(s.precision for s in scores) / len(scores) if scores else 0.0
        ),
        mean_ndcg=sum(ndcgs) / len(ndcgs) if ndcgs else None,
        unlabelled_in_top_k=sum(s.unlabelled_in_top_k for s in scores),
        unlabelled_samples=unlabelled_samples,
    )


def select_alpha(curve, tolerance=0.02):
    """Choose alpha from {alpha: mean nDCG@5 on tune} (#37 selection rule).

    Every alpha within `tolerance` of the best mean qualifies. The chosen
    alpha is the qualifying one closest to the middle of the qualifying range
    (min to max); on a tie, the lower alpha. Choosing among qualifying values
    only means the result always meets the tolerance, even when the
    qualifying alphas aren't contiguous. Returns (chosen, qualifying).
    """
    scored = {a: v for a, v in curve.items() if v is not None}
    if not scored:
        return None, []
    best = max(scored.values())
    qualifying = sorted(a for a, v in scored.items() if v >= best - tolerance - 1e-12)
    middle = (qualifying[0] + qualifying[-1]) / 2
    # Rounded so float noise (0.1 + 0.2 != 0.3) can't break a genuine tie.
    chosen = min(qualifying, key=lambda a: (round(abs(a - middle), 9), a))
    return chosen, qualifying


def rater_agreement(first, second):
    """Simple agreement between two raters' labels ({key: {id: grade}}).

    Only items graded by both raters count. Returns None when there are none.
    """
    pairs = [
        (grades[a], second[k][a])
        for k, grades in first.items()
        for a in grades
        if a in second.get(k, {})
    ]
    if not pairs:
        return None
    n = len(pairs)
    return {
        "items": n,
        "exact": sum(x == y for x, y in pairs) / n,
        "relevant_at_1": sum((x >= 1) == (y >= 1) for x, y in pairs) / n,
        "relevant_at_2": sum((x >= 2) == (y >= 2) for x, y in pairs) / n,
    }


@dataclass(frozen=True)
class HeldOutLabels:
    relevance: dict  # {child_id: {activity_id: grade}}, labelled rows only
    rater2: dict  # the same for relevance_rater2
    rows: dict  # {child_id: [activity_id, ...]}, every row in the sheet

    @property
    def total_rows(self):
        return sum(len(ids) for ids in self.rows.values())

    @property
    def labelled_rows(self):
        return sum(len(grades) for grades in self.relevance.values())


def _grade(raw, column, line, problems):
    if raw == "":
        return None
    if raw not in {str(v) for v in RELEVANCE_VALUES}:
        problems.append(f"line {line}: {column} '{raw}' must be 0, 1 or 2 (or empty)")
        return None
    return int(raw)


def load_heldout_labels(path):
    """Read the held-out sheet (#37); every problem is collected first.

    Checks that each child_id is a held-out child, that its split matches the
    stored definition (the split can't be changed after labelling), that
    grades are 0, 1, 2 or empty, and that no (child, activity) repeats.
    """
    relevance, rater2, rows, problems, seen = {}, {}, {}, [], {}
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            missing = [c for c in HELDOUT_COLUMNS if c not in fields]
            if missing:
                raise LabelError([f"missing column(s): {', '.join(missing)}"])
            for row in reader:
                line = reader.line_num
                child_id = (row.get("child_id") or "").strip()
                split = (row.get("split") or "").strip()
                activity_id = (row.get("activity_id") or "").strip()
                child = HELDOUT_BY_ID.get(child_id)
                if child is None:
                    problems.append(f"line {line}: unknown child_id '{child_id}'")
                    continue
                if split != child.split:
                    problems.append(
                        f"line {line}: {child_id} has split '{split}', but its "
                        f"stored split is '{child.split}'"
                    )
                    continue
                if not activity_id:
                    problems.append(f"line {line}: missing activity_id")
                    continue
                pair = (child_id, activity_id)
                if pair in seen:
                    problems.append(
                        f"line {line}: duplicate row for {child_id} / "
                        f"{activity_id} (first on line {seen[pair]})"
                    )
                    continue
                seen[pair] = line
                rows.setdefault(child_id, []).append(activity_id)
                for column, target in (
                    ("relevance", relevance),
                    ("relevance_rater2", rater2),
                ):
                    raw = (row.get(column) or "").strip()
                    grade = _grade(raw, column, line, problems)
                    if grade is not None:
                        target.setdefault(child_id, {})[activity_id] = grade
    except OSError as exc:
        raise LabelError([f"cannot read {path}: {exc}"]) from exc
    if problems:
        raise LabelError(problems)
    return HeldOutLabels(relevance=relevance, rater2=rater2, rows=rows)


# The metrics reported on the held-out set, in report order.
METRICS = (
    ("P@3>=1", lambda ids, rel: precision_at_k(ids, rel, 3, 1)),
    ("P@5>=1", lambda ids, rel: precision_at_k(ids, rel, 5, 1)),
    ("P@3>=2", lambda ids, rel: precision_at_k(ids, rel, 3, 2)),
    ("P@5>=2", lambda ids, rel: precision_at_k(ids, rel, 5, 2)),
    ("nDCG@3", lambda ids, rel: ndcg_at_k(ids, rel, 3)),
    ("nDCG@5", lambda ids, rel: ndcg_at_k(ids, rel, 5)),
)
SELECTION_METRIC = "nDCG@5"


def score_all(ranked_ids, relevance):
    """{metric name: value} for one ranking; nDCG is None without labels."""
    return {name: fn(ranked_ids, relevance) for name, fn in METRICS}


def mean(values):
    """Mean of the values that aren't None, or None if there are none."""
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def compare(hybrid, baseline, tolerance=1e-9):
    """'improved', 'tied' or 'worse' (hybrid vs baseline); None if either is None."""
    if hybrid is None or baseline is None:
        return None
    if abs(hybrid - baseline) <= tolerance:
        return "tied"
    return "improved" if hybrid > baseline else "worse"


def unlabelled_in_top(rankings, relevance, depth):
    """{method: {child_id: count}} of top-`depth` activities with no grade.

    `rankings` is {child_id: {method: [activity_id, ...]}}; an activity counts
    as unlabelled if its row is blank or it isn't in the sheet at all.
    """
    counts = {}
    for child_id, methods in rankings.items():
        graded = relevance.get(child_id, {})
        for method, ranked_ids in methods.items():
            counts.setdefault(method, {})[child_id] = sum(
                1 for a in ranked_ids[:depth] if a not in graded
            )
    return counts
