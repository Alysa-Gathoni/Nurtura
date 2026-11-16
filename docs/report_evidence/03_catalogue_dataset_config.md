# Catalogue, dataset and configuration

> Generated 2026-11-12T21:55:30+03:00 at commit `1b4c11e` by `backend\venv\Scripts\python.exe scripts\report_evidence\catalogue_and_config.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

## 1c. Milestone catalogue

- **Load command:** `python manage.py seed_milestones` (from `backend/`); default file `data/reference/developmental_milestones.csv` (`backend/profiles/management/commands/seed_milestones.py:26`). It validates every row before writing and matches on `milestone_key`.
- **Verified:** 25 of 133 catalogue milestones (`ReferenceMilestone.verified`; `raw/milestones_inventory.csv`).
- **Used by the held-out children:** 19 milestones (`heldout.milestone_keys()`), 19 of them verified:

| Milestone key | Verified |
|---|---|
| CDC-02M-MO-01 | True |
| CDC-02M-SE-04 | True |
| CDC-04M-CO-02 | True |
| CDC-04M-LA-02 | True |
| CDC-06M-MO-01 | True |
| CDC-06M-SE-03 | True |
| CDC-09M-SE-05 | True |
| CDC-12M-LA-01 | True |
| CDC-12M-LA-02 | True |
| CDC-15M-CO-02 | True |
| CDC-15M-MO-01 | True |
| CDC-15M-SE-05 | True |
| CDC-18M-CO-02 | True |
| CDC-18M-SE-02 | True |
| CDC-24M-LA-02 | True |
| CDC-24M-LA-03 | True |
| CDC-30M-CO-02 | True |
| CDC-30M-LA-01 | True |
| CDC-30M-MO-03 | True |

## Published activities by area and age band

449 Published activities ({'published': 449} by status). `raw/published_by_domain_age.csv`; heatmap in `figures/published_heatmap.png`.

| Area | Prenatal | 0-3 months | 3-6 months | 6-12 months | 12-18 months | 18-24 months | 24-36 months | Total |
|---|---|---|---|---|---|---|---|---|
| Cognitive | 15 | 13 | 13 | 14 | 13 | 13 | 14 | 95 |
| Language | 11 | 13 | 13 | 13 | 14 | 13 | 13 | 90 |
| Motor | 13 | 13 | 13 | 13 | 13 | 13 | 14 | 92 |
| Sensory | 9 | 13 | 13 | 13 | 13 | 12 | 13 | 86 |
| Socio-Emotional | 12 | 13 | 12 | 12 | 12 | 12 | 13 | 86 |

By source: {'Pathways.org': 181, 'WHO': 23, 'CDC': 167, 'UNICEF': 78}. With a source URL: 449 of 449. By batch (from `data/raw/activities.csv`): {'1': 8, '2': 15, '3': 14, '4': 16, '5': 196, '6': 200}.

## 1d. Storage and engine

- **Embeddings:** `recommendations_activityembedding.id` bigint, `recommendations_activityembedding.model_name` character varying, `recommendations_activityembedding.dimensions` smallint, `recommendations_activityembedding.text_hash` character varying, `recommendations_activityembedding.vector` bytea, `recommendations_activityembedding.updated_at` timestamp with time zone, `recommendations_activityembedding.activity_id` bigint (`information_schema.columns`). Vectors are float32 bytes in a `BinaryField` (`backend/recommendations/models.py:141`), compared with a NumPy dot product (`backend/recommendations/retrieval.py:131`).
- **FAISS / pgvector / experta imported by code:** faiss: no, pgvector: no, experta: no. Mentions in the repository (docs and comments): faiss: 1, pgvector: 0, experta: 3; listed in `raw/engine_mentions.json`.
- **Reason for the custom rule engine** (pull request text containing "experta", via `gh pr view`):
  - PR #20 (feat: implement rule engine core evaluator (FR-05)): "The core of the developmental-profiling rule engine (FR-05): a **custom IF-THEN engine** (the plan's documented fallback to `experta`, which is unmaintained and unlikely to install on Python 3.13). This PR is the **mechanism only**; the WHO/CDC/ASQ rules come in #18."
  - PR #20 (feat: implement rule engine core evaluator (FR-05)): "- **Additive adjustments.** Several delayed milestones in one domain add up, so a domain with more concerns ranks higher. There's no rule chaining, which is simpler than `experta` and enough for milestone-to-domain rules."

## 1e. Does α = 1.0 rank every eligible Published activity?

Yes. `rank()` calls `retrieve(child, limit=None, ...)` (`backend/recommendations/ranking.py:148`), and `limit=None` returns every eligible activity in similarity order (`backend/recommendations/retrieval.py:107`). Eligible means Published, embedded with the current model, and prenatal-only for pregnancies or postnatal-only otherwise (same function). The app's `generate()` uses `rank(child)` (`backend/recommendations/generation.py:165`). At α = 1.0, ties in priority × age weight are broken by age weight, then activity ID (`backend/recommendations/ranking.py:138`).

## 2a. Samples and preparation

Samples (`raw/dataset_samples.json`): one Published activity, one catalogue milestone, one fictional held-out child (H01) and the recommendation row generated for it inside a rolled-back transaction.

Preparation and validation steps:

| Step | Command / file |
|---|---|
| Activities loaded from CSV as Draft, all-or-nothing validation | backend/activities/management/commands/seed_activities.py |
| Plain-language aims loaded | backend/activities/management/commands/load_plain_aims.py |
| Review: Draft → Under Review → Published (only Published are recommended) | backend/activities/models.py |
| Embeddings precomputed; re-encoded only when the text hash changes | backend/recommendations/management/commands/embed_activities.py |
| Milestone catalogue loaded and validated | backend/profiles/management/commands/seed_milestones.py |
| Data files and their provenance | data/README.md |

## 2b. Configuration ("hyperparameters")

Every module constant in the recommendation path, plus the settings that affect results. Values are read from the code at run time. `raw/configuration.csv`.

| Setting | Value | Where |
|---|---|---|
| DOMAINS | tuple(Domain.values) | backend/profiles/rules/engine.py:19 |
| NOT_YET_DEFICIT | 10.0 | backend/profiles/rules/guidelines.py:29 |
| EMERGING_DEFICIT | 5.0 | backend/profiles/rules/guidelines.py:30 |
| UPCOMING_WINDOW_MONTHS | 3.0 | backend/profiles/rules/guidelines.py:34 |
| UPCOMING_WEIGHT | 2.0 | backend/profiles/rules/guidelines.py:35 |
| CONCERN_WEIGHT | EMERGING_DEFICIT | backend/profiles/rules/guidelines.py:38 |
| SENSORY_INTEREST_WEIGHT | 2.0 | backend/profiles/rules/guidelines.py:41 |
| NOT_A_DELAY_SIGNAL | {"WHO-MO-03"} | backend/profiles/rules/guidelines.py:56 |
| REFERRAL_MIN_NOT_YET | 1 | backend/profiles/rules/referral.py:22 |
| SOURCE | "CDC Learn the Signs. Act Early. (2022)" | backend/profiles/rules/referral.py:24 |
| FOCUS_THRESHOLD | 0.5 | backend/recommendations/retrieval.py:28 |
| DEFAULT_LIMIT | 10 | backend/recommendations/retrieval.py:29 |
| MAX_LIMIT | 50 | backend/recommendations/retrieval.py:30 |
| BRACKET_INDEX | {age_range: i for i, (age_range, _, _) in enumerate(AGE_BRACKETS)} | backend/recommendations/ranking.py:42 |
| SAME_BRACKET | 1.0 | backend/recommendations/ranking.py:48 |
| ONE_YOUNGER | 0.7 | backend/recommendations/ranking.py:49 |
| ONE_OLDER | 0.5 | backend/recommendations/ranking.py:50 |
| TWO_AWAY | 0.25 | backend/recommendations/ranking.py:51 |
| FURTHER | 0.1 | backend/recommendations/ranking.py:52 |
| RECOMMENDATIONS_PER_BATCH | 5 | backend/recommendations/generation.py:50 |
| MAX_PINNED | 2 | backend/recommendations/generation.py:51 |
| SHORT_DESCRIPTION_LENGTH | 160 | backend/recommendations/generation.py:52 |
| EXPLANATION_VERSION | "2" | backend/recommendations/explanations.py:46 |
| MAX_SENTENCES | 4 | backend/recommendations/explanations.py:47 |
| MAX_NAMED_MILESTONES | 3 | backend/recommendations/explanations.py:48 |
| MAX_GROUPS | 2 | backend/recommendations/explanations.py:49 |
| SUPPORT | dict(AREA, Sensory="sensory development") | backend/recommendations/explanations.py:59 |
| NOT_YET | "due-milestone-not-yet" | backend/recommendations/explanations.py:61 |
| EMERGING | "due-milestone-emerging" | backend/recommendations/explanations.py:62 |
| UPCOMING | "upcoming-milestone" | backend/recommendations/explanations.py:63 |
| MILESTONE_RULES | (NOT_YET, EMERGING, UPCOMING) | backend/recommendations/explanations.py:64 |
| MODEL_NAME | "all-MiniLM-L6-v2" | backend/recommendations/embeddings.py:14 |
| SIMILARITY_FLOOR | 0.5 | backend/recommendations/personalisation.py:31 |
| BOOST | 0.25 | backend/recommendations/personalisation.py:32 |
| PENALTY | 0.25 | backend/recommendations/personalisation.py:33 |
| MENTION_BOOST | 0.03 | backend/recommendations/personalisation.py:37 |
| MAX_NOTES | 2 | backend/recommendations/personalisation.py:38 |
| MAX_OPTIONS | 3 | backend/recommendations/options.py:27 |
| DIFFICULTY_ORDER | [Difficulty.BEGINNER, Difficulty.INTERMEDIATE, Difficulty.ADVANCED] | backend/recommendations/options.py:28 |
| CALM_WORDS | ("calm", "sooth", "gentle", "cuddle", "relax", "quiet", "settle") | backend/recommendations/options.py:29 |
| NO_MATERIALS | ("", "none") | backend/recommendations/options.py:30 |
| MIN_AGE_WEIGHT | 0.5 | backend/recommendations/browse.py:31 |
| QUICK_MAX_CHARS | 220 | backend/recommendations/browse.py:32 |
| DEFAULT_LIMIT | 30 | backend/recommendations/browse.py:33 |
| MAX_LIMIT | 100 | backend/recommendations/browse.py:34 |
| ENV_FLAG | "NURTURA_MODEL_WARMUP" | backend/recommendations/warmup.py:30 |
| DISABLED_VALUES | {"0", "false", "no", "off"} | backend/recommendations/warmup.py:31 |
| RANKING_ALPHA | 0.7 | backend/nurtura_backend/settings.py:265 (env RANKING_ALPHA) |
| SBERT_MODEL_PATH | all-MiniLM-L6-v2 | backend/nurtura_backend/settings.py:250 |
| DEFAULT_THROTTLE_RATES | {'login': '5/minute', 'two_factor': '10/minute', 'password_reset': '5/minute', 'account_delete': '5/minute'} | backend/nurtura_backend/settings.py:229 |
| TOKEN_LIFETIME | 30 days, 0:00:00 | backend/nurtura_backend/settings.py:213 |
| ranking_version() | da4d8bcfc4b96aa8275ddf6d450433ff66df8c6786952221e19cad800840de31 | backend/recommendations/generation.py:68 |
| RuleEngine baseline | 1.0 | backend/profiles/rules/engine.py:99 |
| Priority normalisation | max(0, raw) / top raw score (top area = 1.0) | backend/profiles/rules/engine.py:122 |
| Similarity normalisation | min-max over the child's pool | backend/recommendations/ranking.py:122 |
| Query template | 'Activities for <age phrase> to support <focus areas>. Still working on: ... Enjoys ...' | backend/recommendations/retrieval.py:73 |
| Embedding model size on disk | 91.6 MB; 384 dimensions | backend\models\all-MiniLM-L6-v2 |
