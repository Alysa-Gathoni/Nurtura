# Relevance labels for ranking evaluation

Sprint 5 tunes the ranking weight **α** against **hand-labelled relevance judgments**, never against the similarity or ranking score itself (α = 0 would then trivially win).

## Files

| File | What it is |
|---|---|
| `relevance_labels_template.csv` | Generated, unfilled template: one row per (sample child, eligible activity). |
| `relevance_labels.csv` | **Your filled-in labels** (create it by copying the template). The evaluation reads this file. |

Regenerate the template (for example after adding activities) with:

```
cd backend
python manage.py export_relevance_template --output ../data/evaluation/relevance_labels_template_new.csv
```

It refuses to overwrite an existing file unless you pass `--force`, so filled-in labels can't be lost by accident. Labels are matched on `sample_key` and `activity_id`, so existing labels stay valid when activities are added. Copy only the new rows across.

## The sample children

Seven sample children are defined in `backend/recommendations/samples.py`, each built from real catalogue milestones or caregiver concerns:

| `sample_key` | Child |
|---|---|
| `language-delay` | 6 months, not cooing yet (expected by 4 months) |
| `motor-delay` | 13 months, not pulling up to stand (expected by 12 months) |
| `cognitive-delay` | 10 months, not looking for dropped objects (expected by 9 months) |
| `socio-emotional-delay` | 10 months, not looking when name is called (expected by 9 months) |
| `sensory-concern` | 8 months, caregiver concerned about sensory development; likes water play and textures |
| `language-and-motor-delay` | 19 months, not yet saying 3+ words or walking alone |
| `expecting-parent` | due in about 3 months, Sensory concern (prenatal activities only) |

## How to label

For each row, judge **how useful this activity would be for this child right now** and enter in `relevance`:

| Value | Meaning |
|---|---|
| **2** | **Highly relevant**: directly supports the child's main need and suits their age. You would recommend it first. |
| **1** | **Partly relevant**: helpful but not targeted (a related skill), or a good activity that is a little young or old for the child. |
| **0** | **Not relevant**: doesn't address the child's needs, or isn't suitable at this age. |
| *(empty)* | Not labelled yet. Unlabelled activities count as not relevant, and the evaluation reports how many top results were unlabelled. |

Guidance:

- **Label before you look at any ranking output.** Judgments made after seeing the system's results tend to agree with them, which would inflate the scores.
- **Judge the child, not the domain tag.** An activity from another domain can still deserve a 1 or 2 if it genuinely helps; `expected_domains` is a hint, not the answer.
- **Age matters.** A good activity that is far too advanced, or unsafe at this age, is a 0.
- Use `notes` to record your reasoning for borderline cases, which is useful for the report.
- Label every row for a sample before moving on, so each child is judged consistently.

## Metrics

- **precision@5**: share of the top 5 ranked activities with relevance ≥ 1.
- **nDCG@5**: rewards putting the most relevant activities first. The gain is 2^relevance − 1 (a 2 is worth three times a 1) and the discount is log2(rank + 1). The result is divided by the best possible score from that child's labels. A child with no relevant labels has no nDCG and is left out of the average.

---

# Held-out set: choosing α (#37)

The seven sample children above are the **development set**. They were used to build and spot-check retrieval and ranking, so they are **not** used to choose α. α is chosen and tested on a separate **held-out set** of 20 children, defined in `backend/recommendations/heldout.py`.

## Files

| File | What it is |
|---|---|
| `heldout_labels.csv` | The held-out labelling sheet, generated once. Fill it in **in place**; the evaluation reads this file. |
| `heldout_labels.provenance.json` | Written with the sheet: a record of the state the pools were built from. Don't edit it. |

The sheet was generated with:

```
cd backend
python manage.py export_heldout_labels
```

It refuses to overwrite an existing file unless you pass `--force`, which would discard your labels.

### Provenance sidecar

When it writes the sheet, the command also writes `heldout_labels.provenance.json`, recording what the pools were built from:

- **activities**: every Published activity ID, with a SHA-256 hash of its content (name, domain, age range, goal, materials, difficulty, description, cultural relevance, source, source URL and status);
- **rule weights**: the rule engine's baseline, weights, upcoming window, sensory keywords, the not-a-delay list and the rule names;
- **ranking settings**: the age weights and the retrieval query settings;
- **catalogue version**: the number of reference milestones and a hash of their key, source, expected age, domain and description. The `verified` flag is deliberately left out, because the rules don't read it: marking milestones as verified isn't a change, but correcting an age or a description is;
- **embedding model**: model name, dimensions, a hash of the stored activity vectors, and a hash of the model files used to encode the profile query;
- **sheet rows**: a hash of the sheet's (child_id, activity_id) pairs.

`evaluate_alpha_grid` takes the same snapshot when it runs and prints a **warning** listing anything that differs, because the rankings may then not match the pools you labelled. The sidecar's `info` section (generation time, git commit, verified-milestone count) is for the record only and isn't compared.

## The held-out children and the split

Each child is built from real catalogue milestones (`ReferenceMilestone`) or caregiver concerns and interests. Every child has a fixed **split**, assigned before any labelling and never changed afterwards:

- **tune** (11 children): α is chosen on these only.
- **test** (8 children): used once, at the chosen α, to report the final result.
- **gap** (1 child, H17): a Sensory child aged 18–24 months, an age and domain with no Published content. H17 is labelled like the others but is **excluded from the tune and test metrics** and reported separately.

