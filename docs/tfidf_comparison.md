# TF-IDF alongside SBERT: comparison (#248)

> **Last updated: 2026-11-19.** The plan and the decision rule were written (in issue #248 and in `compare_tfidf`) before the comparison was run. Every figure below is from that run. **The results are provisional:** 123 top-5 pairs aren't graded yet (see [What's still to do](#whats-still-to-do)).

## Question

Does adding TF-IDF (word matching) to SBERT (meaning matching) rank activities better?

- **SBERT** turns text into numbers that capture meaning, so "babbling" and "sound games" can match.
- **TF-IDF** counts the words two texts share, weighting rare words more. It catches exact words, such as an interest ("animals", "blocks"), but nothing it doesn't literally see.
- **Both are compared by cosine similarity,** with the same child's needs sentence and the same activity text, so the only difference is how text becomes numbers.

## How it works

`similarity = β × SBERT cosine + (1 − β) × TF-IDF cosine`

- **β = 1** is SBERT only: the evaluated configuration and the app's setting (`RETRIEVAL_BETA`). At β = 1, TF-IDF isn't computed, and the provenance fingerprint is unchanged.
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
- **Ungraded activities** in a top 5 count as not relevant, and the result stays provisional until they're graded.

Command (from `backend/`):

```
python manage.py compare_tfidf --markdown --export-unlabelled ../data/evaluation/tfidf_extra.csv
# after grading the sheet with label_heldout.html:
python manage.py compare_tfidf --markdown --extra-labels ../data/evaluation/tfidf_extra.csv
```

## Results (provisional, 19 Nov 2026)

**Sanity check:** at β = 1 the run reproduces the published v2 figures exactly (test nDCG@5 0.836 at α = 0.7, and 0.582 similarity-only; [eval_v2_results.md](eval_v2_results.md)).

### Tune set (11 children), mean nDCG@5

| β | Similarity-only | α = 0.7 |
|---|---|---|
| 0 (TF-IDF only) | 0.249 | 0.582 |
| 0.25 | 0.342 | 0.678 |
| 0.5 | 0.419 | 0.731 |
| 0.75 | 0.488 | **0.754** |
| 1 (SBERT only) | **0.548** | 0.736 |

### Decision

- **Best on tune at α = 0.7:** β = 0.75 (0.754), against 0.736 for SBERT only: a gain of **0.018**, just under the 0.02 needed.
- **So, by the rule fixed in advance, the app keeps SBERT only (β = 1).** Nothing in the app changes.

### Test set (8 children), mean nDCG@5, for the record

| β | Similarity-only | α = 0.7 |
|---|---|---|
| 0 (TF-IDF only) | 0.241 | 0.633 |
| 0.25 | 0.388 | 0.671 |
| 0.5 | 0.502 | 0.739 |
| 0.75 | 0.561 | 0.792 |
| 1 (SBERT only) | **0.582** | **0.836** |

### Ungraded pairs

TF-IDF puts activities in the top 5 that the v2 sheet never graded, because the sheet was built from SBERT rankings. They count as not relevant here, which is unfavourable to TF-IDF:

| β | Similarity-only (tune / test) | α = 0.7 (tune / test) |
|---|---|---|
| 0 | 39 / 31 | 19 / 12 |
| 0.25 | 32 / 23 | 13 / 10 |
| 0.5 | 22 / 15 | 6 / 8 |
| 0.75 | 15 / 7 | 1 / 4 |
| 1 | 0 / 0 | 0 / 0 |

In total there are 123 distinct pairs, including the content-gap child.

## What it shows so far

- **TF-IDF alone is much weaker than SBERT** (tune similarity-only 0.249 against 0.548, test 0.241 against 0.582). Even allowing for its ungraded pairs, word matching misses activities that mean the same thing in other words. That supports the proposal's choice of a semantic model.
- **Every bit of TF-IDF lowers the search alone** (similarity-only falls steadily as β falls).
- **Inside the full ranking, the gap closes.** The rule priority and age weight do much of the work, and a light mix (β = 0.75) scores close to SBERT on tune. It's slightly above on tune (+0.018) and below on test (0.792 against 0.836).
- **The tune decision is close to the line,** and β = 0.75 has one ungraded tune pair at α = 0.7. Grading the extra pairs could change the decision, so the result isn't final until then.

## What's still to do

1. **Grade** `data/evaluation/tfidf_extra.csv` (123 pairs, blind and shuffled) on the same 0/1/2 scale, with `label_heldout.html`. The nurse's grades cover only the v2 sheet.
2. **Rerun** with `--extra-labels`, and replace the provisional figures above.
3. **If the rule then chooses β < 1,** setting `RETRIEVAL_BETA` changes the ranking. That needs its own issue, a documented provenance note and a new frozen evaluation state.

## Limits

- **Same limits as v2:** 20 constructed children and one main rater; no significance claims.
- **The labels came from SBERT-based pools,** so until the extra pairs are graded the comparison favours SBERT.
- **The query is a generated sentence** (age, focus areas, milestones not yet seen, interests). Much of its wording is fixed text, which TF-IDF matches literally, so TF-IDF may do better with free-text queries such as Explore searches. That isn't tested here.
