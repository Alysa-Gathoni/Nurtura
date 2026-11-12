# Held-out evaluation (v2)

> Generated 2026-11-12T21:57:21+03:00 at commit `1b4c11e` by `backend\venv\Scripts\python.exe scripts\report_evidence\evaluation.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

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

**Who produced the labels (repository evidence):** `docs/eval_v2_results.md:29`: "graded 0/1/2 by the researcher, blind (no scores, ranks or areas shown)"; `:33`: one rater. `relevance_rater2` is empty in the sheet.

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
