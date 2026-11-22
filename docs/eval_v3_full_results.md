# Full v3 evaluation: results (#270)

> **Last updated: 2026-11-23.** Every figure is from `python manage.py evaluate_v3_full --markdown` (from `backend/`), run on 23 Nov 2026 at the app's configuration (β = 0.25, α = 0.7). The plan ([eval_v3_full_plan.md](eval_v3_full_plan.md)) was committed before the run. The full tables, raw files and figures are in the evidence pack: [report_evidence/04_evaluation.md](report_evidence/04_evaluation.md) ("Full evaluation of the current system (v3)") and [report_evidence/09_figures.md](report_evidence/09_figures.md).

## Headline results (8 test children, researcher's grades)

| Measure | v3 (α = 0.7) | Hybrid retrieval only | SBERT only |
|---|---|---|---|
| nDCG@5 | **0.882** | 0.604 | 0.577 |
| nDCG@3 | **0.897** | 0.588 | 0.608 |
| P@5, grade ≥ 1 | **1.000** | 0.875 | 0.850 |
| P@5, grade 2 | **0.825** | 0.450 | 0.400 |

- **Against SBERT only:** +0.305 nDCG@5, 95% CI [+0.164, +0.455], all 8 children better, W = 0, p = 0.008.
  - On the nurse's grades: 0.788 against 0.382, +0.406, CI [+0.225, +0.561], 7 of 8 better, W = 1, p = 0.016.
- **Against hybrid retrieval only** (the ablation "similarity only"): +0.278, CI [+0.141, +0.422], 8 of 8 better, p = 0.008.
  - On the nurse's grades: 6 of 8 better.
- **H17 (content gap), reported separately:**
  - researcher's grades: v3 0.563, against 0.774 for hybrid retrieval and 0.903 for SBERT only;
  - nurse's grades: v3 0.677, against 0.349 and 0.228.

## α and the selection rule

- **Tune nDCG@5 at β = 0.25** is flat from α 0.2 to 0.9 (0.814 to 0.822), and 1.0 gives 0.803.
- **The rule** (the best tune mean, then the middle of the values within 0.02 of it) qualifies α 0.2 to 1.0 and **chooses α = 0.6**. α = 0.7 has the same tune and test scores (0.822 and 0.882).
- **α 0.0 and 0.1 are UNKNOWN** (ungraded pairs), so the rule left them out.

## Agreement between raters

380 rows were graded by both raters (the 257 v2 rows and the 123 extra rows, 20 children):

| Measure | Value | 95% CI |
|---|---|---|
| Cohen's κ, unweighted | 0.477 | [0.381, 0.562] |
| Cohen's κ, linear | 0.564 | [0.484, 0.633] |
| Cohen's κ, quadratic | 0.665 | [0.599, 0.723] |
| Exact agreement | 0.666 | – |

The nurse was usually stricter: 41 of the researcher's 1s were the nurse's 0s, and 60 of the researcher's 2s were the nurse's 1s.

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

## Ablation (test set, nDCG@5)

| Setting | Test nDCG@5 | Full system's gain |
|---|---|---|
| Full system | 0.882 | – |
| No age weight | UNKNOWN (1 ungraded pair) | UNKNOWN |
| No rule priority (α = 0) | UNKNOWN (5 ungraded pairs) | UNKNOWN |
| Similarity only (hybrid retrieval) | 0.604 | +0.278, CI [+0.141, +0.422], p = 0.008 |

## Explanations

Batches were stored for the 20 profiles, giving 100 explanations:
- at most 3 sentences in any one (the limit is 4);
- 122 milestones, concerns and interests named, **none of them outside the child's stored profile**;
- **no explanation shows a score.**

## Label coverage and what is UNKNOWN

- **Fully graded, for both raters:** every top 5 at α 0.4 to 1.0, for both baselines, and for every tune and test top 5 at α 0.2 and 0.3.
- **15 pairs are ungraded,** for both raters. They are listed in `docs/report_evidence/raw/v3_ungraded_pairs.csv` with empty grade columns:

| Setting | Ungraded pairs (tune / test / H17) | UNKNOWN because of them |
|---|---|---|
| α = 0.0 | 5 / 5 / 2 | the α 0.0 tune and test means; the "no rule priority" ablation |
| α = 0.1 | 2 / 1 / 1 | the α 0.1 tune and test means |
| α = 0.2 and 0.3 | 0 / 0 / 1 | nothing reported (H17 isn't in the means) |
| No age weight | 2 / 1 / 0 | the "no age weight" ablation |

- **What grading them would settle:** once both raters grade these 15 pairs, the α grid, the selection rule over every α and both remaining ablations will be complete.
- **Not affected:** every headline figure above (α = 0.7 and both baselines) is fully graded.
- **Grading them (#272):** `python manage.py evaluate_v3_full --export-ungraded PATH` writes the 15 pairs as a blind, shuffled sheet in the held-out format (child profile and activity only: no setting, rank or score). Once both raters have graded it, it goes in as `data/evaluation/v3_extra.csv`, and the command reads it automatically.

## Limits

- **The same as v2 and #268:**
  - 20 constructed profiles, and 8 test children, so the results support no wider claims;
  - the main rater designed the system;
  - β was chosen on the tune children, with test figures in view ([eval_v3_statistics.md](eval_v3_statistics.md)).
- **The extra pairs were graded in a later session** than the v2 sheet ([tfidf_comparison.md](tfidf_comparison.md#limits)).
- **nDCG's ideal ordering** uses each child's graded pairs, as in v2. Grading more pairs can raise it.
