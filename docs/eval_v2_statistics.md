# Held-out evaluation v2: paired statistics and age-weight sensitivity

Last updated: 2026-11-16

- **What this adds:** confidence intervals and a signed-rank test for the v2 results in [eval_v2_results.md](eval_v2_results.md), a check of how much the ranking depends on the age weights, and agreement with a second, independent rater. It chooses nothing: α stays at 0.7.
- **Same data:** the v2 labels and the state tagged `sprint9-eval-v2`. The provenance check matched on the day of each run.
- **Runs:**
  - 2026-11-09, with `python manage.py evaluate_statistics --markdown` (#196);
  - 2026-11-16, the same command, after the second rater's grades were added (#218). The first two sections were unchanged.

## Summary

| Question | Answer (8 test children) |
|---|---|
| Is α = 0.7 better than SBERT alone? | Yes. +0.254 nDCG@5, 95% CI [+0.136, +0.379], 7 of 8 children better, Wilcoxon p = 0.016. |
| Is it better than α = 0 (similarity with age weighting, no rule priority)? | Not shown on test. +0.029, CI [−0.007, +0.095], 5 of 8 tied, p = 1.000. On tune, +0.059, CI [+0.011, +0.115]. |
| Is α = 1.0 better than α = 0.7? | Not shown. −0.040, CI [−0.169, +0.048], p = 1.000. α = 1.0's lead comes from its tie-break (see the v2 results). |
| Do the exact age weights matter? | No. Four alternative sets of weights give the same top 5 for every test child. Removing age weighting altogether costs about 0.32. |
| Would an independent rater agree with the labels? | Substantially. Quadratic-weighted κ 0.661, 95% CI [0.589, 0.718], over all 257 rows. The second rater (a registered nurse) was stricter. |
| Does the result hold on the second rater's labels? | Yes. α = 0.7 beats SBERT alone by +0.339 nDCG@5, CI [+0.156, +0.532], 7 of 8 children better, p = 0.016. |

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

## Agreement between raters (#218)

**The second rater** is a registered nurse with no part in building Nurtura, identified here by role only, with their agreement.

- **What they graded:** all 257 rows of `heldout_labels_v2.csv`, on 2026-11-16, in the labelling page's second-rater mode. Their grades are in `relevance_rater2`.
- **Blind:** the page hides the first rater's grades and notes, and the sheet shows no scores, ranks or areas. They were given the scale and the labelling rules in [data/evaluation/README.md](../data/evaluation/README.md), and nothing about how the system ranks.
- **Planned and actual:** a stratified subset of 45 rows was planned; the rater graded the whole sheet instead, which removes any sampling question.

**Method:**
- Cohen's kappa, unweighted and weighted. The scale is ordered, so the **quadratic-weighted κ is the main figure**: a 0–2 disagreement counts four times a 0–1.
- 95% interval: 10,000 bootstrap resamples of **children** (a child's rows stay together, because they aren't independent), seed 2026, percentiles.
- The κ code is checked against scikit-learn's `cohen_kappa_score` in the tests.

| Measure | Value | 95% CI |
|---|---|---|
| **Cohen's κ, quadratic-weighted** | **0.661** | [0.589, 0.718] |
| Cohen's κ, linear-weighted | 0.533 | [0.443, 0.612] |
| Cohen's κ, unweighted | 0.416 | [0.297, 0.523] |
| Exact agreement | 0.623 | – |
| Agree on relevant (grade ≥ 1) | 0.837 | – |
| Agree on clearly relevant (grade 2) | 0.778 | – |

Rows: first rater (the researcher). Columns: second rater (the nurse).

| | Nurse 0 | Nurse 1 | Nurse 2 | Total |
|---|---|---|---|---|
| **Researcher 0** | 27 | 1 | 0 | 28 |
| **Researcher 1** | 39 | 48 | 6 | 93 |
| **Researcher 2** | 2 | 49 | 85 | 136 |
| **Total** | 68 | 98 | 91 | 257 |

How to read it:

- **Substantial agreement** on the usual reading of κ (0.61–0.80). The interval's lower end (0.589) is just below that band, so "moderate to substantial" is the careful wording.
- **The disagreement is systematic, not random.** The nurse was stricter: 88 rows are one grade lower, against 7 one grade higher. Only 2 rows differ by two grades.
- **Where the researcher said "not relevant", the nurse agreed** in 27 of 28 rows. Most disagreement is about how relevant an activity is, not whether it is.
- **Unweighted κ is lower** (0.416) because it counts every one-grade step as a full disagreement.

### nDCG@5 on each rater's labels

The same rankings, scored with each rater's grades:

| Ranking | Researcher, tune | Researcher, test | Nurse, tune | Nurse, test |
|---|---|---|---|---|
| SBERT-only | 0.548 | 0.582 | 0.427 | 0.398 |
| α = 0.0 | 0.677 | 0.807 | 0.640 | 0.689 |
| **α = 0.7** | 0.736 | **0.836** | 0.718 | **0.737** |
| α = 1.0 | 0.829 | 0.876 | 0.767 | 0.834 |

On the nurse's labels, test set: α = 0.7 scores 0.737 against 0.398 for SBERT alone, a difference of **+0.339**, 95% CI [+0.156, +0.532], 7 of 8 children better, 0 tied, 1 worse, Wilcoxon p = 0.016.

- **The main finding holds** for an independent rater, and the gain over SBERT alone is larger than on the researcher's labels (+0.339 against +0.254).
- **The order of the rankings is the same** for both raters: SBERT-only < α = 0 < α = 0.7 < α = 1.0. α = 1.0's lead is the activity-ID tie-break explained in [eval_v2_results.md](eval_v2_results.md#why-α--10-tops-the-tune-curve), not better ranking.
- **Scores are lower on the nurse's labels** because they gave fewer grade 2s, so each ranking finds fewer clearly relevant activities to put first.
- α was not re-chosen. With the nurse's labels, the rule fixed in advance would also pick α = 1.0 on tune (0.767), for the same tie-break reason.

## Limitations

- **Small samples:**
  - 8 test children (constructed profiles); two raters, the first of whom designed the system;
  - a bootstrap over 8 children tends to give intervals that are too narrow;
  - Wilcoxon p-values with few non-zero differences are coarse (with 3, the smallest possible is 0.25).
- **Pooling:** only the pooled top 5 of the evaluated rankings were labelled. Comparisons between those rankings are fair, but a new ranking (like "no age weighting") can surface unlabelled activities.
- **Several comparisons:** nine tests in the paired table and five scenarios. Only the test-set comparison with SBERT-only is treated as a finding; the rest are context.
- **Same labels as the α decision:** this adds uncertainty to the v2 result. It isn't an independent replication. The second rater's grades are independent judgements of the same rows, not a new set of children.
- **One second rater:** agreement with one nurse shows the labels aren't one person's view; it doesn't show what clinicians in general would say.

## Reproducing

From `backend/`, at `sprint9-eval-v2` or later with the provenance check passing:

```
python manage.py evaluate_alpha_grid --check-provenance
python manage.py evaluate_statistics --markdown
```

The command refuses to run if any top-5 activity of the compared rankings has no label. The agreement sections appear only when `relevance_rater2` is filled in. The code is `recommendations/statistics.py` and `recommendations/management/commands/evaluate_statistics.py`.
