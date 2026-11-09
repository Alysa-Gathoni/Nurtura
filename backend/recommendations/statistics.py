"""Paired statistics for the held-out evaluation (#196).

Small samples (8 test children), so both are reported together and read
with caution:

- a percentile bootstrap 95% confidence interval for the mean paired
  difference, resampling children with replacement (fixed seed);
- a two-sided Wilcoxon signed-rank test on the paired differences. Zero
  differences (ties) are dropped, as in Wilcoxon's original method, so the
  effective sample size can be smaller than the number of children.
"""

from dataclasses import dataclass

import numpy as np
from scipy import stats

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 2026
CONFIDENCE = 0.95
TIE_TOLERANCE = 1e-9


@dataclass(frozen=True)
class PairedResult:
    n: int  # children with both scores
    mean_a: float
    mean_b: float
    mean_diff: float  # a minus b
    ci_low: float
    ci_high: float
    improved: int
    tied: int
    worse: int
    wilcoxon_n: int  # non-zero differences
    wilcoxon_w: float | None
    p_value: float | None  # None when every difference is zero


def paired_differences(a, b):
    """[a_i - b_i] for the pairs where neither score is None."""
    return [x - y for x, y in zip(a, b) if x is not None and y is not None]


def bootstrap_ci(
    diffs, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED, confidence=CONFIDENCE
):
    """Percentile bootstrap interval for the mean of diffs."""
    values = np.asarray(diffs, dtype=float)
    if values.size == 0:
        raise ValueError("No paired differences to resample.")
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, values.size, size=(resamples, values.size))
    means = values[picks].mean(axis=1)
    tail = (1 - confidence) / 2 * 100
    low, high = np.percentile(means, [tail, 100 - tail])
    return float(low), float(high)


def wilcoxon(diffs):
    """(non-zero n, W, two-sided p); W and p are None if all diffs are zero."""
    nonzero = [d for d in diffs if abs(d) > TIE_TOLERANCE]
    if not nonzero:
        return 0, None, None
    result = stats.wilcoxon(nonzero, alternative="two-sided")
    return len(nonzero), float(result.statistic), float(result.pvalue)


def paired(a, b, **bootstrap_options):
    """Compare two methods' per-child scores (same child order in a and b)."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    diffs = [x - y for x, y in pairs]
    low, high = bootstrap_ci(diffs, **bootstrap_options)
    n_nonzero, w, p = wilcoxon(diffs)
    return PairedResult(
        n=len(pairs),
        mean_a=float(np.mean([x for x, _ in pairs])),
        mean_b=float(np.mean([y for _, y in pairs])),
        mean_diff=float(np.mean(diffs)),
        ci_low=low,
        ci_high=high,
        improved=sum(d > TIE_TOLERANCE for d in diffs),
        tied=sum(abs(d) <= TIE_TOLERANCE for d in diffs),
        worse=sum(d < -TIE_TOLERANCE for d in diffs),
        wilcoxon_n=n_nonzero,
        wilcoxon_w=w,
        p_value=p,
    )
