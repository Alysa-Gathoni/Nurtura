# Held-out evaluation v2: paired statistics and age-weight sensitivity

Last updated: 2026-11-09

- **What this adds:** confidence intervals and a signed-rank test for the v2 results in [eval_v2_results.md](eval_v2_results.md), and a check of how much the ranking depends on the age weights. It chooses nothing: α stays at 0.7.
- **Same data:** the v2 labels and the state tagged `sprint9-eval-v2`. The provenance check matched on the day of the run.
- **Run:** 2026-11-09, with `python manage.py evaluate_statistics --markdown` (#196).

## Summary

| Question | Answer (8 test children) |
|---|---|
| Is α = 0.7 better than SBERT alone? | Yes. +0.254 nDCG@5, 95% CI [+0.136, +0.379], 7 of 8 children better, Wilcoxon p = 0.016. |
| Is it better than α = 0 (similarity with age weighting, no rule priority)? | Not shown on test. +0.029, CI [−0.007, +0.095], 5 of 8 tied, p = 1.000. On tune, +0.059, CI [+0.011, +0.115]. |
| Is α = 1.0 better than α = 0.7? | Not shown. −0.040, CI [−0.169, +0.048], p = 1.000. α = 1.0's lead comes from its tie-break (see the v2 results). |
| Do the exact age weights matter? | No. Four alternative sets of weights give the same top 5 for every test child. Removing age weighting altogether costs about 0.32. |

Most of the gain over SBERT alone comes from the age weight. Rule priority adds a little on top, more clearly on tune than on test.

## Method

- **Paired comparison:** for each child, the nDCG@5 of α = 0.7 minus the nDCG@5 of the other ranking.
- **Bootstrap interval:**
  - resamples the children with replacement, 10,000 times, with seed 2026;
  - the 95% interval is the 2.5th to 97.5th percentile of the resampled mean differences.
- **Wilcoxon signed-rank test:**
  - two-sided, on the same differences;
  - zero differences (ties) are dropped, so "non-zero" can be less than n;
  - with this few non-zero differences, SciPy uses the exact distribution.
- **Primary result:** the 8 test children.
  - Tune (11) and tune + test (19) are shown for context only.
  - α = 0.7 was not chosen on these labels, but the tune curve was looked at before the decision.
- **Age-weight scenarios:**
  - fixed in the code before the first run;
  - each re-ranks every child at α = 0.7 with different weights by bracket distance (same / one younger / one older / two away / further);
  - top-5 activities that were never labelled count as not relevant.

## Paired nDCG@5: α = 0.7 against each ranking

| Against | Children | n | α = 0.7 | Other | Difference | 95% CI | Better / tied / worse | Non-zero | W | p |
|---|---|---|---|---|---|---|---|---|---|---|
| SBERT-only | **Test** | 8 | 0.836 | 0.582 | **+0.254** | [+0.136, +0.379] | 7 / 0 / 1 | 8 | 1 | **0.016** |
| SBERT-only | Tune | 11 | 0.736 | 0.548 | +0.188 | [+0.068, +0.309] | 8 / 1 / 2 | 10 | 5 | 0.020 |
| SBERT-only | Tune + test | 19 | 0.778 | 0.562 | +0.216 | [+0.127, +0.306] | 15 / 1 / 3 | 18 | 9 | < 0.001 |
| α = 0.0 | **Test** | 8 | 0.836 | 0.807 | +0.029 | [−0.007, +0.095] | 1 / 5 / 2 | 3 | 3 | 1.000 |
| α = 0.0 | Tune | 11 | 0.736 | 0.677 | +0.059 | [+0.011, +0.115] | 5 / 5 / 1 | 6 | 1 | 0.062 |
| α = 0.0 | Tune + test | 19 | 0.778 | 0.732 | +0.046 | [+0.010, +0.089] | 6 / 10 / 3 | 9 | 6 | 0.055 |
| α = 1.0 | **Test** | 8 | 0.836 | 0.876 | −0.040 | [−0.169, +0.048] | 3 / 3 / 2 | 5 | 7 | 1.000 |
| α = 1.0 | Tune | 11 | 0.736 | 0.829 | −0.093 | [−0.182, +0.003] | 3 / 1 / 7 | 10 | 11 | 0.105 |
| α = 1.0 | Tune + test | 19 | 0.778 | 0.849 | −0.071 | [−0.146, −0.000] | 6 / 4 / 9 | 15 | 32 | 0.121 |

How to read it:

- **Against SBERT-only:**
  - the interval is well clear of zero in every group;
  - on test, 7 of 8 children improve;
  - the test p-value (0.016) is close to the smallest possible with 8 children (0.008), and it stays below 0.05 after a Bonferroni correction for the three test comparisons (0.05 / 3 = 0.017).
- **Against α = 0:**
  - α = 0 already applies the age weight, and on test it is within 0.03 of α = 0.7;
  - five of the eight test children have the same score under both;
  - rule priority helps on tune (the interval excludes zero there), but the test set doesn't confirm it.
- **Against α = 1.0:**
  - α = 1.0 scores higher, but the difference isn't significant;
  - α = 1.0 ranks by rule priority alone, so many activities tie and it breaks ties by activity ID;
  - its lead isn't evidence of better ranking (see [eval_v2_results.md](eval_v2_results.md#why-α--10-tops-the-tune-curve)).

## Age-weight sensitivity at α = 0.7

| Scenario | Weights | Tune | Test | Test vs current | 95% CI | Test top 5 changed | Test top-5 slots outside the child's bracket | Unlabelled top 5 (all 20 children) |
|---|---|---|---|---|---|---|---|---|
| **Current** (agreed in Sprint 5) | 1 / 0.7 / 0.5 / 0.25 / 0.1 | 0.736 | 0.836 | – | – | 0 of 8 | 0 of 40 | 0 |
| No age weighting | 1 / 1 / 1 / 1 / 1 | 0.555 | 0.520 | −0.316 | [−0.425, −0.200] | 7 of 8 | 29 of 40 | 12 |
| Weaker (square root) | 1 / 0.837 / 0.707 / 0.5 / 0.316 | 0.736 | 0.836 | 0.000 | [0.000, 0.000] | 0 of 8 | 0 of 40 | 0 |
| Stronger (squared) | 1 / 0.49 / 0.25 / 0.0625 / 0.01 | 0.736 | 0.836 | 0.000 | [0.000, 0.000] | 0 of 8 | 0 of 40 | 0 |
| Symmetric (0.7 either side) | 1 / 0.7 / 0.7 / 0.25 / 0.1 | 0.736 | 0.836 | 0.000 | [0.000, 0.000] | 0 of 8 | 0 of 40 | 0 |
| Reversed (older favoured) | 1 / 0.5 / 0.7 / 0.25 / 0.1 | 0.736 | 0.836 | 0.000 | [0.000, 0.000] | 0 of 8 | 0 of 40 | 0 |

How to read it:

- **The exact values don't matter.**
  - With 449 activities, every child has enough well-matched activities in their own bracket to fill the top 5.
  - Any penalty for another bracket keeps those in front, so softer, harsher, symmetric and reversed weights all give the same top 5.
  - The asymmetry (younger 0.7, older 0.5) only affects positions below 5, which weren't labelled.
- **Having an age weight matters a lot.**
  - Without it, 29 of the 40 test top-5 slots go to activities from another bracket, and test nDCG@5 drops from 0.836 to 0.520.
  - 12 of those activities were never labelled and count as not relevant, so −0.316 overstates the loss somewhat. The direction is clear either way.
- **What this means for the design:**
  - the age weights are a design choice, not a tuned parameter;
  - the results don't depend on their exact values;
  - a reviewer could question 0.7 and 0.5 specifically, and this shows those numbers don't drive the result.

## Limitations

- **Small samples:**
  - 8 test children (constructed profiles) and one rater;
  - a bootstrap over 8 children tends to give intervals that are too narrow;
  - Wilcoxon p-values with few non-zero differences are coarse (with 3, the smallest possible is 0.25).
- **Pooling:** only the pooled top 5 of the evaluated rankings were labelled. Comparisons between those rankings are fair, but a new ranking (like "no age weighting") can surface unlabelled activities.
- **Several comparisons:** nine tests in the paired table and five scenarios. Only the test-set comparison with SBERT-only is treated as a finding; the rest are context.
- **Same labels as the α decision:** this adds uncertainty to the v2 result. It isn't an independent replication.

## Reproducing

From `backend/`, at `sprint9-eval-v2` or later with the provenance check passing:

```
python manage.py evaluate_alpha_grid --check-provenance
python manage.py evaluate_statistics --markdown
```

The command refuses to run if any top-5 activity of the compared rankings has no label. The code is `recommendations/statistics.py` and `recommendations/management/commands/evaluate_statistics.py`.
