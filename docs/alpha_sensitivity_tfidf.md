# α at the SBERT/TF-IDF mix: sensitivity check (#260)

> **Last updated: 2026-11-21.** Every figure is from `python manage.py alpha_sensitivity --markdown` (from `backend/`), run on 21 Nov 2026 on `main` after `sprint9-eval-v3` (β = 0.25). The plan below was written in issue #260 before the run.

## Question

α = 0.7 was chosen in v2 with SBERT-only retrieval. Since #250, retrieval mixes in TF-IDF (`similarity = 0.25 × SBERT + 0.75 × TF-IDF`), which changes the similarity scores. Is 0.7 still a sensible α?

## Plan (fixed before running)

- **A check, not a retune.** The app keeps α = 0.7: `sprint9-eval-v3` is frozen for the caregiver sessions.
- **Data:** the 20 constructed held-out children (11 tune, 8 test); every graded pair: `heldout_labels_v2.csv` plus `tfidf_extra.csv` (the researcher's grades).
- **What's scored:** mean nDCG@5 for α 0.0 to 1.0 at β = 0.25, on tune and test. Ungraded activities in a top 5 count as not relevant and are counted.
- **Reading:** apply the v2 α rule (every α within 0.02 of the best tune mean qualifies; the middle of that range wins). If 0.7 is within 0.02 of the best, the check supports it; otherwise it's a limitation for Chapter 5.

## Results

| α | Tune nDCG@5 | Test nDCG@5 | Ungraded (tune / test) |
|---|---|---|---|
| similarity-only | 0.474 | 0.604 | 0 / 0 |
| 0.0 | 0.704 | 0.769 | 5 / 5 |
| 0.1 | 0.773 | 0.873 | 2 / 1 |
| 0.2 | 0.820 | 0.892 | 0 / 0 |
| 0.3 | 0.821 | 0.893 | 0 / 0 |
| 0.4 | 0.820 | 0.893 | 0 / 0 |
| 0.5 | 0.814 | 0.882 | 0 / 0 |
| 0.6 | 0.822 | 0.882 | 0 / 0 |
| **0.7 (the app)** | **0.822** | **0.882** | 0 / 0 |
| 0.8 | 0.822 | 0.882 | 0 / 0 |
| 0.9 | 0.822 | 0.882 | 0 / 0 |
| 1.0 | 0.803 | 0.852 | 0 / 0 |

- **Best tune mean:** 0.822, reached at α 0.6 to 0.9.
- **Within 0.02 of it:** α 0.2 to 1.0. The rule's choice (the middle of that range) is **0.6**, which scores the same as 0.7 on tune and test.
- **α = 0.7 is tied for the best on tune** (0 below it), so the check supports keeping it.
- **Ungraded pairs** appear only at α 0.0 and 0.1 (13 slots), far from 0.7.

## What it shows

- **The curve is flat from α 0.2 to 0.9** (tune 0.814 to 0.822, test 0.882 to 0.893), as it was with SBERT only in v2. The exact α matters little once the rules have some weight.
- **Leaning entirely on either side is worse:** similarity alone (0.474 on tune) or almost no rule weight (α 0 to 0.1), or rules alone (α 1.0, 0.803).
- **No retune is needed.** α = 0.7 stays, and the decision is unchanged by adding TF-IDF.

## Limits

- **Same as v2:** 20 constructed children, one main rater, no significance claims.
- **One set of grades:** the extra pairs use the researcher's grades. The nurse's grades for them (`relevance_rater2`) aren't used here.
- **The test set** is reported for the record; the reading uses tune only.
