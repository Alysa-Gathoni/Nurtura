# Experiment: a learned ranker (#183)

> **Last updated: 2026-11-04.** The plan and the decision rule below were written before the learned ranker was run on the labels. Results are added under [Results](#results).

## Question

Can a model learned from the held-out labels rank activities better than the hand-set formula `age_weight × ((1−α)·similarity + α·priority)` with α = 0.7?

The formula fixes how the signals combine and tunes one number. A learned ranker uses the same signals as **features** and learns from the labels how much each one matters.

## Plan (fixed before running)

**Features** for each (child, activity) pair, all already computed by the system:

| Feature | From |
|---|---|
| SBERT similarity (raw cosine) | SBERT |
| SBERT similarity, normalised within the child's candidates (0–1) | SBERT |
| Rule priority of the activity's area (0–1) | Rule engine |
| Age weight (1, 0.7, 0.5, 0.25 or 0.1) | Age rule |
| Top area (1 if the activity's area has the highest priority) | Rule engine |
| Difficulty (0 Beginner, 1 Intermediate, 2 Advanced) | Activity |

**Model:** multinomial logistic regression on the relevance grade (0, 1 or 2), with standardised features and C = 1.0. Each candidate is scored by its expected gain, P(grade 1) × 1 + P(grade 2) × 3, which matches nDCG's gain of 2^grade − 1, and candidates are ranked by that score. No setting is tuned.

**Data:**
- **Training:** the labelled pairs of the 11 **tune** children in `heldout_labels_v2.csv`, the same children α was chosen on.
- **Testing:** the 8 **test** children, used once. The content-gap child (H17) is reported separately, as before.
- **Unlabelled pairs:** the learned ranker may put activities in a test top 5 that nobody has labelled. They are exported as a blind, shuffled sheet and graded by the researcher **before** any test figures are read. Until then, the results are marked provisional.
- **Leave-one-child-out on tune:** to check the model isn't simply memorising, it is also trained on 10 tune children and scored on the 11th, in turn.

**Compared on the same labels:** SBERT-only, α = 0.7 (the app), and the learned ranker. Metrics: nDCG@5, nDCG@3, precision@5 (grade ≥ 1 and grade 2), and children improved, tied or worse.

**Also reported:** the learned weights (standardised), showing how much each signal matters.

## Decision rule (fixed before running)

The learned ranker would replace the formula only if **all three** hold on the **test** children, with every top-5 activity labelled:

1. Mean nDCG@5 is at least **0.02 higher** than α = 0.7's.
2. **More test children improve than get worse** against α = 0.7.
3. Leave-one-child-out on tune doesn't fall below α = 0.7's tune nDCG@5 (so it generalises rather than memorising).

Otherwise α = 0.7 stays, and the result is reported as it is.

**Even if it is met,** switching changes the app's ranking, so the evaluation would have to be re-frozen. That decision belongs to the researcher, before the caregiver sessions or not at all.

## Results

> Run on 2026-11-06 with `python manage.py evaluate_learned_ranker --extra-labels ../data/evaluation/learned_ranker_extra.csv --markdown`, once every top-5 activity of the learned ranker was graded.

**Extra grades.** The learned ranker put 13 pairs in a top 5 that the v2 sheet doesn't grade: 10 on the first run, then 3 more after the tune-child grades among them were added to the training data. The researcher graded all 13 blind; they are in `data/evaluation/learned_ranker_extra.csv`. The model was finally trained on **149 labelled pairs** of the 11 tune children (grade 0: 21, grade 1: 58, grade 2: 70).

### Test set (8 children)

| Ranking | P@3 ≥1 | P@5 ≥1 | P@3 =2 | P@5 =2 | nDCG@3 | nDCG@5 |
|---|---|---|---|---|---|---|
| SBERT-only | 0.833 | 0.850 | 0.458 | 0.400 | 0.608 | 0.582 |
| **α = 0.7 (the app)** | **1.000** | **1.000** | **0.792** | **0.725** | **0.853** | **0.836** |
| Learned ranker | 0.958 | 0.950 | 0.708 | 0.625 | 0.755 | 0.737 |

| Child | SBERT-only | α = 0.7 | Learned | Learned vs α = 0.7 |
|---|---|---|---|---|
| H02 | 0.903 | 0.887 | 0.887 | tied |
| H03 | 0.217 | 0.548 | 0.548 | tied |
| H04 | 0.673 | 0.760 | 0.760 | tied |
| H07 | 0.799 | 1.000 | 1.000 | tied |
| H10 | 0.815 | 1.000 | 0.476 | worse |
| H14 | 0.244 | 0.815 | 0.913 | improved |
| H15 | 0.559 | 0.774 | 0.540 | worse |
| H18 | 0.446 | 0.903 | 0.774 | worse |

Against α = 0.7: 1 improved, 4 tied, 3 worse. With this few children, no significance claims are made.

### Leave one child out on tune (11 children)

| Ranking | nDCG@3 | nDCG@5 |
|---|---|---|
| SBERT-only | 0.549 | 0.548 |
| α = 0.7 | 0.722 | 0.736 |
| Learned ranker | 0.748 | 0.734 |

### Content-gap child (H17)

The learned ranker and α = 0.7 give the same top 5 (nDCG@5 0.686; SBERT-only 0.903).

### Learned weights

Standardised, towards grade 2 over grade 0:

| Feature | Weight |
|---|---|
| Age weight | +1.232 |
| Rule priority | +0.593 |
| SBERT similarity | +0.382 |
| SBERT similarity, normalised | −0.360 |
| Top area | +0.359 |
| Difficulty | −0.182 |

Age fit matters most, then rule priority, then text similarity: the same order as the formula, which gives guideline knowledge (age and rules) more weight than similarity. The two similarity features largely cancel, as they carry the same information.

### Decision

| Condition | Met |
|---|---|
| Test nDCG@5 at least 0.02 above α = 0.7 | no (0.737 against 0.836) |
| More test children improve than get worse | no (1 against 3) |
| Leave-one-out tune nDCG@5 not below α = 0.7's | no (0.734 against 0.736) |

**α = 0.7 stays.** With 149 labelled pairs, the learned model doesn't combine the signals better than the hand-set formula; it agrees on half the test children and loses on three. The formula's structure (age weight multiplying a mix of similarity and priority) already encodes what the model learns, without needing data to estimate it. A learned ranker may pay off once caregiver feedback provides far more labels; that is future work.
