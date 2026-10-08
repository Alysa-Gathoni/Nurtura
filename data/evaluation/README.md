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
