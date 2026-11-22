# Held-out evaluation (v2 and v3)

> Generated 2026-11-23T00:22:17+03:00 at commit `3966c02` by `backend\venv\Scripts\python.exe scripts\report_evidence\evaluation.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

Labels: `data/evaluation/heldout_labels_v2.csv`. Raw command output: `raw/alpha_grid_markdown.txt` (`manage.py evaluate_alpha_grid --markdown --report-alpha 0.7`). The tables below are recomputed from the same rankings and labels.

## 1f. Tuning curve (11 tune children, mean of each metric)

`raw/alpha_curve.csv` (also holds the test-set means). Precision counts grade ≥ 1 or grade 2 in the top k.

| Ranking | P@3>=1 | P@5>=1 | P@3>=2 | P@5>=2 | nDCG@3 | nDCG@5 |
|---|---|---|---|---|---|---|
| SBERT-only | 0.848 | 0.818 | 0.364 | 0.364 | 0.549 | 0.548 |
| alpha 0.0 | 0.879 | 0.891 | 0.515 | 0.527 | 0.666 | 0.677 |
| alpha 0.1 | 0.909 | 0.927 | 0.576 | 0.545 | 0.711 | 0.711 |
| alpha 0.2 | 0.909 | 0.927 | 0.606 | 0.618 | 0.722 | 0.745 |
| alpha 0.3 | 0.909 | 0.927 | 0.606 | 0.618 | 0.722 | 0.745 |
| alpha 0.4 | 0.909 | 0.927 | 0.606 | 0.600 | 0.722 | 0.736 |
| alpha 0.5 | 0.909 | 0.927 | 0.606 | 0.600 | 0.722 | 0.736 |
| alpha 0.6 | 0.909 | 0.927 | 0.606 | 0.600 | 0.722 | 0.736 |
| alpha 0.7 | 0.909 | 0.927 | 0.606 | 0.600 | 0.722 | 0.736 |
| alpha 0.8 | 0.909 | 0.927 | 0.606 | 0.600 | 0.722 | 0.736 |
| alpha 0.9 | 0.909 | 0.927 | 0.606 | 0.600 | 0.722 | 0.736 |
| alpha 1.0 | 0.970 | 0.909 | 0.788 | 0.673 | 0.878 | 0.829 |

## Test children: α = 0.7 against SBERT-only (and H17 separately)

`raw/per_profile_test.csv`.

| Child | Split | Ranking | P@3>=1 | P@5>=1 | P@3>=2 | P@5>=2 | nDCG@3 | nDCG@5 |
|---|---|---|---|---|---|---|---|---|
| H02 | test | alpha 0.7 | 1.000 | 1.000 | 0.667 | 0.800 | 0.844 | 0.887 |
| H02 | test | SBERT-only | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.903 |
| H03 | test | alpha 0.7 | 1.000 | 1.000 | 0.333 | 0.200 | 0.490 | 0.548 |
| H03 | test | SBERT-only | 0.667 | 0.600 | 0.000 | 0.000 | 0.177 | 0.217 |
| H04 | test | alpha 0.7 | 1.000 | 1.000 | 0.667 | 0.600 | 0.803 | 0.760 |
| H04 | test | SBERT-only | 0.667 | 0.800 | 0.333 | 0.600 | 0.547 | 0.673 |
| H07 | test | alpha 0.7 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| H07 | test | SBERT-only | 1.000 | 1.000 | 0.667 | 0.600 | 0.844 | 0.799 |
| H10 | test | alpha 0.7 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| H10 | test | SBERT-only | 1.000 | 1.000 | 1.000 | 0.600 | 1.000 | 0.815 |
| H14 | test | alpha 0.7 | 1.000 | 1.000 | 1.000 | 0.600 | 1.000 | 0.815 |
| H14 | test | SBERT-only | 0.333 | 0.400 | 0.000 | 0.200 | 0.156 | 0.244 |
| H15 | test | alpha 0.7 | 1.000 | 1.000 | 0.667 | 0.800 | 0.687 | 0.774 |
| H15 | test | SBERT-only | 1.000 | 1.000 | 0.333 | 0.200 | 0.646 | 0.559 |
| H17 | gap | alpha 0.7 | 1.000 | 1.000 | 0.667 | 0.600 | 0.687 | 0.686 |
| H17 | gap | SBERT-only | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.903 |
| H18 | test | alpha 0.7 | 1.000 | 1.000 | 1.000 | 0.800 | 1.000 | 0.903 |
| H18 | test | SBERT-only | 1.000 | 1.000 | 0.333 | 0.200 | 0.490 | 0.446 |

## Labels per split

| Split | Children | Rows | Grade 0 | Grade 1 | Grade 2 | Blank |
|---|---|---|---|---|---|---|
| tune | 11 | 141 | 21 | 55 | 65 | 0 |
| test | 8 | 101 | 6 | 34 | 61 | 0 |
| gap | 1 | 15 | 1 | 4 | 10 | 0 |

**Who produced the labels (repository evidence):** `docs/eval_v2_results.md:29`: "graded 0/1/2 by the researcher, blind (no scores, ranks or areas shown)"; first rater.

### Second rater

Since #218, a second rater (a registered nurse, independent of the project) has graded 257 rows blind in `relevance_rater2` (`docs/eval_v2_statistics.md:96`). Raw: `raw/rater_agreement.json`, `raw/rater_confusion.csv`, `raw/per_profile_test_by_rater.csv`. Bootstrap intervals resample children (10,000, seed 2026).

| Measure | Value | 95% CI |
|---|---|---|
| Cohen's kappa, unweighted | 0.416 | [0.297, 0.523] |
| Cohen's kappa, linear | 0.533 | [0.443, 0.612] |
| Cohen's kappa, quadratic | 0.661 | [0.589, 0.718] |
| Exact agreement | 0.623 | - |

Rows: first rater (researcher); columns: second rater (nurse).

|  | Second 0 | Second 1 | Second 2 |
|---|---|---|---|
| First 0 | 27 | 1 | 0 |
| First 1 | 39 | 48 | 6 |
| First 2 | 2 | 49 | 85 |

Test set on the second rater's labels: α = 0.7 0.737 against SBERT-only 0.398, difference +0.339 [+0.156, +0.532], 7/0/1 better/tied/worse, Wilcoxon p = 0.016. Quadratic-weighted κ (main figure): 0.661.

| Child | Researcher α = 0.7 | Researcher SBERT-only | Nurse α = 0.7 | Nurse SBERT-only |
|---|---|---|---|---|
| H02 | 0.887 | 0.903 | 0.903 | 1.000 |
| H03 | 0.548 | 0.217 | 0.296 | 0.060 |
| H04 | 0.760 | 0.673 | 0.595 | 0.321 |
| H07 | 1.000 | 0.799 | 1.000 | 0.756 |
| H10 | 1.000 | 0.815 | 1.000 | 0.476 |
| H14 | 0.815 | 0.244 | 0.893 | 0.048 |
| H15 | 0.774 | 0.559 | 0.661 | 0.113 |
| H18 | 0.903 | 0.446 | 0.548 | 0.409 |

## Difference from the sprint5-eval-v1 results document

`docs/sprint5_alpha_results.md` reports the **v1** evaluation (54 activities, 205 labels; reproducible from tag `sprint5-eval-v1`). This page reports **v2** (current catalogue, `heldout_labels_v2.csv`). The figures differ by design. v1 rows for comparison:

- line 55: | SBERT-only | 0.758 | 0.618 | 0.242 | 0.182 | 0.505 | 0.491 |
- line 63: | **α = 0.7 (chosen)** | 0.939 | 0.909 | 0.667 | 0.527 | 0.844 | 0.873 |
- line 103: | SBERT-only | 0.708 | 0.700 | 0.292 | 0.300 | 0.441 | 0.452 |
- line 106: | **α = 0.7 (chosen)** | **1.000** | **0.925** | **0.625** | **0.675** | **0.789** | **0.814** |
- line 125: | **α = 0.7 (chosen)** | **7 / 0 / 1** | **7 / 0 / 1** |

## 1g. Exploratory measures (labelled as such: not part of the fixed protocol)

- **Distinct areas in each child's top 5:** `raw/exploratory_top5.csv`. Mean at α = 0.7: 1.40; SBERT-only: 1.95.
- **Catalogue coverage at α = 0.7:** 96 distinct activities across the 20 top-5 lists, out of 449 Published activities (not 54: the catalogue grew after v1). The most possible is 100 (20 × 5).
- **How often each activity appears:** `raw/activity_frequency_alpha_0.7.csv`; the most frequent appears in 2 top-5 lists.

| Child | Split | Areas in top 5 (α = 0.7) | Areas (SBERT-only) |
|---|---|---|---|
| H01 | tune | 1 | 2 |
| H02 | test | 1 | 2 |
| H03 | test | 1 | 1 |
| H04 | test | 1 | 2 |
| H05 | tune | 1 | 2 |
| H06 | tune | 1 | 2 |
| H07 | test | 1 | 2 |
| H08 | tune | 1 | 1 |
| H09 | tune | 1 | 3 |
| H10 | test | 5 | 2 |
| H11 | tune | 1 | 1 |
| H12 | tune | 1 | 3 |
| H13 | tune | 1 | 1 |
| H14 | test | 1 | 1 |
| H15 | test | 1 | 3 |
| H16 | tune | 1 | 3 |
| H17 | gap | 1 | 1 |
| H18 | test | 1 | 1 |
| H19 | tune | 2 | 3 |
| H20 | tune | 4 | 3 |

## 2d. Figure data

| Figure | Data |
|---|---|
| α curve with the SBERT-only line | `raw/alpha_curve.csv` (split = tune) |
| Per-profile test nDCG@5, baseline vs α = 0.7 | `raw/per_profile_test.csv` |
| Grade distribution by split | `raw/grade_distribution.csv` |
| Rank × grade matrix (error analysis) | `raw/rank_grade_matrix.csv` |
| Where grade-0 results come from | `raw/grade0_sources.csv` |

Grade-0 results in the top 5 (all 20 children), by area and by age band relative to the child:

| Ranking | Grade-0 slots | By area | By age band |
|---|---|---|---|
| alpha 0.7 | 4 | {'Motor': 2, 'Socio-Emotional': 1, 'Cognitive': 1} | {'same band': 4} |
| SBERT-only | 16 | {'Motor': 8, 'Socio-Emotional': 2, 'Cognitive': 3, 'Language': 2, 'Sensory': 1} | {'+1 band(s)': 3, '+2 band(s)': 4, '+4 band(s)': 1, '+3 band(s)': 2, 'same band': 1, '-2 band(s)': 3, '-3 band(s)': 2} |

## TF-IDF alongside SBERT (#248) and the app's retrieval (#250)

The tables above are the frozen v2 record, ranked with SBERT only (β = 1, run here with `RETRIEVAL_BETA=1`). Since #250 the app's retrieval is `similarity = β × SBERT + (1 − β) × TF-IDF` with β = 0.25 (`backend/nurtura_backend/settings.py:322`, `backend/recommendations/retrieval.py:49`). The comparison below grades every top-5 pair: the v2 labels plus `data/evaluation/tfidf_extra.csv` (123 extra pairs, graded by the researcher; the nurse's grades are in `relevance_rater2`). Raw output: `raw/tfidf_comparison_markdown.txt` (`manage.py compare_tfidf --markdown --extra-labels data/evaluation/tfidf_extra.csv`). Mean nDCG@5:

| β | Tune, similarity-only | Tune, α = 0.7 | Test, similarity-only | Test, α = 0.7 |
|---|---|---|---|---|
| beta 0.00 (TF-IDF only) | 0.417 | 0.872 | 0.543 | 0.886 |
| beta 0.25 | 0.474 | 0.822 | 0.604 | 0.882 |
| beta 0.50 | 0.499 | 0.782 | 0.612 | 0.881 |
| beta 0.75 | 0.537 | 0.741 | 0.607 | 0.852 |
| beta 1.00 (SBERT only) | 0.535 | 0.720 | 0.577 | 0.823 |

The pre-registered rule's choice on these labels: beta 0.00 (TF-IDF only). The app uses β = 0.25, chosen deliberately: it is the rule's choice on the nurse's grades and within 0.004 of β = 0 on test under both raters (`docs/tfidf_comparison.md:108`).

## Significance tests for v3 (#268)

The app's configuration (β = 0.25, α = 0.7) against SBERT only and against the v2 system (β = 1, α = 0.7), on the same labels (v2 sheet plus `data/evaluation/tfidf_extra.csv`). Per-child nDCG@5 differences, bootstrap 95% CI (10,000 resamples of children, seed 2026), two-sided Wilcoxon signed-rank test; the 8 test children are primary. The plan was fixed in issue #268 before the run (`docs/eval_v3_statistics.md:9`). β was chosen on the tune children, so tune figures against the v2 system aren't independent evidence. Raw output: `raw/v3_statistics_markdown.txt` (`manage.py evaluate_v3_statistics --markdown`).

### Paired nDCG@5, researcher's grades
| Against | Children | n | v3 | Other | Difference | 95% CI | Better/tied/worse | Non-zero | W | p |
|---|---|---|---|---|---|---|---|---|---|---|
| SBERT only (beta 1, similarity only) | Test (primary) | 8 | 0.882 | 0.577 | +0.305 | [+0.164, +0.455] | 8/0/0 | 8 | 0 | 0.008 |
| SBERT only (beta 1, similarity only) | Tune | 11 | 0.822 | 0.535 | +0.287 | [+0.168, +0.400] | 9/1/1 | 10 | 1 | 0.004 |
| SBERT only (beta 1, similarity only) | Tune + test | 19 | 0.847 | 0.553 | +0.295 | [+0.204, +0.385] | 17/1/1 | 18 | 2 | < 0.001 |
| v2 system (beta 1, alpha 0.7) | Test (primary) | 8 | 0.882 | 0.823 | +0.059 | [-0.005, +0.127] | 5/2/1 | 6 | 3 | 0.156 |
| v2 system (beta 1, alpha 0.7) | Tune | 11 | 0.822 | 0.720 | +0.103 | [+0.027, +0.189] | 8/2/1 | 9 | 4.5 | 0.031 |
| v2 system (beta 1, alpha 0.7) | Tune + test | 19 | 0.847 | 0.763 | +0.084 | [+0.032, +0.143] | 13/4/2 | 15 | 13.5 | 0.008 |

### Paired nDCG@5, nurse's grades
| Against | Children | n | v3 | Other | Difference | 95% CI | Better/tied/worse | Non-zero | W | p |
|---|---|---|---|---|---|---|---|---|---|---|
| SBERT only (beta 1, similarity only) | Test (primary) | 8 | 0.788 | 0.382 | +0.406 | [+0.225, +0.561] | 7/0/1 | 8 | 1 | 0.016 |
| SBERT only (beta 1, similarity only) | Tune | 11 | 0.802 | 0.400 | +0.402 | [+0.305, +0.492] | 11/0/0 | 11 | 0 | < 0.001 |
| SBERT only (beta 1, similarity only) | Tune + test | 19 | 0.796 | 0.393 | +0.404 | [+0.307, +0.489] | 18/0/1 | 19 | 2 | < 0.001 |
| v2 system (beta 1, alpha 0.7) | Test (primary) | 8 | 0.788 | 0.700 | +0.089 | [-0.020, +0.213] | 3/2/3 | 6 | 6 | 0.438 |
| v2 system (beta 1, alpha 0.7) | Tune | 11 | 0.802 | 0.683 | +0.119 | [+0.037, +0.210] | 7/4/0 | 7 | 0 | 0.016 |
| v2 system (beta 1, alpha 0.7) | Tune + test | 19 | 0.796 | 0.690 | +0.106 | [+0.039, +0.181] | 10/6/3 | 13 | 12 | 0.017 |

## Full evaluation of the current system (v3)

The configuration the app uses (β = 0.25, α = 0.7), evaluated in full with the v2 method, so Chapter 5 can report the current system (#270). The plan was committed before the run (`docs/eval_v3_full_plan.md:40`). Labels: the v2 sheet plus `data/evaluation/tfidf_extra.csv`; researcher's grades unless stated. No grade is imputed and no ungraded pair counts as 0: figures that need one are UNKNOWN, and every ungraded pair is in `raw/v3_ungraded_pairs.csv` with empty grade columns. Command: `manage.py evaluate_v3_full --markdown --raw-dir docs/report_evidence/raw` (raw output `raw/v3_full_markdown.txt`). Raw tables: `raw/v3_alpha_grid.csv`, `raw/v3_test_results.csv`, `raw/v3_per_profile_by_rater.csv`, `raw/v3_rater_agreement.json`, `raw/v3_confusion.csv`, `raw/v3_beyond_accuracy.csv`, `raw/v3_rank_grade_matrix.csv`, `raw/v3_ablation.csv`, `raw/v3_explanation_check.json`, `raw/v3_label_coverage.csv`. Figures: `figures/v3_alpha_curve.png`, `figures/v3_per_profile.png`, `figures/v3_grade_by_rank.png` (see `09_figures.md`).

### Setting
v3: retrieval beta 0.25 (settings.RETRIEVAL_BETA), alpha 0.7. Labels: heldout_labels_v2.csv, tfidf_extra.csv. Plan fixed before the run: docs/eval_v3_full_plan.md (#270).
Bootstrap: 10,000 resamples of children, seed 2026, percentile 95% interval. Wilcoxon: two-sided signed-rank test, zero differences dropped. Test children primary.
No grade is imputed and no ungraded pair counts as 0: a figure that needs an ungraded top-k pair is UNKNOWN.

### Label coverage (top-5 pairs)
| Setting | Tune graded | Test graded | Gap (H17) graded |
|---|---|---|---|
| SBERT only | 55/55 (0 ungraded by nurse) | 40/40 (0 ungraded by nurse) | 5/5 (0 ungraded by nurse) |
| Hybrid retrieval only | 55/55 (0 ungraded by nurse) | 40/40 (0 ungraded by nurse) | 5/5 (0 ungraded by nurse) |
| alpha 0.0 | 50/55 (5 ungraded by nurse) | 35/40 (5 ungraded by nurse) | 3/5 (2 ungraded by nurse) |
| alpha 0.1 | 53/55 (2 ungraded by nurse) | 39/40 (1 ungraded by nurse) | 4/5 (1 ungraded by nurse) |
| alpha 0.2 | 55/55 (0 ungraded by nurse) | 40/40 (0 ungraded by nurse) | 4/5 (1 ungraded by nurse) |
| alpha 0.3 | 55/55 (0 ungraded by nurse) | 40/40 (0 ungraded by nurse) | 4/5 (1 ungraded by nurse) |
| alpha 0.4 | 55/55 (0 ungraded by nurse) | 40/40 (0 ungraded by nurse) | 5/5 (0 ungraded by nurse) |
| alpha 0.5 | 55/55 (0 ungraded by nurse) | 40/40 (0 ungraded by nurse) | 5/5 (0 ungraded by nurse) |
| alpha 0.6 | 55/55 (0 ungraded by nurse) | 40/40 (0 ungraded by nurse) | 5/5 (0 ungraded by nurse) |
| alpha 0.7 | 55/55 (0 ungraded by nurse) | 40/40 (0 ungraded by nurse) | 5/5 (0 ungraded by nurse) |
| alpha 0.8 | 55/55 (0 ungraded by nurse) | 40/40 (0 ungraded by nurse) | 5/5 (0 ungraded by nurse) |
| alpha 0.9 | 55/55 (0 ungraded by nurse) | 40/40 (0 ungraded by nurse) | 5/5 (0 ungraded by nurse) |
| alpha 1.0 | 55/55 (0 ungraded by nurse) | 40/40 (0 ungraded by nurse) | 5/5 (0 ungraded by nurse) |
| No age weight | 53/55 (2 ungraded by nurse) | 39/40 (1 ungraded by nurse) | 5/5 (0 ungraded by nurse) |

Ungraded pairs across all settings: 15 (15 need grading by both raters). Listed in raw/v3_ungraded_pairs.csv with empty grade columns.

### 1. Alpha grid (mean nDCG@5, researcher's grades)
| Setting | Tune | Test | Ungraded (tune) | Ungraded (test) |
|---|---|---|---|---|
| SBERT only | 0.535 | 0.577 | 0 | 0 |
| Hybrid retrieval only | 0.474 | 0.604 | 0 | 0 |
| alpha 0.0 | UNKNOWN | UNKNOWN | 5 | 5 |
| alpha 0.1 | UNKNOWN | UNKNOWN | 2 | 1 |
| alpha 0.2 | 0.820 | 0.892 | 0 | 0 |
| alpha 0.3 | 0.821 | 0.893 | 0 | 0 |
| alpha 0.4 | 0.820 | 0.893 | 0 | 0 |
| alpha 0.5 | 0.814 | 0.882 | 0 | 0 |
| alpha 0.6 | 0.822 | 0.882 | 0 | 0 |
| alpha 0.7 | 0.822 | 0.882 | 0 | 0 |
| alpha 0.8 | 0.822 | 0.882 | 0 | 0 |
| alpha 0.9 | 0.822 | 0.882 | 0 | 0 |
| alpha 1.0 | 0.803 | 0.852 | 0 | 0 |

Rule (best tune mean, middle of the range within 0.02): best 0.822; within 0.02: 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0; chosen alpha 0.6. Left out (tune mean UNKNOWN): 0.0, 0.1.

### 2. Test set at alpha 0.7 against both baselines
| Setting | nDCG@5 | nDCG@3 | P@5>=1 | P@5=2 |
|---|---|---|---|---|
| alpha 0.7 | 0.882 | 0.897 | 1.000 | 0.825 |
| Hybrid retrieval only | 0.604 | 0.588 | 0.875 | 0.450 |
| SBERT only | 0.577 | 0.608 | 0.850 | 0.400 |

P@5>=1 counts grade 1 or 2 in the top 5; P@5=2 counts grade 2 only.

### 3. Per-profile nDCG@5 (8 test children and H17)
| Child | Split | Rater | alpha 0.7 | Hybrid retrieval only | SBERT only |
|---|---|---|---|---|---|
| H02 | test | researcher | 0.913 | 0.869 | 0.903 |
| H02 | test | nurse | 0.887 | 0.913 | 1.000 |
| H03 | test | researcher | 0.686 | 0.462 | 0.177 |
| H03 | test | nurse | 0.686 | 0.462 | 0.049 |
| H04 | test | researcher | 0.913 | 0.790 | 0.673 |
| H04 | test | nurse | 0.752 | 0.365 | 0.287 |
| H07 | test | researcher | 1.000 | 0.688 | 0.799 |
| H07 | test | nurse | 1.000 | 0.590 | 0.756 |
| H10 | test | researcher | 1.000 | 0.647 | 0.815 |
| H10 | test | nurse | 1.000 | 0.431 | 0.476 |
| H14 | test | researcher | 0.857 | 0.261 | 0.244 |
| H14 | test | nurse | 0.760 | 0.318 | 0.044 |
| H15 | test | researcher | 0.686 | 0.672 | 0.559 |
| H15 | test | nurse | 0.573 | 0.601 | 0.113 |
| H18 | test | researcher | 1.000 | 0.446 | 0.446 |
| H18 | test | nurse | 0.647 | 0.559 | 0.333 |
| H17 | gap | researcher | 0.563 | 0.774 | 0.903 |
| H17 | gap | nurse | 0.677 | 0.349 | 0.228 |

Test, researcher's grades, alpha 0.7 against SBERT only: 8/0/0 better/tied/worse.
Test, researcher's grades, alpha 0.7 against Hybrid retrieval only: 8/0/0 better/tied/worse.
Test, nurse's grades, alpha 0.7 against SBERT only: 7/0/1 better/tied/worse.
Test, nurse's grades, alpha 0.7 against Hybrid retrieval only: 6/0/2 better/tied/worse.

### 4. Agreement between raters (every row graded by both)
380 rows (20 children).

| Measure | Value | 95% CI |
|---|---|---|
| Cohen's kappa, unweighted | 0.477 | [0.381, 0.562] |
| Cohen's kappa, linear | 0.564 | [0.484, 0.633] |
| Cohen's kappa, quadratic | 0.665 | [0.599, 0.723] |
| Exact agreement | 0.666 | - |

Rows: researcher; columns: nurse.

|  | Nurse 0 | Nurse 1 | Nurse 2 | Total |
|---|---|---|---|---|
| Researcher 0 | 41 | 10 | 0 | 51 |
| Researcher 1 | 41 | 97 | 12 | 150 |
| Researcher 2 | 4 | 60 | 115 | 179 |

### 5. Test: alpha 0.7 against SBERT only, on each rater's grades
| Rater | n | alpha 0.7 | SBERT only | Difference [95% CI] | Better/tied/worse | W | p |
|---|---|---|---|---|---|---|---|
| researcher | 8 | 0.882 | 0.577 | +0.305 [+0.164, +0.455] | 8/0/0 | 0 | 0.008 |
| nurse | 8 | 0.788 | 0.382 | +0.406 [+0.225, +0.561] | 7/0/1 | 1 | 0.016 |

### 6. Beyond accuracy (all 20 profiles, researcher's grades)
| Setting | Grade-0 slots (of 100) | From another age band | Grade-0 slots, test | Areas per top 5 | Distinct activities | Most frequent |
|---|---|---|---|---|---|---|
| alpha 0.7 | 1 | 0 | 0 | 1.35 | 99 | 2 (ACT-0038 Simple Puzzle and Sorting Play) |
| SBERT only | 16 | 15 | 6 | 1.95 | 50 | 7 (ACT-0125 Songs Every Day) |

Grade by rank position, all 20 profiles:

| Setting | Rank | Grade 0 | Grade 1 | Grade 2 | Ungraded |
|---|---|---|---|---|---|
| alpha 0.7 | 1 | 0 | 4 | 16 | 0 |
| alpha 0.7 | 2 | 0 | 3 | 17 | 0 |
| alpha 0.7 | 3 | 1 | 4 | 15 | 0 |
| alpha 0.7 | 4 | 0 | 7 | 13 | 0 |
| alpha 0.7 | 5 | 0 | 8 | 12 | 0 |
| SBERT only | 1 | 2 | 6 | 12 | 0 |
| SBERT only | 2 | 5 | 9 | 6 | 0 |
| SBERT only | 3 | 2 | 10 | 8 | 0 |
| SBERT only | 4 | 3 | 11 | 6 | 0 |
| SBERT only | 5 | 4 | 8 | 8 | 0 |

### 7. Ablation on the test set (nDCG@5, researcher's grades)
| Setting | Test nDCG@5 | Ungraded (test) | Full minus this [95% CI] | Full better/tied/worse | W | p |
|---|---|---|---|---|---|---|
| Full system | 0.882 | 0 | - | - | - | - |
| No age weight | UNKNOWN | 1 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| No rule priority (age weight + similarity) | UNKNOWN | 5 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Similarity only (hybrid retrieval) | 0.604 | 0 | +0.278 [+0.141, +0.422] | 8/0/0 | 0 | 0.008 |

### 8. Explanation check (stored batches, 20 profiles)
| Measure | Value |
|---|---|
| Profiles | 20 |
| Explanations | 100 |
| Most sentences in one explanation | 3 |
| Milestones, concerns and interests named | 122 |
| Named but not in the stored profile | 0 |
| Explanations showing a score | 0 |
