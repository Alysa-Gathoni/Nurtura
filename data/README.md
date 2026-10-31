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
4. Load the processed file into the database:
   ```
   cd backend
   python manage.py seed_activities            # add --dry-run to preview
   ```
   `make seed-data` runs steps 2 and 4 together. Loading is safe to repeat: rows are matched on `activity_id` and updated, never duplicated. New activities are always created as **Draft**, whatever the CSV's `content_status` says, and must be reviewed and published in the Django admin. Re-loading keeps the status set in the admin, except that an Under Review or Published activity whose content changed goes back to Draft for re-review. If any row is invalid, nothing is written.

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
| `raw/activities_batch1.csv` | 8 (`ACT-0001`–`ACT-0008`) | Initial sample. Descriptions are original wording. Each has a `source_url` to the specific guidance (#154). |
| `raw/activities_batch2.csv` | 15 (`ACT-0009`–`ACT-0024`) | Mixed sources (CDC, Pathways.org, UNICEF, WHO), each with a `source_url` (#154). `ACT-0021` was removed (#160). |
| `raw/activities_batch3.csv` | 14 (`ACT-0025`–`ACT-0038`) | All CDC, with `source_url` pointing to the CDC *Milestone Moments* booklet. |
| `raw/activities_batch4.csv` | 16 (`ACT-0039`–`ACT-0054`) | 11 Socio-Emotional, 6 Prenatal, plus Language, Sensory and Cognitive, filling the gaps found by the retrieval preview. Sources and `source_url` values as in the CSV. |
| `raw/activities_batch5.csv` | 196 (`ACT-0055`–`ACT-0254`) | Brings every age and area to at least 7 activities, including pregnancy Cognitive and Motor (#156). Four were removed (#160). Each follows a specific recommendation on its `source_url`, written in our own words. All `Draft` until reviewed. |
| `raw/activities_batch6.csv` | 200 (`ACT-0255`–`ACT-0454`) | A second large batch (#158): 26 for pregnancy and 29 for each age from birth to 36 months. Each follows one specific page on its `source_url`, written in our own words. All `Draft` until reviewed. |

Every activity is loaded as `Draft` and must pass admin review, including checking its source, before it is published.

### Source links added (#154, 30 Oct 2026)

`ACT-0001`–`ACT-0024` had a source organisation but no link. Each now links to the page or document its content follows, opened and checked on 30 Oct 2026:

| Link | Organisation | Activities |
|---|---|---|
| CDC *Learn the Signs. Act Early.* milestone pages (`cdc.gov/act-early/milestones/<age>.html`, "Tips and activities") | CDC | 0003, 0005, 0008, 0010, 0012, 0016, 0018, 0019, 0021, 0022, 0023, 0024 |
| WHO/UNICEF *Care for Child Development* counselling cards (`unicef.org/media/91181/file/4-CCD-Counselling-Cards.pdf`) | WHO or UNICEF | 0004, 0007, 0013, 0020 |
| WHO *Nurturing Care Practice Guide*, antenatal section (`nurturing-care.org/.../PG-handout1.pdf`) | WHO | 0002, 0009 |
| Pathways.org activity and guidance pages | Pathways.org | 0001, 0006, 0011, 0014, 0015, 0017 |

Where no page from the tagged organisation covered the activity, the `source` was corrected to the organisation whose guidance does: 0002 UNICEF → WHO; 0007 Montessori → WHO; 0008 WHO → CDC; 0012, 0016, 0019, 0022 Montessori → CDC; 0015 CDC → Pathways.org; 0021 and 0024 Pathways.org → CDC. Pathways.org advises supporting a new walker's trunk rather than holding their hands, while CDC suggests letting the baby hold your hands, so 0024 follows CDC. Re-loading these returns them to Draft for re-review.

### Batch 5 sources (#156, 30 Oct 2026)

Each of the 200 activities follows a specific recommendation on one of these pages, all opened and read on 30 Oct 2026. Nothing is copied: the wording, materials and Kenyan notes are ours.

| Source | Pages | Activities |
|---|---|---|
| CDC | *Learn the Signs. Act Early.* milestone pages at 2, 4, 6, 9 and 15 months and 1, 18, 2, 30 and 3 years ("Tips and activities") | 100 |
| Pathways.org | Sensory activities 0–18 months; household-item activities; tummy time guide; comforting a crying baby; activities to encourage walking; toddler coordination skills; animal walks; water play; Cup in the Bath; Monkey See, Monkey Do; Baby See, Baby Do | 51 |
| UNICEF | WHO/UNICEF *Care for Child Development* counselling cards; UNICEF Parenting: what to eat when pregnant, second and third trimester guides, how music affects your baby's brain | 32 |
| WHO | *Nurturing Care Practice Guide* (antenatal care); physical activity in pregnancy; daily iron and folic acid in pregnancy; nutrition counselling during pregnancy | 17 |

Pregnancy activities are about the parent's actions that support the baby: nutrition for the baby's brain and spine, a smoke-free home, safe physical activity at a talking pace, rest, support, and talking, singing and touch. They give no medical doses: supplements are taken "as the health worker advises".

### Batch 6 sources (#158, 30 Oct 2026)

Each of the 200 activities follows a specific recommendation on one of these pages, all opened and read on 30 Oct 2026. Nothing is copied: the wording, materials and Kenyan notes are ours.

| Source | Pages | Activities |
|---|---|---|
| Pathways.org | 126 single activity pages under `pathways.org/activities/…`, one per activity, each naming its age band | 126 |
| CDC | *Steps to a Healthier Me and Baby-to-Be* planner (13); milestone pages at 2 years, 30 months and 3 years (16); *Positive Parenting Tips* for infants, toddlers 1–2 and toddlers 2–3 (9); physical activity in pregnancy (3) | 41 |
| UNICEF | WHO/UNICEF *Care for Child Development* participant manual (14); 21 learning activities for babies and toddlers (11); what to avoid when pregnant (5); playtime anytime (3) | 33 |

Pathways.org activities sit in the age band the page gives (its 0–2 and 2–4 month bands map to 0–3 months, 4–6 to 3–6, 6–9 and 9–12 to 6–12, 12–15 and 15–18 to 12–18). No Pathways activity was moved to an older band. Pregnancy activities give no medical advice beyond the source: they point the parent to the health worker.

Names were checked against batches 1 to 5, so there are no repeats. CDC pages refuse automated link checks (HTTP 403) but open normally in a browser.

| Age | Cognitive | Language | Motor | Sensory | Socio-Emotional | Total |
|---|---|---|---|---|---|---|
| Prenatal | 15 | 11 | 13 | 9 | 12 | 60 |
| 0–3 months | 13 | 13 | 13 | 13 | 13 | 65 |
| 3–6 months | 13 | 13 | 13 | 13 | 12 | 64 |
| 6–12 months | 14 | 13 | 13 | 13 | 12 | 65 |
| 12–18 months | 13 | 14 | 13 | 13 | 12 | 65 |
| 18–24 months | 13 | 13 | 13 | 12 | 12 | 63 |
| 24–36 months | 14 | 13 | 14 | 13 | 13 | 67 |

Counts are for all 449 activities in the CSVs, after the removals below (#160).

### Source check and removals (#160, 30 Oct 2026)

Every Draft activity was checked against the text of its `source_url`. Seven did not match their page closely enough:

| Activity | Outcome |
|---|---|
| `ACT-0200` Float or Sink? | Kept. The link now goes to the Pathways.org *Float or Sink?* activity (18–24 months), which describes it. |
| `ACT-0216` Watering-Can Play | Reworked as *Funnel and Cup Water Play*, following the CDC 2-year tip "Let your child play with … plastic containers, spoons, or a funnel in the tub". Source changed from Pathways.org to CDC. |
| `ACT-0021` Retelling a Simple Story | Removed. No source page covers retelling, and the nearest CDC tip is already `ACT-0232`. |
| `ACT-0062` Getting a Simple Toy Basket Ready | Removed. The source only says to prepare the home for the baby. |
| `ACT-0072` Dancing to Family Music | Removed. The WHO fact sheet does not mention dancing. |
| `ACT-0080` Calm Time in Light and Shade | Removed. The UNICEF page says nothing about sun or shade, and its pillow tip is already `ACT-0074`. |
| `ACT-0220` Splashing in Puddles | Removed. No source page mentions puddles. |

Removed IDs are not reused. `seed_activities` does not delete rows, so a database seeded earlier keeps them as `Draft`, where they are never recommended. `ACT-0021` was one of the 54 activities in the `sprint5-eval-v1` evaluation, which stays reproducible from that tag. Pregnancy Sensory now has 9 activities; every other age and area has at least 11.

## Guideline milestone catalogue

`reference/developmental_milestones.csv` lists the developmental milestones the rule engine uses to decide when a milestone is due. It is reference data, not caregiver-facing content.

| Column | Description |
|---|---|
| `milestone_key` | Unique key, e.g. `CDC-12M-LA-01` (source, age, domain, number) or `WHO-MO-06` |
| `source` | `CDC` or `WHO` |
| `expected_age_months` | Age by which the guideline expects the milestone |
| `domain` | `Socio-Emotional`, `Language`, `Cognitive` or `Motor`. The guidelines have no Sensory category |
| `description` | The milestone |
| `source_reference` | Citation |
| `notes` | How the expected age was derived, and any caveats |

Sources:

- **CDC** *Learn the Signs. Act Early.* milestone checklists, 2022 revision (Zubler et al., *Pediatrics* 2022;149(3):e2021052138): 127 milestones at 2, 4, 6, 9, 12, 15, 18, 24, 30 and 36 months. Each is reached by most children (75% or more) by that age. CDC's Social/Emotional, Language/Communication, Cognitive and Movement/Physical domains map to Socio-Emotional, Language, Cognitive and Motor.
- **WHO** Multicentre Growth Reference Study, Motor Development Study (*Acta Paediatrica* Suppl 2006;450:86-95): 6 gross motor milestones. The expected age is the end of the WHO window of achievement (99th percentile).

The entries were written from these publications and **must each be checked against the source document**. Load them with `python manage.py seed_milestones` (also part of `make seed-data`); every entry starts unverified. An administrator marks entries verified in the Django admin (**Reference milestones**, "Mark selected milestones as verified"). Re-loading keeps the verified flag unless an entry's content changed, in which case it is marked unverified for re-checking.

## Access, privacy and ethics

- **Open, published sources only.** Activities are written in our own words from published WHO, CDC, UNICEF, Montessori and Pathways.org guidance, each with its source (and, where available, a link). The milestone catalogue cites the CDC 2022 checklists and the WHO Motor Development Study. No licensed or restricted dataset is used, and nothing needs an access agreement.
- **Not yet fully verified.** 25 of the 133 catalogue milestones have been checked against the source documents: the 6 WHO ones and the 19 CDC ones used in the evaluation. The other 108 are still to check (see the guideline section above).
- **No personal data in the repository.** Caregiver accounts, child profiles, milestones and feedback live only in the running database, which is never committed (`.env` and local databases are gitignored). Test accounts made during development and end-to-end runs are deleted afterwards.
- **Caregivers agree to a privacy notice first** (#136). [docs/privacy_notice.md](../docs/privacy_notice.md) says what is stored, why, who sees it and that it's kept until the caregiver deletes it. The version agreed to and the time are stored on the account.
- **Signing in with Google keeps only the email.** Continue with Google (#130) uses the Google account's verified email to find or create the account; the name and photo Google also sends are not stored.
- **Caregivers can erase their data** (#134). Deleting an account in the app removes the account and everything linked to it (children, milestones, developmental profiles, recommendations, completions, ratings, sign-in codes and trusted phones) at once. A single child's profile can also be deleted, with its records.
- **Evaluation data uses constructed children.** The held-out children in `evaluation/heldout_labels.csv` and the sample children are realistic but hypothetical profiles built from real catalogue milestones. No real child's data was used, and the relevance labels are the researcher's own judgements.
- **Studies with people are anonymous.** The explanation reader test and the planned caregiver evaluation record no names: readers are R1–R5, forms are anonymous, verbal or written consent is asked first, people can stop at any time, and responses are kept out of the repository (see `docs/explanation_reader_test.md`).
- **To confirm with the client:** how responsibility for protecting caregivers' data is divided between Nurtura and Webmasters Kenya once SOFIA hosts it (IR-10).
