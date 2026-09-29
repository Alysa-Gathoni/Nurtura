# Nurtura activity data

Developmental activities that the Nurtura recommender draws from.

> **Do NOT fabricate developmental activities or claim unverified sources. All entries must be traceable to WHO, CDC, UNICEF, Montessori, or Pathways.org guidance.**

## Workflow

```
data/raw/*.csv  ──►  scripts/clean_activities.py  ──►  data/processed/*.csv
 (hand-curated)      (validate + standardise)          (used by the backend)
```

1. Add a new batch as its own CSV under `raw/` (e.g. `activities_batch4.csv`), continuing the `activity_id` numbering from the previous batch.
2. Run the cleaning script over **all** batches together, so duplicates are caught across batches:
   ```
   cd data/scripts
   python clean_activities.py "../raw/activities_batch*.csv" ../processed/activities_clean.csv
   ```
   (or `make seed-data` from the repo root). The script expands the wildcard itself, so the same command works in PowerShell.
3. Fix every `[REJECTED]` row in the **raw** file it came from and re-run until the summary shows all rows valid. Never edit files in `processed/` by hand.

Exit codes: `0` all rows valid, `1` one or more rows rejected, `2` usage/file error.

## Schema

The first ten columns are required. `content_status` and `source_url` are optional in raw batches and always present in the processed file.

| Column | Description |
|---|---|
| `activity_id` | Unique ID in the format `ACT-0000`, e.g. `ACT-0001` |
| `activity_name` | Short name of the activity |
| `developmental_domain` | Controlled vocabulary (below) |
| `recommended_age_range` | Controlled vocabulary (below) |
| `developmental_goal` | What skill the activity supports |
| `required_materials` | Materials needed; use `None` if nothing is required |
| `difficulty_level` | Controlled vocabulary (below) |
| `activity_description` | Step-by-step instructions for the caregiver, in our own words |
| `cultural_relevance` | How it fits Kenyan/local contexts (materials, language, family) |
| `source` | Controlled vocabulary (below) |
| `content_status` | *Optional.* Controlled vocabulary (below); defaults to `Draft` |
| `source_url` | *Optional.* Link to the specific guidance document (`http://` or `https://`); defaults to empty |

Any field containing a comma **must** be wrapped in double quotes, otherwise the columns shift. The cleaning script rejects rows with the wrong number of fields. Writing the file with Python's `csv` module or a spreadsheet's "Save as CSV" handles this automatically.

## Controlled vocabularies

Values are matched case-insensitively and rewritten to the canonical spelling below; anything else is rejected.

- **developmental_domain**: `Cognitive`, `Language`, `Motor`, `Sensory`, `Socio-Emotional`
- **recommended_age_range**: `Prenatal`, `0-3 months`, `3-6 months`, `6-12 months`, `12-18 months`, `18-24 months`, `24-36 months`
- **difficulty_level**: `Beginner`, `Intermediate`, `Advanced`
- **source**: `WHO`, `CDC`, `UNICEF`, `Montessori`, `Pathways.org`
- **content_status**: `Draft`, `Under Review`, `Published`. Activities go through the admin review workflow before they are recommended, so new batches should normally be `Draft`.

## What the cleaning script checks

- All required columns present in the header, and a value in every required field
- `activity_id` format (`ACT-0000`)
- Controlled-vocabulary values for domain, age range, difficulty, source and content status
- `source_url`, when given, is an `http(s)` link
- Duplicate `activity_id` across **all** input batches (case-insensitive)
- Duplicate (`activity_name`, `developmental_domain`) pair across all batches (case- and whitespace-insensitive)
- Unknown extra columns are reported as a warning and not copied to the output
- Wrong field count (usually an unquoted comma)
- Whitespace: trims ends and collapses repeated spaces in every field

Each rejected row is reported with its file, line number and every problem found; the rest of the batch is still processed.

## Batch status

| File | Rows | Notes |
|---|---|---|
| `raw/activities_batch1.csv` | 8 (`ACT-0001`–`ACT-0008`) | Initial sample. Descriptions are original wording. The `source` tag names the organisation whose guidance covers the activity type; the specific guidance documents still need to be cited (no `source_url`). |
| `raw/activities_batch2.csv` | 16 (`ACT-0009`–`ACT-0024`) | Mixed sources (CDC, Pathways.org, Montessori, UNICEF, WHO); no `source_url` yet. |
| `raw/activities_batch3.csv` | 14 (`ACT-0025`–`ACT-0038`) | All CDC, with `source_url` pointing to the CDC *Milestone Moments* booklet. |

Every activity is loaded as `Draft` and must pass admin review, including checking its source, before it is published.
