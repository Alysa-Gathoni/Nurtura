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

**First run (2026-11-04): provisional, no figures read.** The model was trained on 141 labelled pairs of the 11 tune children (grade 0: 21, grade 1: 55, grade 2: 65). Its top 5s include 10 pairs nobody has labelled (5 for tune children in the leave-one-out check, 5 for test children, none for H17). They are in `data/evaluation/learned_ranker_extra.csv`, blind and shuffled, to be graded before any results are printed.

```
cd backend
python manage.py evaluate_learned_ranker --extra-labels ../data/evaluation/learned_ranker_extra.csv --markdown
```
