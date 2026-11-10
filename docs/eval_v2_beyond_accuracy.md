# Held-out evaluation v2: diversity, novelty, coverage and personalisation

Last updated: 2026-11-10

- **What this adds:** the personalisation measures promised in proposal Section 3.2.4 and NFR-12, for the same rankings as [eval_v2_results.md](eval_v2_results.md). Relevance is in that document; these measures need no labels.
- **Same state:** the 449 Published activities tagged `sprint9-eval-v2`. The provenance check matched on the day of the run.
- **Run:** 2026-11-10, with `python manage.py evaluate_beyond_accuracy --markdown` (#199).

## Summary

- **Personalised.** At α = 0.7, two children have on average 0.4% of their top 5 in common: personalisation 0.996 across all pairs, and 0.962 between children of the same age band.
- **Little repetition.** The 20 children's 100 top-5 slots hold 96 different activities. Coverage is 0.214, near the ceiling of 0.223 (100 slots out of 449 activities).
- **Focused, not spread across areas.** At α = 0.7 a top 5 covers 1.4 areas on average (area diversity 0.28). The ranking puts the child's priority area first by design. Within that area the activities still differ (intra-list diversity 0.442, more than SBERT alone).
- **SBERT alone repeats itself.** Only 50 distinct activities across the 20 children, and lower novelty and personalisation. Similar profiles produce similar queries, so the same activities come back.

## Method

Each measure uses the top 5 of all 20 held-out children (11 tune, 8 test and the content-gap child).

| Measure | Definition | Range |
|---|---|---|
| Intra-list diversity | Mean of 1 − cosine similarity between the SBERT vectors of each pair of activities in a child's top 5, averaged over children | 0 (identical) upwards |
| Area diversity | Distinct developmental areas in a child's top 5, divided by 5, averaged over children | 0.2 (one area) to 1.0 |
| Catalogue coverage | Activities in at least one child's top 5, divided by the 449 Published activities | 0 to 0.223 here (100 slots) |
| Novelty | Mean over every slot of −log2(share of children whose top 5 contains that activity) | 0 to 4.32 bits (log2 20) |
| Personalisation | 1 − mean share of top-5 activities two children have in common, over all pairs; also over pairs in the same age band only | 0 (identical lists) to 1 |

With no usage history, "popular" for novelty means "recommended to many of these 20 children".

## Results

| Ranking | Intra-list diversity | Area diversity | Distinct activities | Coverage | Novelty (bits) | Personalisation (all pairs) | Personalisation (same age band) |
|---|---|---|---|---|---|---|---|
| SBERT-only | 0.398 | 0.390 | 50 | 0.111 | 3.038 | 0.897 | 0.895 |
| α = 0.0 | 0.426 | 0.530 | 79 | 0.176 | 3.872 | 0.974 | 0.743 |
| **α = 0.7** | **0.442** | **0.280** | **96** | **0.214** | **4.242** | **0.996** | **0.962** |
| α = 1.0 | 0.531 | 0.280 | 93 | 0.207 | 4.182 | 0.993 | 0.933 |

How to read it:

- **α = 0.7 against SBERT alone:** higher on every measure except area diversity.
- **α = 0 against α = 0.7:**
  - α = 0 spreads the top 5 across more areas (0.53);
  - but children in the same age band get more similar lists (0.743): with no rule priority, a child's own milestones and concerns matter less.
- **α = 1.0:** the highest intra-list diversity, because it ranks by priority alone and ignores how closely each activity matches the profile.
- **Low area diversity is intended.** Recommending mostly in the area the rules flag is the point of the rule engine. It is a trade-off: a child flagged in one area sees few activities from other areas. Explore (#194) lets caregivers browse every area.

## Limitations

- **20 constructed children.** The measures describe these profiles, not real use.
- **Coverage is capped** at 100 of 449 activities by the number of slots, so it says more about repetition than about how much of the catalogue a real user base would see.
- **Novelty without usage data** measures repetition across these children only.
- **Not relevance.** A ranking can be varied and still unhelpful; read these with the nDCG results in [eval_v2_results.md](eval_v2_results.md) and [eval_v2_statistics.md](eval_v2_statistics.md).

## Reproducing

From `backend/`, with the provenance check passing:

```
python manage.py evaluate_alpha_grid --check-provenance
python manage.py evaluate_beyond_accuracy --markdown
```

The code is `recommendations/beyond_accuracy.py` and `recommendations/management/commands/evaluate_beyond_accuracy.py`.
