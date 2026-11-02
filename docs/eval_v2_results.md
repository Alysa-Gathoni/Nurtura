# Held-out evaluation v2: the 449-activity pool

- **Result:** at α = **0.7**, the app's setting, test nDCG@5 is **0.836**, against **0.582** for SBERT alone. 7 of the 8 test children improved and 1 was worse.
- **α is unchanged at 0.7.** The selection rule fixed before labelling chose α = 1.0 on the tune set. That choice comes from how ties are broken at α = 1.0, not from better ranking (see [Why α = 1.0 tops the tune curve](#why-α--10-tops-the-tune-curve)), so α = 0.7 is kept and reported. This departs from the rule and is stated as such.
- **Applies to:** git tag **`sprint9-eval-v2`** and the provenance below. The v1 result (54 activities, nDCG@5 0.814) is in [sprint5_alpha_results.md](sprint5_alpha_results.md) and stays reproducible from `sprint5-eval-v1`.
- **Evaluated:** 2026-11-02, with `python manage.py evaluate_alpha_grid --markdown --report-alpha 0.7` (#168, #170).

## Provenance

| Item | Value |
|---|---|
| Labels | `data/evaluation/heldout_labels_v2.csv`, git blob `e7ab725ee5b50696cc7b1e0d2074488bd418f989` |
| Provenance sidecar | `data/evaluation/heldout_labels_v2.provenance.json` (format 2), git blob `c5cb52330a878e680682c03e44225122715ad59f`. For each Published activity it hashes the name, goal, description, area, age band and status. |
| Activities | 449 Published, all embedded |
| Milestone catalogue | 133 milestones, sha256 `cde95da5dc2d7819a68603e3161a565617716c2b38d2f8a2c7e17f20990558a6` (unchanged from v1) |
| Embedding model | `all-MiniLM-L6-v2`, 384 dimensions; model files sha256 `457f7e5e77fac1c5a85b53f291dcc661e8205458e98be0ea7323e404141cf32b` (unchanged from v1) |
| Stored vectors | sha256 `6c23608cb4ff02fb9f3725a6117391a95ebfedbfee9121bdf1a85e6dbf4f5fbf` |
| Sheet rows | sha256 `3095d70aebbd0cb4f5c178054dc5b88c930f400dc6dea90283a1c8cb683fda47` |
| Rule weights, ranking settings | Unchanged from v1 |

The evaluation checks the live state against the sidecar each time it runs; for this run, it matched.

## Set-up

The protocol is v1's, applied to the current catalogue:

- **Children:** the same 20 held-out children, with the same fixed split: **11 tune**, **8 test** and **1 content-gap child** (H17), reported separately.
- **Pool:** the top 5 of SBERT-only and of every α from 0.0 to 1.0, de-duplicated and shuffled. **257 rows**, against 205 in v1: with 449 activities the rankings disagree more.
- **Labels:** graded 0/1/2 by the researcher, blind (no scores, ranks or areas shown).
  - 80 rows carried their v1 label, because the child, activity, name and description were unchanged. The researcher revised 4 of them while labelling (H06/ACT-0012 1→2, H07/ACT-0020 0→1, H10/ACT-0020 0→1, H16/ACT-0012 0→1).
  - 177 rows were new.
  - All 257 are labelled: 136 graded 2, 93 graded 1, 28 graded 0. No top-5 candidate in any ranking is unlabelled.
  - One rater, so no agreement is reported.
- **Metrics:** as in v1. Precision@3 and @5 counting grade ≥ 1 and grade 2, and nDCG@3 and @5 (gain 2^grade − 1).

## Tune set (11 children): the full curve

| Ranking | P@3 ≥1 | P@5 ≥1 | P@3 =2 | P@5 =2 | nDCG@3 | nDCG@5 |
|---|---|---|---|---|---|---|
| SBERT-only | 0.848 | 0.818 | 0.364 | 0.364 | 0.549 | 0.548 |
| α = 0.0 | 0.879 | 0.891 | 0.515 | 0.527 | 0.666 | 0.677 |
| α = 0.1 | 0.909 | 0.927 | 0.576 | 0.545 | 0.711 | 0.711 |
| α = 0.2 | 0.909 | 0.927 | 0.606 | 0.618 | 0.722 | 0.745 |
| α = 0.3 | 0.909 | 0.927 | 0.606 | 0.618 | 0.722 | 0.745 |
| α = 0.4 | 0.909 | 0.927 | 0.606 | 0.600 | 0.722 | 0.736 |
| α = 0.5 | 0.909 | 0.927 | 0.606 | 0.600 | 0.722 | 0.736 |
| α = 0.6 | 0.909 | 0.927 | 0.606 | 0.600 | 0.722 | 0.736 |
| **α = 0.7 (kept)** | 0.909 | 0.927 | 0.606 | 0.600 | 0.722 | 0.736 |
| α = 0.8 | 0.909 | 0.927 | 0.606 | 0.600 | 0.722 | 0.736 |
| α = 0.9 | 0.909 | 0.927 | 0.606 | 0.600 | 0.722 | 0.736 |
| α = 1.0 (rule's choice) | 0.970 | 0.909 | 0.788 | 0.673 | 0.878 | 0.829 |

- **A flat curve from 0.2 to 0.9.** Mean nDCG@5 stays between 0.736 and 0.745, so on tune the ranking is not sensitive to the exact α in that range.
- **The rule's choice:** best mean nDCG@5 is 0.829 at α = 1.0, and no other α is within 0.02 of it, so the rule chooses **α = 1.0**.

## Why α = 1.0 tops the tune curve

At α = 1.0 the score is age weight × rule priority, with no similarity term. Ties are broken by age fit and then by **activity ID** (`rank_candidates` in `recommendations/ranking.py`).

- With 54 activities (v1), few activities tied, so the tie-break hardly mattered.
- With 449, most activities in the child's top area and age band tie. The top 5 is then simply the **lowest-numbered** activities in that area and band.
- The lowest IDs are the original 54 hand-written activities (`ACT-0001` to `ACT-0054`). Over all 20 children, they fill **47 of the 100** top-5 places at α = 1.0, against **27 of 100** at α = 0.7, although they are 12% of the catalogue.

So the α = 1.0 score measures how well the first-written activities suit these children, not how well the system ranks. At α = 1.0 the embeddings play no part, and every child with the same top area and age band would get the same five ideas. For these reasons α = 0.7 is kept. It was fixed in advance by v1's rule, before any v2 labels existed.

**This is a departure from the selection rule.** The rule was fixed before labelling, and v2 does not follow its choice. The reason is given here, the rule's choice and its test result are reported below, and the decision is recorded so it can be judged.

## Test set (8 children): α = 0.7 against SBERT-only

| Child | α = 0.7 nDCG@5 | SBERT-only nDCG@5 | Difference | On nDCG@5 |
|---|---|---|---|---|
| H02 | 0.887 | 0.903 | −0.016 | worse |
| H03 | 0.548 | 0.217 | +0.331 | improved |
| H04 | 0.760 | 0.673 | +0.087 | improved |
| H07 | 1.000 | 0.799 | +0.201 | improved |
| H10 | 1.000 | 0.815 | +0.185 | improved |
| H14 | 0.815 | 0.244 | +0.571 | improved |
| H15 | 0.774 | 0.559 | +0.214 | improved |
| H18 | 0.903 | 0.446 | +0.456 | improved |
| **Mean** | **0.836** | **0.582** | **+0.254** | 7 improved, 0 tied, 1 worse |

All metrics, means over the 8 test children:

| Ranking | P@3 ≥1 | P@5 ≥1 | P@3 =2 | P@5 =2 | nDCG@3 | nDCG@5 |
|---|---|---|---|---|---|---|
| **α = 0.7** | 1.000 | 1.000 | 0.792 | 0.725 | 0.853 | **0.836** |
| SBERT-only | 0.833 | 0.850 | 0.458 | 0.400 | 0.608 | 0.582 |
| α = 1.0 (rule's choice, for the record) | 1.000 | 1.000 | 0.792 | 0.775 | 0.858 | 0.876 |

With this few children, no significance claims are made.

## Content-gap child (H17)

H17 is a Sensory child aged 18–24 months. In v1 that cell had no Published activity; it now has 12. H17 stays outside the tune and test means, as fixed in advance.

| Ranking | nDCG@3 | nDCG@5 |
|---|---|---|
| α = 0.7 | 0.687 | 0.686 |
| SBERT-only | 1.000 | 0.903 |

For H17, SBERT alone does better (−0.216 on nDCG@5 at α = 0.7). H17 has no milestone evidence, only a caregiver concern and interests, so the rule priority adds less, and the age weighting pulls in neighbouring age bands.

## Comparison with v1

| | v1 (`sprint5-eval-v1`) | v2 (`sprint9-eval-v2`) |
|---|---|---|
| Published activities | 54 | 449 |
| Rows labelled | 205 | 257 (80 carried, 177 new) |
| α (app setting) | 0.7, the rule's choice | 0.7, kept; the rule chose 1.0 |
| Test nDCG@5, α = 0.7 | 0.814 | 0.836 |
| Test nDCG@5, SBERT-only | 0.452 | 0.582 |
| Test children improved / tied / worse | 7 / 0 / 1 | 7 / 0 / 1 |

SBERT alone does better in v2 (0.452 → 0.582) because there are now several relevant activities in every area and age band to find. The ranking's gain over it is about the same (+0.36 in v1, +0.25 in v2).

## Limitations

- **Small and constructed:** 8 test children, all hypothetical profiles.
- **One rater,** who also designed the system, with no agreement measure. 80 labels were carried from v1.
- **The α decision departs from the rule fixed in advance,** for the reason given above.
- **The ID tie-break at α = 1.0** is a weakness of the ranking at that setting. It doesn't affect α = 0.7, where ties are broken by similarity.
- **Only the top 5 were labelled,** so the metrics can't be extended beyond k = 5.
