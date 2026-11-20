# TF-IDF alongside SBERT: comparison (#248)

> **Last updated: 2026-11-20 (β = 0.25 adopted, #250).** The plan and the decision rule were written (in issue #248 and in `compare_tfidf`) before the comparison was run. Every figure below is from the final run on 20 Nov 2026, after the 123 extra top-5 pairs were graded.

## Question

Does adding TF-IDF (word matching) to SBERT (meaning matching) rank activities better?

- **SBERT** turns text into numbers that capture meaning, so "babbling" and "sound games" can match.
- **TF-IDF** counts the words two texts share, weighting rare words more. It catches exact words, such as an interest ("animals", "blocks"), but nothing it doesn't literally see.
- **Both are compared by cosine similarity,** with the same child's needs sentence and the same activity text, so the only difference is how text becomes numbers.

## How it works

`similarity = β × SBERT cosine + (1 − β) × TF-IDF cosine`

- **β = 1** is SBERT only: the configuration evaluated at `sprint9-eval-v2`. At β = 1, TF-IDF isn't computed, and the provenance fingerprint is unchanged.
- **β = 0.25** is the app's setting since #250 (`RETRIEVAL_BETA`; see [Adopted](#adopted-β--025-250)).
- **β = 0** is TF-IDF only.
- **The rest of the ranking is unchanged:** `age_weight × ((1 − α) × similarity + α × priority)`, with α = 0.7.
- **TF-IDF settings:** fixed, not tuned. scikit-learn `TfidfVectorizer` with English stop words, sublinear term frequency, single words and L2 normalisation. It's fitted on every Published activity.
- **Not affected:** Explore search and feedback personalisation stay on SBERT.

## Plan (fixed before running)

- **Data:** the frozen v2 held-out evaluation (`sprint9-eval-v2`): 20 constructed children (11 tune, 8 test, 1 content-gap), with the researcher's labels.
- **What's compared:** β = 0, 0.25, 0.5, 0.75 and 1, each in two rankings:
  - **similarity-only:** is the search itself better?
  - **α = 0.7:** is what the app would show better?
- **α is not re-tuned.**
- **Rule for choosing β:** on the tune children at α = 0.7, take the β with the highest mean nDCG@5. It replaces β = 1 only if it's at least **0.02** higher; otherwise the app keeps SBERT only. The chosen β is reported once on the test children.
- **Ungraded activities** in a top 5 count as not relevant, so the extra pairs had to be graded before the result was final.

Command (from `backend/`):

```
python manage.py compare_tfidf --markdown --export-unlabelled ../data/evaluation/tfidf_extra.csv
# after grading the sheet with label_heldout.html:
python manage.py compare_tfidf --markdown --extra-labels ../data/evaluation/tfidf_extra.csv
```

## Results (final, 20 Nov 2026)

Every activity in every top 5 is now graded: the v2 sheet, plus the 123 extra pairs in `tfidf_extra.csv`, graded blind on 20 Nov 2026 by the researcher (`relevance`) and by the registered nurse who was the v2 second rater (`relevance_rater2`). The main figures use the researcher's grades, as v2 does.

**Why SBERT's own figures moved:** the extra grades don't touch SBERT's top 5s, but some of them are 2s. That raises the best possible score for those children, so SBERT's nDCG@5 falls a little (test at α = 0.7: 0.836 → 0.823). The provisional run on 19 Nov reproduced the published v2 figures exactly.

### Tune set (11 children), mean nDCG@5

| β | Similarity-only | α = 0.7 |
|---|---|---|
| 0 (TF-IDF only) | 0.417 | **0.872** |
| 0.25 | 0.474 | 0.822 |
| 0.5 | 0.499 | 0.782 |
| 0.75 | **0.537** | 0.741 |
| 1 (SBERT only) | 0.535 | 0.720 |

### Decision

- **Best on tune at α = 0.7:** β = 0 (TF-IDF only), 0.872, against 0.720 for SBERT only: a gain of **0.152**, well over the 0.02 needed.
- **So, by the rule fixed in advance, β = 0 is chosen.**
- **The app adopted β = 0.25, not β = 0** (#250; see [Adopted](#adopted-β--025-250)).

### Test set (8 children), mean nDCG@5, for the record

| β | Similarity-only | α = 0.7 |
|---|---|---|
| 0 (TF-IDF only) | 0.543 | **0.886** |
| 0.25 | 0.604 | 0.882 |
| 0.5 | **0.612** | 0.881 |
| 0.75 | 0.607 | 0.852 |
| 1 (SBERT only) | 0.577 | 0.823 |

**Test, per child, β = 0 against SBERT only (improved / tied / worse on nDCG@5):**
- similarity-only: 3 / 0 / 5;
- α = 0.7: 4 / 2 / 2.

With 8 children, no significance claims are made.

### Second rater

**Agreement on the 123 extra pairs:**
- The two raters gave the same grade to 93 of 123 pairs.
- Quadratic-weighted κ was 0.685, with a 95% bootstrap CI of [0.545, 0.798] (2,000 resamples).
- That's close to the v2 sheet's 0.661 ([eval_v2_statistics.md](eval_v2_statistics.md#agreement-between-raters-218)).

**The comparison rerun with the nurse's grades for the extra pairs** (the v2 pairs keep the researcher's grades), mean nDCG@5 at α = 0.7:

| β | Tune | Test |
|---|---|---|
| 0 (TF-IDF only) | 0.770 | 0.866 |
| 0.25 | **0.790** | **0.870** |
| 0.5 | 0.789 | **0.870** |
| 0.75 | 0.757 | 0.852 |
| 1 (SBERT only) | 0.732 | 0.823 |

- **Under the nurse's grades, the rule chooses β = 0.25** (0.790 against 0.732 on tune).
- **Both raters' grades lead to the same decision:** move away from SBERT only.
- **They differ on how far:** β = 0 under the researcher's grades and β = 0.25 under the nurse's. On test, β = 0 to 0.5 are within 0.005 of each other under both sets of grades.

## What it shows

- **The provisional result was wrong.** With the TF-IDF pairs counted as not relevant, the comparison favoured SBERT. Once they're graded, many turn out relevant: of the 123, the researcher graded 43 as 2, 57 as 1 and 23 as 0.
- **In the full ranking (α = 0.7), every mix with TF-IDF beats SBERT only,** on tune and on test, under both raters' grades.
- **The search on its own is mixed.** Similarity-only, TF-IDF alone is below SBERT on tune (0.417 against 0.535) and on test (0.543 against 0.577). The light mixes (β = 0.5 to 0.75) are roughly level with SBERT or slightly above it. So TF-IDF helps most in combination with the rule priority and age weight, not as a better search by itself.
- **Why that happens isn't tested.** One possibility: the query is a generated sentence whose fixed wording (focus areas, milestone names) TF-IDF matches literally, which may line up with the rule engine's priorities.

## Adopted: β = 0.25 (#250)

- **Setting:** `RETRIEVAL_BETA` defaults to 0.25, so `similarity = 0.25 × SBERT cosine + 0.75 × TF-IDF cosine`. α stays 0.7 and isn't re-tuned.
- **Why not β = 0, the rule's choice on the researcher's grades:**
  - β = 0.25 is the rule's choice on the nurse's grades.
  - On test it scores within 0.004 of β = 0 under both sets of grades (0.882 against 0.886 with the researcher's grades, 0.870 against 0.866 with the nurse's).
  - It keeps SBERT's matching by meaning, which helps when a profile and an activity share no words. With β = 0, SBERT would drop out of recommendations entirely.
  - So the choice is deliberate and recorded as such, not the pre-registered rule applied alone.
- **The figures for the app's configuration** (researcher's grades, every top-5 pair graded): tune nDCG@5 0.822 and test 0.882, against 0.720 and 0.823 for SBERT only on the same labels.
- **Provenance:**
  - The ranking fingerprint now includes the retrieval settings, recorded as `TFIDF_MIX_RANKING_VERSION` in `generation.py`.
  - `evaluate_alpha_grid --check-provenance` against the `sprint9-eval-v2` sidecar reports one expected difference: "ranking settings changed: retrieval".
  - Run with `RETRIEVAL_BETA=1`, it matches, and the v2 figures reproduce.
- **Still to do:** tag a new frozen evaluation state before the caregiver sessions.

## Limits

- **Same limits as v2:** 20 constructed children and one main rater; no significance claims.
- **The extra pairs were graded in a later session than the v2 sheet,** by the same two raters, blind to which ranking each pair came from. They weren't mixed in with the v2 pairs, so grading drift between the two sessions can't be ruled out.
- **The decision is far over the 0.02 line under both raters,** but the choice of β itself differs between them (0 against 0.25).
- **The query is a generated sentence** (age, focus areas, milestones not yet seen, interests). Much of its wording is fixed text, which TF-IDF matches literally, so TF-IDF may do better with free-text queries such as Explore searches. That isn't tested here.
