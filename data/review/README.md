# Content for review

## `plain_aims_draft.csv`: caregiver wording of each activity's aim (#70)

These are drafts of `plain_aim` for the 54 Published activities. In an explanation, `plain_aim` completes the sentence **"Its aim is to …"**. Nothing has been loaded: every activity's `plain_aim` is blank until the drafts are approved, so explanations show no aim sentence yet.

Each draft:
- completes "Its aim is to …" in the **second person** ("your baby", "your child", "you");
- uses **at most 20 words** (the longest draft has 18);
- avoids **technical terms** such as "gross motor", "receptive language" or "sensory processing";
- uses **British spelling**;
- makes **no claim beyond the curated `developmental_goal`**. In particular, ACT-0051 doesn't imply that the caregiver punishes.

`developmental_goal` itself is unchanged. It feeds the embedding, so editing it would change the recommendations. `plain_aim` feeds nothing but the explanation text.

| Column | Meaning |
|---|---|
| `activity_id`, `activity_name`, `age_range`, `developmental_goal` | The activity, as stored |
| `plain_aim_draft` | The draft |
| `rendered` | The sentence as it would appear in an explanation |
| `words` | Word count (20 at most) |
| `notes` | Why the wording differs from the goal; "Judgement call" marks the ones most worth checking |
| `approved` | **For the reviewer:** `yes`, or leave blank |
| `reviewer_edit` | **For the reviewer:** your own wording, if you'd rather. It replaces the draft when loaded. |

Once the sheet is reviewed, the approved rows (with any reviewer edits) will be loaded in a separate change. The model's validator runs again on load: at most 20 words, a lower-case start and no final full stop.
