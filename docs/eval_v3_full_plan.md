# Full v3 evaluation: plan

> **Last updated: 2026-11-22.** Written and committed before any result of this run was computed (issue #270). Results go in `docs/report_evidence/04_evaluation.md` ("Full evaluation of the current system (v3)") and in `docs/eval_v3_full_results.md`.

## Purpose

Report the system the app runs now in Chapter 5, not the v2 (SBERT-only) system. v3 is retrieval mixing SBERT and TF-IDF at β = 0.25 (`settings.RETRIEVAL_BETA`) and the current ranking `age_weight × ((1 − α)·similarity + α·priority)` with α = 0.7. The app's settings and ranking code don't change.

**Already seen before this plan:** the α sensitivity check at β = 0.25 (#260: tune and test nDCG@5 by α, with ungraded pairs counted as not relevant) and the v3 significance tests against SBERT only and the v2 system (#268). This run repeats some of those figures under the stricter coverage rules below, and adds the rest.

## Data and method (as v2 and #268)

- **Profiles:** the 20 held-out profiles H01–H20 with the fixed split: 11 tune, 8 test (primary), and H17 (content gap), reported separately.
- **Labels:** `data/evaluation/heldout_labels_v2.csv` plus `data/evaluation/tfidf_extra.csv`. `relevance` (the researcher) is the main label; `relevance_rater2` is the nurse's.
- **Baselines (similarity only, no rule priority, no age weight):**
  - (a) **SBERT only:** β = 1, the baseline of v2 and #268;
  - (b) **hybrid retrieval only:** β = 0.25.
- **Statistics:**
  - per-child paired differences;
  - a percentile bootstrap 95% CI (10,000 resamples of children, seed 2026);
  - a two-sided Wilcoxon signed-rank test with zero differences dropped.

  The test children are primary.
- **Data:** fictional only. The children are created inside a transaction that is rolled back.

## Label coverage

Changing α (or removing a component) can put pairs in a top 5 that were never graded.

- **No imputing.** Grades are never imputed, ungraded pairs are never treated as 0, and nothing is graded by the person running this.
- **Counted per setting:** for every setting, and per set (tune, test, gap), the number of graded and ungraded top-5 pairs, for each rater.
- **Listed:** every ungraded pair goes to `raw/v3_ungraded_pairs.csv`, with:
  - child, activity ID, activity name and child age;
  - the setting(s) it appears in;
  - empty researcher and rater-2 grade columns.
- **UNKNOWN:** a per-child figure that needs an ungraded top-k pair is UNKNOWN, and so is any mean or test that uses it.
- **Selection rule:** the rule below is applied only to the α values whose tune mean is known. Any α left out is named.
- **Convention kept from v2:** nDCG's ideal ordering uses the child's graded pairs.

## What is computed (β = 0.25)

1. **α grid** 0.0 to 1.0 in steps of 0.1, plus both baselines: mean nDCG@5 on tune and on test.
   - Apply the pre-registered selection rule: the highest tune mean; if several values are within 0.02 of it, the middle of that range.
   - Report the rule's choice.
   - Figure `v3_alpha_curve.png`: nDCG@5 against α for tune and test, with both baselines.
2. **Test set at α = 0.7** against SBERT only and against hybrid retrieval only:
   - nDCG@5 and nDCG@3;
   - P@5 counting grade ≥ 1;
   - P@5 counting grade 2 only.
3. **Per-profile nDCG@5** for the 8 test children and H17:
   - at α = 0.7 and for both baselines, on both raters' labels;
   - better, tied and worse counts against each baseline;
   - figure `v3_per_profile.png`.
4. **Rater agreement** over all rows graded by both raters (v2 rows plus extra rows):
   - unweighted, linear and quadratic Cohen's κ, each with a bootstrap 95% CI over children;
   - exact agreement;
   - the 3 × 3 confusion matrix, with the number of rows.
5. **Test comparison on each rater's labels,** α = 0.7 against SBERT only:
   - n and the mean of each;
   - the difference with its 95% CI;
   - better, tied and worse counts;
   - W and p.
6. **Beyond accuracy,** over all 20 profiles, at α = 0.7 and for SBERT only:
   - grade-0 slots in the top 5 (of 100), and how many are from another age band;
   - grade-0 slots in the 8 test top 5s;
   - the mean number of areas per top 5;
   - distinct activities across the 20 top 5s, and the most frequent activity's count;
   - grade by rank position (1–5), with figure `v3_grade_by_rank.png`.
7. **Ablation on the test set:**
   - the settings: the full system (α = 0.7); no age weight (α = 0.7, `use_age=False`); no rule priority (α = 0: age weight and similarity); similarity only (hybrid retrieval);
   - for each, nDCG@5, with paired differences (CI and Wilcoxon) between the full system and each ablation.
8. **Explanation check:** the batches stored by `generation.generate` for the 20 profiles. Report:
   - the number of explanations;
   - the maximum sentences in one explanation;
   - the number of milestones, concerns and interests named that aren't in the child's stored profile (expected 0);
   - whether any explanation shows a score (a decimal number, a percentage or the word "score"; expected none).

## Outputs

- **Command:** `manage.py evaluate_v3_full --markdown [--raw-dir PATH]`.
- **Evidence pack:** a section in `scripts/report_evidence/evaluation.py`, so it appears in `04_evaluation.md` with the command, date and commit.
- **Raw files** in `raw/`:
  - `v3_alpha_grid.csv`, `v3_test_results.csv`, `v3_per_profile_by_rater.csv`;
  - `v3_rater_agreement.json`, `v3_confusion.csv`;
  - `v3_beyond_accuracy.csv`, `v3_rank_grade_matrix.csv`;
  - `v3_ablation.csv`, `v3_explanation_check.json`, `v3_ungraded_pairs.csv`.
- **Figures:** `v3_alpha_curve.png`, `v3_per_profile.png` and `v3_grade_by_rank.png`, on white backgrounds with black and grey text sized for print.
- **Finally:** the full backend test suite, the provenance check, a regenerated evidence pack, and the tag `sprint9-eval-v3.2`.
- **Reported whatever the result.**