The tune/test split is stratified by domain (largest-remainder allocation of 60% to tune, random seed 2026). See `stratified_split()` in `heldout.py`.

## What gets labelled (pooling)

Labelling every activity for 20 children would take too long, so each child's sheet holds a **pool**. The pool is the union of the **top 5** activities (5 = the largest k reported) from:

- the **SBERT-only baseline**: cosine similarity only, with no rule priority and no age weighting; and
- the **weighted ranking** at every α from 0.0 to 1.0 in steps of 0.1.

Duplicates are removed and the pool is **shuffled** within each child (fixed seed), so row order says nothing about rank. The sheet shows no similarity scores, ranks, rule priorities or domains.

Because every ranking that is evaluated contributes its whole top 5, every activity that can appear in a reported top k is in the sheet. If a row is left blank, it counts as not relevant, and the evaluation reports how many such rows there were.

## Columns

| Column | Fill in? |
|---|---|
| `child_id`, `split`, `child_profile` | No: who the child is. `child_profile` is the plain-English description to judge against. |
| `activity_id`, `activity_name`, `activity_description`, `age_range` | No: the activity. |
| `relevance` | **Yes**: 0, 1 or 2 (scale below). |
| `notes` | Optional: your reasoning, especially for borderline cases. |
| `relevance_rater2` | Optional: a second rater's independent 0/1/2, for an agreement check. |

## The scale

0 = not relevant for this child, 1 = somewhat relevant (right area or age, but not a good match), 2 = clearly relevant and age-appropriate

| Value | Meaning |
|---|---|
| **2** | Clearly relevant and age-appropriate. |
| **1** | Somewhat relevant: the right area or the right age, but not a good match. |
| **0** | Not relevant for this child. |
| *(empty)* | Not labelled; counts as not relevant. |

## Labelling rules

- **Label blind.** Don't look at any ranking output (spot-check tables, the app, `evaluate_alpha_grid`) for these children until labelling is finished.
- **A domain tag alone doesn't make an activity relevant.** Judge what the activity actually asks the caregiver and child to do against the child's profile. That's why the sheet has no domain column.
- **Right topic, wrong age: 1 at most.** An activity that addresses the child's need but is meant for a clearly different age gets 1 at most (or 0 if it is unsafe or unusable at this age).
- **On-track children (H10, H20) have no specific need**, so judge age-appropriateness and general usefulness for a child of that age.
- Expecting-parent profiles (H01, H02) only ever show prenatal activities. Judge them against the parent's stated focus.
- `relevance_rater2` must be filled in without looking at `relevance`.

## How α is chosen (fixed before labelling)

1. For each α in 0.0, 0.1, …, 1.0, compute the **mean nDCG@5 over the tune children**. Only tune children are used.
2. Every α whose mean is within **0.02** of the best mean qualifies.
3. Take the **middle of that range**: the qualifying α closest to the midpoint of the smallest and largest qualifying α. If two are equally close, take the lower one.
4. Report the **full curve**: every α, with precision@3, precision@5, nDCG@3 and nDCG@5, plus the SBERT-only baseline for comparison.

The test children play no part in the choice.

## How the result is reported (test set)

At the chosen α, for each test child and on average:

- precision@3 and precision@5, at relevance ≥ 1 and at relevance ≥ 2, and nDCG@3 and nDCG@5, for both the hybrid ranking and the SBERT-only baseline;
- the **per-child difference** (hybrid minus SBERT-only) for each metric; and
- the **count of test children improved, tied or worse** on nDCG@5 (the selection metric). A child with no relevant labels has no nDCG and is counted separately.

With 8 test children, no significance claims are made. The gap child (H17) is reported separately in the same way. If `relevance_rater2` has been filled in for some rows, the simple agreement between the two raters is reported for those rows: the exact match rate, and the match rate on relevant/not relevant at ≥ 1 and at ≥ 2.

## Metrics on this set

- **precision@k at ≥ 1** (and **at ≥ 2**): the share of the top k with relevance of at least 1 (or 2).
- **nDCG@k**: as above (gain 2^relevance − 1, discount log2(rank + 1)), normalised by the best possible DCG@k from that child's labels. A child with no relevant labels has no nDCG and is left out of the averages.
- k = 3 and k = 5.

## Tie-breaks in the ranking

Equal scores are broken deterministically:

- α < 1: higher raw similarity first, then activity ID.
- α = 1 (rule priority only): **better age fit first** (the higher age weight), **then activity ID**. Similarity is deliberately not used here, so the α = 1 end of the curve has no semantic signal.
- SBERT-only baseline: similarity order (ties keep a stable order).

## Unlabelled candidates

`evaluate_alpha_grid` counts, for every ranking (SBERT-only and each α), the top-5 candidates with no label, by split. While **any** is unlabelled:

- the chosen α is marked **provisional** if any of them belong to tune children; and
- the **final test numbers (and the gap child's) are not printed**.

Every row in the sheet is in some ranking's top 5, so this means every row must be labelled.

## Running the evaluation

```
cd backend
python manage.py evaluate_alpha_grid [--labels ../data/evaluation/heldout_labels.csv] [--markdown]
```

The children are created in a transaction that is rolled back, so they are never saved.
