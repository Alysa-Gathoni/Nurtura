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

from .samples import SAMPLES_BY_KEY

RELEVANCE_VALUES = {0, 1, 2}
RELEVANT_AT = 1
LABEL_COLUMNS = ("sample_key", "activity_id", "relevance")


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


def precision_at_k(ranked_ids, relevance, k):
    top = ranked_ids[:k]
    hits = sum(1 for a in top if relevance.get(a, 0) >= RELEVANT_AT)
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
