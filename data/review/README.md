# Content for review

## Which file to open

| You want | Open |
|---|---|
| **The caregiver wording of every activity's aim** | `plain_aims.csv`: one sheet, 449 rows, all approved |
| Activities whose area or age band the classifier doubts | `classifier_flags.csv` (60 rows, #181) |

## `plain_aims.csv`: caregiver wording of each activity's aim

One row per activity. In an explanation, `plain_aim` completes the sentence **"Its aim is to …"**. Until #190 the aims were in three sheets: the original 54 activities (#70; 53 rows since `ACT-0021` was removed in #160), batch 5 (#156) and batch 6 (#158). They are now combined, sorted by `activity_id`, with nothing else changed. All 449 rows are approved: the original 54 with reviewer edits to five (#70), batches 5 and 6 in #166.

Each aim:
- completes "Its aim is to …" in the **second person** ("your baby", "your child", "you"); pregnancy aims address the parent ("help you…") where the activity is about the parent's own health;
- uses **at most 20 words**;
- avoids **technical terms** such as "gross motor", "receptive language" or "sensory processing";
- uses **British spelling**;
- makes **no claim beyond the curated `developmental_goal`**. In particular, ACT-0051 doesn't imply that the caregiver punishes.

`developmental_goal` itself is unchanged. It feeds the embedding, so editing it would change the recommendations. `plain_aim` feeds nothing but the explanation text.

| Column | Meaning |
|---|---|
| `activity_id`, `activity_name`, `age_range`, `developmental_goal` | The activity, as stored |
| `plain_aim_draft` | The drafted aim |
| `rendered` | The sentence as it appears in an explanation |
| `words` | Word count (20 at most) |
| `notes` | Why the wording differs from the goal; "Judgement call" marks the ones most worth checking |
| `approved` | **For the reviewer:** `yes`, or blank |
| `reviewer_edit` | **For the reviewer:** your own wording, if you'd rather. It replaces the draft when loaded. |

### Loading the approved aims

From `backend/`:

```
venv/Scripts/python.exe manage.py load_plain_aims
```

It reads this sheet, validates every approved row (at most 20 words, a lower-case start, no final full stop) and updates `plain_aim` only: content status, the embeddings, the ranking and the evaluation's provenance are untouched. A new batch of ideas then carries the aim sentence in its explanations.

## `classifier_flags.csv`: labels the classifier doubts

Written by `python manage.py train_activity_classifier` (#181). Each row is an activity whose area or age band the cross-validated classifier predicted differently, with at least 70% confidence. A flag is a prompt to check against the activity's source, not a correction: many flagged activities fit two areas or two bands. Record the outcome in `reviewer_decision`. See [docs/activity_classifier_results.md](../../docs/activity_classifier_results.md).
