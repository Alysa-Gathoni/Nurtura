# Nurtura activity data

Developmental activities that the Nurtura recommender draws from.

> **Do NOT fabricate developmental activities or claim unverified sources. All entries must be traceable to WHO, CDC, UNICEF, Montessori, or Pathways.org guidance.**

## Workflow

```
data/raw/*.csv  ──►  scripts/clean_activities.py  ──►  data/processed/*.csv
 (hand-curated)      (validate + standardise)          (used by the backend)
```

1. Add or edit activities in a CSV under `raw/`, one batch per file (e.g. `activities_batch2.csv`).
2. Run the cleaning script:
   ```
   cd data/scripts
   python clean_activities.py ../raw/activities_batch1.csv ../processed/activities_clean.csv
   ```
   (or `make seed-data` from the repo root).
3. Fix every `[REJECTED]` row in the **raw** file and re-run until the summary shows all rows valid. Never edit files in `processed/` by hand.

Exit codes: `0` all rows valid, `1` one or more rows rejected, `2` usage/file error.

## Schema

Every column is required.

| Column | Description |
|---|---|
| `activity_id` | Unique ID, e.g. `ACT001` |
| `activity_name` | Short name of the activity |
| `developmental_domain` | Controlled vocabulary (below) |
| `recommended_age_range` | Controlled vocabulary (below) |
| `developmental_goal` | What skill the activity supports |
| `required_materials` | Materials needed; use `None` if nothing is required |
| `difficulty_level` | Controlled vocabulary (below) |
| `activity_description` | Step-by-step instructions for the caregiver, in our own words |
| `cultural_relevance` | How it fits Kenyan/local contexts (materials, language, family) |
| `source` | Controlled vocabulary (below) |

Any field containing a comma **must** be wrapped in double quotes, otherwise the columns shift. The cleaning script rejects rows with the wrong number of fields. Writing the file with Python's `csv` module or a spreadsheet's "Save as CSV" handles this automatically.

## Controlled vocabularies

Values are matched case-insensitively and rewritten to the canonical spelling below; anything else is rejected.

- **developmental_domain**: `Cognitive`, `Language`, `Motor`, `Sensory`, `Socio-Emotional`
- **recommended_age_range**: `Prenatal`, `0-3 months`, `3-6 months`, `6-12 months`, `12-18 months`, `18-24 months`, `24-36 months`
- **difficulty_level**: `Beginner`, `Intermediate`, `Advanced`
- **source**: `WHO`, `CDC`, `UNICEF`, `Montessori`, `Pathways.org`

## What the cleaning script checks

- All required columns present in the header, and a value in every required field
- Controlled-vocabulary values for domain, age range, difficulty and source
- Duplicate `activity_id` (case-insensitive)
- Duplicate (`activity_name`, `developmental_domain`) pair (case- and whitespace-insensitive)
- Wrong field count (usually an unquoted comma)
- Whitespace: trims ends and collapses repeated spaces in every field

Each rejected row is reported with its line number and every problem found; the rest of the batch is still processed.

## Batch status

| File | Rows | Notes |
|---|---|---|
| `raw/activities_batch1.csv` | 8 | Initial sample. Descriptions are original wording. The `source` tag names the organisation whose guidance covers the activity type; the specific guidance documents still need to be cited and checked before production use. |
