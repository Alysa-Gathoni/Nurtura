# v3 statistics: significance tests for SBERT + TF-IDF (#268)

> **Last updated: 2026-11-22.** Every figure is from `python manage.py evaluate_v3_statistics --markdown` (from `backend/`), run on 22 Nov 2026 on `main` at the `sprint9-eval-v3.1` configuration (β = 0.25, α = 0.7). The plan below was fixed in issue #268 before the run.

## Question

The v2 evaluation has paired significance tests ([eval_v2_statistics.md](eval_v2_statistics.md)). The configuration the app has used since #250 (v3: SBERT and TF-IDF mixed at β = 0.25, α = 0.7) had only mean nDCG@5 ([tfidf_comparison.md](tfidf_comparison.md)). Are its gains statistically supported?

## Plan (fixed before running)

- **Data:** the 20 constructed held-out children (11 tune, 8 test). Labels: `heldout_labels_v2.csv` plus `tfidf_extra.csv`, so every compared top 5 is graded. The command refuses to report if any is ungraded.
- **Method:** as v2 (#196):
  - per-child nDCG@5 differences;
  - a bootstrap 95% interval (10,000 resamples of children, seed 2026);
  - a two-sided Wilcoxon signed-rank test, with ties dropped.
- **Two comparisons, both against v3:**
  1. **SBERT only** (β = 1, similarity only): does the final system beat semantic search alone?
  2. **The v2 system** (β = 1, α = 0.7): does adding TF-IDF improve the ranking?
- **Primary result:** the 8 test children, on the researcher's grades. Tune and tune + test are context.
- **Second rater:** the same comparisons on the nurse's grades for every pair.
- **Reported whatever the result.**

## Summary

| Question (8 test children) | Researcher's grades | Nurse's grades |
|---|---|---|
| Is v3 better than SBERT alone? | **Yes.** +0.305, 95% CI [+0.164, +0.455], all 8 children better, p = 0.008 | **Yes.** +0.406, CI [+0.225, +0.561], 7 of 8 better, p = 0.016 |
| Is v3 better than the v2 system? | **Not shown.** +0.059, CI [−0.005, +0.127], 5 better, 2 tied, 1 worse, p = 0.156 | **Not shown.** +0.089, CI [−0.020, +0.213], 3 / 2 / 3, p = 0.438 |

- **v3 against SBERT alone** holds up as strongly as v2 did (v2: +0.254, p = 0.016), under both raters.
- **Adding TF-IDF** raises the mean on test under both raters, but with 8 children the interval includes zero. Report it as a gain on these children, not a significant one.
- **On tune and tune + test** the gain over the v2 system is significant (for example tune + test +0.084, CI [+0.032, +0.143], p = 0.008). But β was chosen on the tune children, so the tune figures can't count as independent evidence (see Limits).

## Results

### Researcher's grades

| Against | Children | n | v3 | Other | Difference | 95% CI | Better/tied/worse | Non-zero | W | p |
|---|---|---|---|---|---|---|---|---|---|---|
| SBERT only | **Test (primary)** | 8 | 0.882 | 0.577 | **+0.305** | [+0.164, +0.455] | 8/0/0 | 8 | 0 | **0.008** |
| SBERT only | Tune | 11 | 0.822 | 0.535 | +0.287 | [+0.168, +0.400] | 9/1/1 | 10 | 1 | 0.004 |
| SBERT only | Tune + test | 19 | 0.847 | 0.553 | +0.295 | [+0.204, +0.385] | 17/1/1 | 18 | 2 | < 0.001 |
| v2 system | **Test (primary)** | 8 | 0.882 | 0.823 | **+0.059** | [−0.005, +0.127] | 5/2/1 | 6 | 3 | **0.156** |
| v2 system | Tune | 11 | 0.822 | 0.720 | +0.103 | [+0.027, +0.189] | 8/2/1 | 9 | 4.5 | 0.031 |
| v2 system | Tune + test | 19 | 0.847 | 0.763 | +0.084 | [+0.032, +0.143] | 13/4/2 | 15 | 13.5 | 0.008 |

### Nurse's grades

| Against | Children | n | v3 | Other | Difference | 95% CI | Better/tied/worse | Non-zero | W | p |
|---|---|---|---|---|---|---|---|---|---|---|
| SBERT only | **Test (primary)** | 8 | 0.788 | 0.382 | **+0.406** | [+0.225, +0.561] | 7/0/1 | 8 | 1 | **0.016** |
| SBERT only | Tune | 11 | 0.802 | 0.400 | +0.402 | [+0.305, +0.492] | 11/0/0 | 11 | 0 | < 0.001 |
| SBERT only | Tune + test | 19 | 0.796 | 0.393 | +0.404 | [+0.307, +0.489] | 18/0/1 | 19 | 2 | < 0.001 |
| v2 system | **Test (primary)** | 8 | 0.788 | 0.700 | **+0.089** | [−0.020, +0.213] | 3/2/3 | 6 | 6 | **0.438** |
| v2 system | Tune | 11 | 0.802 | 0.683 | +0.119 | [+0.037, +0.210] | 7/4/0 | 7 | 0 | 0.016 |
| v2 system | Tune + test | 19 | 0.796 | 0.690 | +0.106 | [+0.039, +0.181] | 10/6/3 | 13 | 12 | 0.017 |

**Why the nurse's figures differ from [tfidf_comparison.md](tfidf_comparison.md):** there, the nurse's grades replaced the researcher's for the 123 extra pairs only (test 0.870). Here the nurse's grades are used for every pair, so both sheets are the nurse's (test 0.788). The nurse was usually one grade stricter, so all nDCG values are lower.

## Limits

- **8 test children.** With 8 non-zero differences, the smallest possible two-sided Wilcoxon p is 0.008. The test has little power for a gain of about 0.06.
- **β was chosen on the tune children,** and the reason for 0.25 over the rule's choice of 0 cites test figures ([tfidf_comparison.md](tfidf_comparison.md#adopted-β--025-250)). So the tune comparisons with the v2 system are favourable by construction, and the test set isn't fully untouched for comparison 2.
- **Same limits as v2:** constructed children, and a main rater who designed the system ([known_limitations.md](known_limitations.md)).
- **The extra pairs were graded in a later session** than the v2 sheet ([tfidf_comparison.md](tfidf_comparison.md#limits)).

## Reproducing

```
cd backend
python manage.py evaluate_v3_statistics --markdown
```

It ranks each child at the app's β and at β = 1 inside a transaction that is rolled back, so nothing is stored. It refuses to run at `RETRIEVAL_BETA=1` (v3 and the v2 system would be the same) or if any compared top-5 activity is ungraded. The code is in `backend/recommendations/management/commands/evaluate_v3_statistics.py`; the statistics are those of `recommendations/statistics.py`.
