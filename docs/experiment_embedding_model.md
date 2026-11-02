# Experiment: a search-trained embedding model (#172)

> **Last updated: 2026-11-02.** The plan and the decision rule below were written before the comparison was run. Results are added under [Results](#results) once the extra pairs are labelled.

## Question

Does `multi-qa-MiniLM-L6-cos-v1` rank activities better than the current `all-MiniLM-L6-v2`?

- `all-MiniLM-L6-v2` was trained to judge whether two sentences mean the same thing.
- `multi-qa-MiniLM-L6-cos-v1` was trained on question-to-answer search: a short query finding a longer passage. That is the shape of Nurtura's task, where a profile query looks for activity descriptions.
- The two models are the same size (384 dimensions, about 90 MB), so a switch wouldn't change memory, speed or hosting needs.

## Plan (fixed before running)

- **Data:** the frozen v2 held-out evaluation (`sprint9-eval-v2`): the same 20 children, splits and labels.
- **What is compared:** only the two rankings fixed in advance, each with both models:
  - **SBERT-only**: is the semantic search itself better?
  - **α = 0.7**: is what the app shows better?
- **α is not re-tuned** for the candidate.
- **Extra labels:** the candidate may put activities in a top 5 that nobody has labelled. They are exported as a blind, shuffled sheet and graded by the researcher on the same 0/1/2 scale before any comparison figures are read.
- **The app is not changed.** The candidate's vectors exist only inside a transaction that is rolled back.

Command (from `backend/`):

```
python manage.py compare_embedding_model --export-unlabelled ../data/evaluation/model_comparison_extra.csv
# grade the exported sheet with label_heldout.html, then:
python manage.py compare_embedding_model --extra-labels ../data/evaluation/model_comparison_extra.csv --markdown
```

## Decision rule (fixed before running)

The candidate is adopted only if **all three** hold on the **test** children, with every top-5 activity labelled:

1. Mean nDCG@5 at **α = 0.7** is at least **0.02 higher** than with the current model (the same margin as the α rule).
2. Mean nDCG@5 for **SBERT-only** is higher than with the current model.
3. At α = 0.7, **more test children improve than get worse** on nDCG@5.

Otherwise the current model stays, and the result is reported as it is, including a negative result.

**Adopting it means re-freezing.** The app would re-embed all activities with the new model. The provenance would then differ from `sprint9-eval-v2`, so the change would be recorded and tagged as a new frozen state. That should happen before the caregiver sessions, or not at all, so the sessions test the system reported in Chapter 5.

## Results

*Not run yet.*
