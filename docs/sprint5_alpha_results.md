# Sprint 5 results: choosing α for the weighted ranking

- **Result:** α = **0.7**, chosen on the tune set by the selection rule fixed before labelling. `RANKING_ALPHA` is now 0.7.
- **Applies to:** git tag **`sprint5-eval-v1`** and the provenance below. Any change to the activities, rule weights, ranking settings, milestone catalogue, embeddings or labels means these numbers no longer apply.
- **Evaluated:** 2026-10-10, with `python manage.py evaluate_alpha_grid` (#37, #44).

## Provenance

| Item | Value |
|---|---|
| Labels | `data/evaluation/heldout_labels.csv`, git blob `47839d304f284c0009f2f9dd4b1b8faad4157c92` (labels commit `acf71dd`, #48) |
| Provenance sidecar | `data/evaluation/heldout_labels.provenance.json`, git blob `a271317420cbe10a28c2e16bca93518ea817ff7b`. It records the content hash of each of the 54 Published activities and the rule weights. |
| Activities | 54 Published, all embedded |
| Milestone catalogue | 133 milestones, sha256 `cde95da5dc2d7819a68603e3161a565617716c2b38d2f8a2c7e17f20990558a6` |
| Embedding model | `all-MiniLM-L6-v2`, 384 dimensions; model files sha256 `457f7e5e77fac1c5a85b53f291dcc661e8205458e98be0ea7323e404141cf32b` |
| Stored vectors | sha256 `fbd28f654e81e752bbdfde74c86f87d227ecd00ee97221792690709c0d3c1127` |
| Sheet rows | sha256 `2b30b724e192c70a75f1da5d43e206a3bb8fd60b89bbe225660001a1a3f5f6f7` |

The evaluation checks the live state against the sidecar each time it runs; for this run, it matched. The 19 catalogue milestones the held-out children use were checked against CDC's current milestone pages and marked verified. The `verified` flag isn't part of the provenance, because the rules don't read it.

## Set-up

- **Children:** 20 held-out sample children (`backend/recommendations/heldout.py`), separate from the 7 development children. Each is built from real CDC milestones or caregiver concerns and interests.
- **Split:** fixed before labelling: **11 tune**, **8 test** and **1 content-gap child** (H17), who is reported separately.
- **Labels:** 205 (child, activity) rows, the pooled top 5 of every ranking evaluated, graded 0/1/2 by the researcher.
  - Labelling was blind: the rows were shuffled, and no scores, ranks or domains were shown.
  - All 205 rows are labelled, so no top-5 candidate in any ranking is unlabelled.
  - There is **one rater**, so no inter-rater agreement is reported.
- **Metrics:** precision@3 and @5 counting grade ≥ 1 and grade 2, and nDCG@3 and @5 (gain 2^grade − 1).
- **Rankings compared:**
  - **SBERT-only:** raw cosine similarity between the profile query and each activity. No rule priority, no age weighting.
  - **α = 0:** similarity × age weight.
  - **α = 1:** rule priority × age weight.
  - **α = 0.7:** the chosen hybrid, age weight × (0.3 · similarity + 0.7 · rule priority).

### What α = 1 ranks

α = 1 ranks **every eligible activity**, not a shortlist from retrieval. "Eligible" means every Published activity with an embedding for the current model, after the prenatal/postnatal filter; for these children that is all 54 Published activities.

- `rank()` and the evaluation both call `retrieve(limit=None)`, which returns the whole eligible pool.
- At α = 1, the score is age weight × rule priority. Ties are broken by age fit, then activity ID.
- So at α = 1, similarity plays no part in choosing candidates or ordering them.
- The one link to the embedding step is eligibility: an activity without an embedding isn't a candidate at any α. All 54 were embedded.

## The selection rule (fixed before labelling)

1. For each α in 0.0, 0.1, …, 1.0, compute the mean nDCG@5 over the **tune** children only.
2. Every α within **0.02** of the best mean qualifies.
3. Choose the qualifying α closest to the midpoint of the smallest and largest qualifying α. If two are equally close, take the lower.

## Tune set (11 children): the full curve

| Ranking | P@3 ≥1 | P@5 ≥1 | P@3 =2 | P@5 =2 | nDCG@3 | nDCG@5 |
|---|---|---|---|---|---|---|
| SBERT-only | 0.758 | 0.618 | 0.242 | 0.182 | 0.505 | 0.491 |
| α = 0.0 | 0.939 | 0.873 | 0.455 | 0.400 | 0.694 | 0.737 |
| α = 0.1 | 0.939 | 0.909 | 0.545 | 0.455 | 0.756 | 0.799 |
| α = 0.2 | 0.909 | 0.927 | 0.545 | 0.473 | 0.762 | 0.825 |
| α = 0.3 | 0.909 | 0.945 | 0.606 | 0.491 | 0.809 | 0.861 |
| α = 0.4 | 0.909 | 0.945 | 0.697 | 0.527 | 0.852 | **0.887** |
| α = 0.5 | 0.909 | 0.927 | 0.667 | 0.527 | 0.835 | 0.877 |
| α = 0.6 | 0.939 | 0.909 | 0.667 | 0.527 | 0.844 | 0.872 |
| **α = 0.7 (chosen)** | 0.939 | 0.909 | 0.667 | 0.527 | 0.844 | 0.873 |
| α = 0.8 | 0.939 | 0.891 | 0.667 | 0.509 | 0.844 | 0.855 |
| α = 0.9 | 0.939 | 0.873 | 0.667 | 0.491 | 0.844 | 0.838 |
| α = 1.0 | 0.970 | 0.873 | 0.697 | 0.527 | 0.894 | 0.882 |

- **Best mean nDCG@5:** 0.887, at α = 0.4. The α values within 0.02 of it are **0.4, 0.5, 0.6, 0.7 and 1.0**.
- **Chosen α:** the midpoint of 0.4 and 1.0 is 0.7, which qualifies, so **α = 0.7** was chosen.
- **A plateau, not a peak.** From α = 0.4 to 1.0, mean nDCG@5 stays between 0.838 and 0.887. On tune, the ranking is not sensitive to the exact α in that range.
- **The choice depends on α = 1.0.** α = 0.8 and 0.9 don't qualify, but α = 1.0 does, which stretches the range to 0.4–1.0. **Without α = 1.0, the qualifying range would be 0.4–0.7, the midpoint 0.55, and the rule would have chosen α = 0.5** (0.5 and 0.6 are equally close, so the lower one). The rule was fixed before labelling, so α = 0.7 stands.

### Tune, per child (nDCG@3 / nDCG@5)

| Child | SBERT-only | α = 0 | α = 1 | α = 0.7 | α = 0.7 − SBERT-only (@3, @5) |
|---|---|---|---|---|---|
| H01 | 0.803 / 0.844 | 0.803 / 0.844 | 0.803 / 0.940 | 0.803 / 0.844 | +0.000, +0.000 |
| H05 | 0.302 / 0.519 | 0.766 / 0.797 | 0.766 / 0.735 | 0.766 / 0.921 | +0.464, +0.403 |
| H06 | 0.395 / 0.343 | 0.629 / 0.817 | 0.629 / 0.546 | 0.629 / 0.803 | +0.234, +0.459 |
| H08 | 0.649 / 0.633 | 0.951 / 0.958 | 1.000 / 0.868 | 1.000 / 0.868 | +0.351, +0.235 |
| H09 | 0.210 / 0.251 | 0.210 / 0.369 | 1.000 / 0.931 | 0.444 / 0.656 | +0.234, +0.404 |
| H11 | 0.646 / 0.565 | 0.453 / 0.556 | 1.000 / 1.000 | 1.000 / 1.000 | +0.354, +0.435 |
| H12 | 0.556 / 0.483 | 0.766 / 0.665 | 0.834 / 0.856 | 0.834 / 0.856 | +0.278, +0.373 |
| H13 | 0.951 / 0.896 | 1.000 / 0.931 | 1.000 / 1.000 | 1.000 / 0.938 | +0.049, +0.042 |
| H16 | 0.235 / 0.268 | 0.531 / 0.530 | 0.803 / 0.932 | 0.803 / 0.825 | +0.568, +0.557 |
| H19 | 0.255 / 0.202 | 0.687 / 0.752 | 1.000 / 0.893 | 1.000 / 0.893 | +0.745, +0.691 |
| H20 | 0.547 / 0.396 | 0.844 / 0.887 | 1.000 / 1.000 | 1.000 / 1.000 | +0.453, +0.604 |

Each ranking compared with SBERT-only, counting children improved / tied / worse on tune:

| | nDCG@3 | nDCG@5 |
|---|---|---|
| α = 0.7 | 10 / 1 / 0 | 10 / 1 / 0 |
| α = 0 | 8 / 2 / 1 | 9 / 1 / 1 |
| α = 1 | 10 / 1 / 0 | 11 / 0 / 0 |

## Test set (8 children)

α = 0.7 was chosen before the test children were scored. **α = 0 and α = 1 are shown as ablations only.** They played no part in selection, and they don't replace the chosen α.

| Ranking | P@3 ≥1 | P@5 ≥1 | P@3 =2 | P@5 =2 | nDCG@3 | nDCG@5 |
|---|---|---|---|---|---|---|
| SBERT-only | 0.708 | 0.700 | 0.292 | 0.300 | 0.441 | 0.452 |
| α = 0 (ablation) | 0.958 | 0.975 | 0.792 | 0.775 | 0.860 | 0.873 |
| α = 1 (ablation) | 0.958 | 0.850 | 0.583 | 0.575 | 0.735 | 0.726 |
| **α = 0.7 (chosen)** | **1.000** | **0.925** | **0.625** | **0.675** | **0.789** | **0.814** |

### Test, per child (nDCG@3 / nDCG@5)

| Child | SBERT-only | α = 0 (ablation) | α = 1 (ablation) | α = 0.7 | α = 0.7 − SBERT-only (@3, @5) | On nDCG@5 |
|---|---|---|---|---|---|---|
| H02 | 1.000 / 0.903 | 1.000 / 0.903 | 0.844 / 0.887 | 0.844 / 0.887 | −0.156, −0.016 | worse |
| H03 | 0.453 / 0.327 | 1.000 / 1.000 | 0.568 / 0.410 | 0.803 / 0.711 | +0.350, +0.384 | improved |
| H04 | 0.333 / 0.333 | 1.000 / 1.000 | 0.844 / 0.653 | 0.844 / 0.756 | +0.510, +0.422 | improved |
| H07 | 0.453 / 0.517 | 1.000 / 1.000 | 0.646 / 0.598 | 0.646 / 0.744 | +0.194, +0.227 | improved |
| H10 | 0.547 / 0.527 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 | +0.453, +0.473 | improved |
| H14 | 0.156 / 0.359 | 0.547 / 0.599 | 0.687 / 0.842 | 0.803 / 0.891 | +0.646, +0.531 | improved |
| H15 | 0.255 / 0.330 | 0.803 / 0.857 | 0.803 / 0.726 | 0.844 / 0.799 | +0.588, +0.469 | improved |
| H18 | 0.333 / 0.317 | 0.531 / 0.628 | 0.490 / 0.692 | 0.531 / 0.724 | +0.197, +0.407 | improved |

Each ranking compared with SBERT-only, counting children improved / tied / worse on test:

| | nDCG@3 | nDCG@5 |
|---|---|---|
| **α = 0.7 (chosen)** | **7 / 0 / 1** | **7 / 0 / 1** |
| α = 0 (ablation) | 7 / 1 / 0 | 7 / 1 / 0 |
| α = 1 (ablation) | 7 / 0 / 1 | 7 / 0 / 1 |

With 8 test children, **no significance claims are made**.

**On test, the α = 0 ablation scored higher than the chosen α**: mean nDCG@5 was 0.873 against 0.814. On tune it was the other way round (0.737 against 0.873). Rule priority helped more on the tune children than on the test children. In particular, α = 0 already ranks four test children perfectly (H03, H04, H07, H10). This is recorded as a limitation, not as grounds to change α: choosing α from test results would make the test set no longer held out.

### H02 and H17

- **H02** (expecting parent, Socio-Emotional concern; the only test child that got worse): prenatal activities all get the same age weight, so the only difference from SBERT-only is rule priority. It promoted the Socio-Emotional activities, moving ACT-0043 (graded 1) into the top 3 and pushing ACT-0002 (Language, graded 2), which SBERT ranked first, down to 5th.
- **H17** (content-gap child: Sensory, 20 months; reported separately): there is no Published Sensory activity for 18–24 months, so every Sensory candidate gets a reduced age weight. At α = 0.7, ACT-0034 (Motor, 18–24 months, graded 0) entered the top 3. On nDCG@5, SBERT-only scored 0.981, α = 0.7 scored 0.911 and α = 1 scored 0.946.

## Exploratory, decided after seeing the results: interest-driven children

This comparison was **not planned before labelling** and was chosen after seeing the results. It asks whether similarity helps when the child's need is expressed as an **interest**, rather than as a missed milestone. Apart from a small Sensory boost from the sensory-interest rule, an interest reaches the ranking only through the profile query, and so through similarity. It compares α = 0.7 with α = 1 (no similarity) for the three children whose profile is a Sensory concern plus interests.

| Child | Split | Interests | nDCG@3 (0.7 vs 1.0) | nDCG@5 (0.7 vs 1.0) | P@5 ≥1 (0.7 vs 1.0) |
|---|---|---|---|---|---|
| H07 | test | music, rattles | 0.646 vs 0.646 (+0.000) | 0.744 vs 0.598 (**+0.146**) | 1.000 vs 0.800 |
| H13 | tune | water play, sand | 1.000 vs 1.000 (+0.000) | 0.938 vs 1.000 (**−0.062**) | 0.800 vs 1.000 |
| H17 | gap | textures | 0.765 vs 1.000 (**−0.235**) | 0.911 vs 0.946 (**−0.035**) | 0.800 vs 0.800 |

The results go both ways:

- **H07:** similarity helped. It brought in ACT-0046 (Socio-Emotional, 3–6 months, graded 2) in place of ACT-0017 (Sensory, 12–18 months, graded 0).
- **H13:** similarity cost a little. ACT-0016 (graded 0) took 5th place from ACT-0004 (graded 1).
- **H17:** similarity cost more. ACT-0034 (graded 0) reached the top 3.

With three children, one in each split, **no conclusion is drawn**. The question is worth revisiting with more interest-driven profiles and more Sensory content.

## Limitations

- **Small numbers:** 11 tune and 8 test children, 54 activities, one rater and no agreement measure. The test results describe these eight children and don't support statistical claims.
- **Shallow pools:** only the union of each ranking's top 5 was labelled, so the metrics can't be extended beyond k = 5.
- **Profiles:** the profiles are realistic but constructed; they aren't real caregivers' children.
- **The rater designed the system:** the researcher who labelled also designed the system. Labelling was blind to rankings and scores, but not to how the system works.
- **Test favoured α = 0:** the test set preferred the α = 0 ablation, and the tune curve is flat from 0.4 to 1.0. The chosen value is a reasonable default, not an optimum. Caregiver feedback in Sprint 9 is the better test.

## Reproducing

From `backend/`, at tag `sprint5-eval-v1`, with the database state described under Provenance:

```
python manage.py evaluate_alpha_grid --markdown
```

The command checks the provenance sidecar and warns if anything differs. The ablation, per-child and exploratory tables above come from the same `heldout.rankings_for` and `evaluation.score_all` functions the command uses, applied to SBERT-only and α = 0, 0.7 and 1.
