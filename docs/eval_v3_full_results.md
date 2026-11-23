# Full v3 evaluation: results (#270, #274)

> **Last updated: 2026-11-23.** Every figure is from `python manage.py evaluate_v3_full --markdown` (from `backend/`), run on 23 Nov 2026 at the app's configuration (β = 0.25, α = 0.7). The plan ([eval_v3_full_plan.md](eval_v3_full_plan.md)) was committed before the first run (#270). The 15 pairs left ungraded then were graded blind by both raters (#272, #274), so **every figure is now known**. The full tables, raw files and figures are in the evidence pack: [report_evidence/04_evaluation.md](report_evidence/04_evaluation.md) ("Full evaluation of the current system (v3)") and [report_evidence/09_figures.md](report_evidence/09_figures.md).

**Labels:** `heldout_labels_v2.csv` (257 pairs), `tfidf_extra.csv` (123) and `v3_extra.csv` (15): 395 pairs, each graded by the researcher and the nurse.

## Headline results (8 test children, researcher's grades)

| Measure | v3 (α = 0.7) | Hybrid retrieval only | SBERT only |
|---|---|---|---|
| nDCG@5 | **0.882** | 0.604 | 0.577 |
| nDCG@3 | **0.897** | 0.588 | 0.608 |
| P@5, grade ≥ 1 | **1.000** | 0.875 | 0.850 |
| P@5, grade 2 | **0.825** | 0.450 | 0.400 |

- **Against SBERT only:** +0.305 nDCG@5, 95% CI [+0.164, +0.455], all 8 children better, W = 0, p = 0.008.
  - On the nurse's grades: 0.780 against 0.379, +0.401, CI [+0.221, +0.555], 7 of 8 better, W = 1, p = 0.016.
- **Against hybrid retrieval only:** +0.278, CI [+0.141, +0.422], 8 of 8 better, p = 0.008.
  - On the nurse's grades: 6 of 8 better.
- **H17 (content gap), reported separately:**
  - researcher's grades: v3 0.563, against 0.774 for hybrid retrieval and 0.903 for SBERT only;
  - nurse's grades: v3 0.677, against 0.349 and 0.228.

**Why the nurse's figures differ slightly from [eval_v3_statistics.md](eval_v3_statistics.md)** (0.788 against 0.382 there): that run didn't have the 15 new pairs.
- **Three of the new pairs are H04's,** and the nurse graded two of them 2 and one 1.
- **None of them is in v3's or SBERT only's top 5,** but they raise H04's best possible score. So H04's nDCG on the nurse's grades falls under every ranking.
- **The test result is unchanged.**

## α and the selection rule

| α | 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | **0.7** | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Tune | 0.781 | 0.792 | 0.820 | 0.821 | 0.820 | 0.814 | 0.822 | **0.822** | 0.822 | 0.822 | 0.803 |
| Test | 0.881 | 0.892 | 0.892 | 0.893 | 0.893 | 0.882 | 0.882 | **0.882** | 0.882 | 0.882 | 0.852 |

Baselines: SBERT only, tune 0.535 and test 0.577; hybrid retrieval only, 0.474 and 0.604.

- **The rule** (the best tune mean, then the middle of the values within 0.02 of it) applies to every α now. It qualifies α 0.2 to 1.0 (0.0 and 0.1 are more than 0.02 below 0.822) and **chooses α = 0.6**. This is unchanged from #270.
- **The app keeps 0.7.** It scores the same as 0.6 on tune (0.822) and test (0.882).

## What each part contributes (ablation, test nDCG@5)

| Setting | Test nDCG@5 | Full system's gain [95% CI] | Better/tied/worse | p |
|---|---|---|---|---|
| Full system | 0.882 | – | – | – |
| No age weight | 0.577 | +0.305 [+0.167, +0.439] | 7/1/0 | 0.016 |
| No rule priority (α = 0: age weight + similarity) | 0.881 | +0.001 [−0.051, +0.057] | 3/2/3 | 0.781 |
| Similarity only (hybrid retrieval) | 0.604 | +0.278 [+0.141, +0.422] | 8/0/0 | 0.008 |

- **The age weight does almost all the work on the test children.** Without it, test nDCG@5 falls to 0.577, which is the SBERT-only level.
- **Rule priority adds nothing measurable on test** (+0.001, p = 0.781). On tune it adds more: 0.822 against 0.781 at α = 0.
- **The same pattern appeared in v2,** where α = 0.7 beat α = 0 by only +0.029 (not significant) ([eval_v2_statistics.md](eval_v2_statistics.md)).
- **The rule priority still decides which area the ideas focus on,** and the explanations name the milestones and concerns behind it. The held-out grades judge relevance to the profile, so they can't show whether the area chosen is the one the child most needs.

## Agreement between raters

395 rows were graded by both raters (20 children):

| Measure | Value | 95% CI |
|---|---|---|
| Cohen's κ, unweighted | 0.471 | [0.377, 0.555] |
| Cohen's κ, linear | 0.556 | [0.477, 0.626] |
| Cohen's κ, quadratic | 0.655 | [0.587, 0.717] |
| Exact agreement | 0.663 | – |

Rows are the researcher's grades and columns the nurse's:

| | Nurse 0 | Nurse 1 | Nurse 2 | Total |
|---|---|---|---|---|
| Researcher 0 | 41 | 11 | 0 | 52 |
| Researcher 1 | 41 | 99 | 15 | 155 |
| Researcher 2 | 5 | 61 | 122 | 188 |

On the 15 new pairs alone, the raters gave the same grade to 9.

## Beyond accuracy (all 20 profiles, researcher's grades)

| Measure | v3 (α = 0.7) | SBERT only |
|---|---|---|
| Grade-0 slots in the top 5 (of 100) | 1 | 16 |
| …from another age band | 0 | 15 |
| Grade-0 slots in the 8 test top 5s | 0 | 6 |
| Areas per top 5 (mean) | 1.35 | 1.95 |
| Distinct activities across the 20 top 5s | 99 | 50 |
| Most frequent activity (top 5s it appears in) | 2 | 7 |

v3 concentrates on the priority area (1.35 areas per top 5) but repeats activities much less than SBERT only.

## Explanations

Batches were stored for the 20 profiles, giving 100 explanations:
- at most 3 sentences in any one (the limit is 4);
- 122 milestones, concerns and interests named, **none of them outside the child's stored profile**;
- **no explanation shows a score.**

## Label coverage

Every top 5 in every setting is graded by both raters: every α, both baselines, both ablations, and H17. Nothing is UNKNOWN, and `raw/v3_ungraded_pairs.csv` has no rows.

## Limits

- **The same as v2 and #268:**
  - 20 constructed profiles, and 8 test children, so the results support no wider claims;
  - the main rater designed the system;
  - β was chosen on the tune children, with test figures in view ([eval_v3_statistics.md](eval_v3_statistics.md)).
- **The extra pairs were graded in later sessions** than the v2 sheet: 20 Nov for the TF-IDF pairs and 23 Nov for these 15. Drift between sessions can't be ruled out.
- **nDCG's ideal ordering** uses each child's graded pairs, as in v2. Grading more pairs can raise it; the H04 change above is an example.
