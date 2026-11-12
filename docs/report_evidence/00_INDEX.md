# Report evidence pack: index

> Built 2026-11-12T22:16:39+03:00 at commit `1b4c11e`. Regenerate everything with `powershell -File scripts\report_evidence\run_all.ps1` from the repository root. Each page states the command, date and commit behind it.

Rules followed: facts come from a command, file and line, or query named on the page; anything that couldn't be verified says UNKNOWN. The database was only read: every row the scripts needed (fictional children, recommendations, the request transcript) was created inside a transaction that was rolled back. No secrets, real emails or names: they are `<redacted>`. Data is fictional.

## Answers by question

| # | Answer (short) | Page |
|---|---|---|
| 1a | Backend 649 tests, OK, 0 skipped locally; Flutter 190 passed. Latest CI on main: success. CI skips: {'Backend (Django, postgresql)': 3, 'Backend (Django, sqlite)': 4} (SBERT model absent in CI; PostgreSQL-only row-lock test on SQLite). | 01 |
| 1b | Windows 11 (10.0.26200); AMD Ryzen 5 5625U with Radeon Graphics; 7.4 GB RAM; Python 3.13.15; PostgreSQL 18.6; Flutter 3.47.4, Dart 3.13.3. pandas installed but not imported; torch only via sentence-transformers. Phone: UNKNOWN (UNKNOWN if not connected). | 02 |
| 1c | `python manage.py seed_milestones`; 25 of 133 verified; all held-out milestones listed with their flag; Published activities by area × age table. | 03 |
| 1d | `bytea` column (`BinaryField`), NumPy dot product; FAISS, pgvector and experta are not imported anywhere; reason quoted from PR #20. | 03 |
| 1e | α = 1.0 ranks every eligible Published activity (rank() calls retrieve(limit=None)); file and line given. | 03 |
| 1f | Full tune curve and per-profile test table; test nDCG@5 α = 0.7 0.836 vs SBERT-only 0.582; labels by one rater (the researcher), from repo docs; v1 document differs by design (54 activities). | 04 |
| 1g | Mean areas per top 5 at α = 0.7: 1.40; 96 distinct activities in the 20 top-5s (catalogue is 449, not 54); latency p50 63.1 ms, p95 82.5 ms, peak working set 580 MB, start-up 21.2 s. | 04, 05 |
| 1h | 22 screen files listed; offline cache = last batch per child in shared preferences; offline launch covered by widget tests; the "not a medical check" footer is not found; 16 phone screenshots in docs/evidence/e2e_2026-10-15. | 08 |
| 1i | https://github.com/Alysa-Gathoni/Nurtura; default branch main; tags sprint5-eval-v1, sprint6-explanations-v1, sprint9-eval-v2; 107 merged PRs; 107 closed issues; per-milestone table; contributors 1; AI co-author trailers 0, PR generated-by lines 15. | 08 |
| 1j | UNKNOWN: no reader-test responses or scorer output in the repository. | 08 |
| 2a | Activity and milestone inventories (CSV), heatmap, samples (activity, milestone, fictional child, recommendation row), preparation steps. | 03, 09 |
| 2b | Configuration table generated from the module constants and settings, each with file:line. | 03 |
| 2c | Three fictional profiles: rules fired with boosts, top five with similarity, priority, age weight and score, explanation text. | 06 |
| 2d | Five 300-dpi figures with their CSVs and computed one-line insights; grade-0 sources by area and age band. | 04, 09 |
| 2e | Test inventory (838 tests) and requirement coverage: {'Done (with a stated deviation)': 5, 'Done': 37, 'Partial': 6, 'Done (built); evidence pending': 3}. | 01 |
| 2f | Register → verify → log out → log in → privacy consent → create child → record milestone → POST and GET recommendations → completion → feedback, all in a rolled-back transaction; rows read back. | 07 |

## Pages

| File | Covers | Script | Generated | Commit |
|---|---|---|---|---|
| `01_tests_and_requirements.md` | 1a, 2e, requirement coverage | `scripts/report_evidence/tests_and_ci.py` | 2026-11-12T22:14:14+03:00 | 1b4c11e |
| `02_environment.md` | 1b | `scripts/report_evidence/environment.py` | 2026-11-12T21:49:30+03:00 | 1b4c11e |
| `03_catalogue_dataset_config.md` | 1c, 1d, 1e, 2a, 2b | `scripts/report_evidence/catalogue_and_config.py` | 2026-11-12T21:55:30+03:00 | 1b4c11e |
| `04_evaluation.md` | 1f, 1g (coverage, areas per top 5), 2d data | `scripts/report_evidence/evaluation.py` | 2026-11-12T21:57:21+03:00 | 1b4c11e |
| `05_latency.md` | 1g (latency, memory, start-up) | `scripts/report_evidence/latency.py` | 2026-11-12T21:58:59+03:00 | 1b4c11e |
| `06_explanation_examples.md` | 2c | `scripts/report_evidence/explanation_examples.py` | 2026-11-12T22:02:27+03:00 | 1b4c11e |
| `07_workflow_transcript.md` | 2f | `scripts/report_evidence/workflow_transcript.py` | 2026-11-12T22:04:04+03:00 | 1b4c11e |
| `08_mobile_and_repository.md` | 1h, 1i, 1j | `scripts/report_evidence/mobile_and_repo.py` | 2026-11-12T22:16:08+03:00 | 1b4c11e |
| `09_figures.md` | 2d figures, 2a heatmap | `scripts/report_evidence/make_figures.py` | 2026-11-12T22:11:08+03:00 | 1b4c11e |

The commit is the one checked out when the page was generated; the scripts themselves are added by this pull request.

## Raw outputs (`raw/`)

- `raw/activities_inventory.csv`
- `raw/activity_frequency_alpha_0.7.csv`
- `raw/alpha_curve.csv`
- `raw/alpha_grid_markdown.txt`
- `raw/ci_runs.json`
- `raw/ci_skips.json`
- `raw/configuration.csv`
- `raw/dataset_samples.json`
- `raw/engine_mentions.json`
- `raw/environment.json`
- `raw/explanation_profiles.json`
- `raw/explanation_rules_fired.csv`
- `raw/explanation_top5.csv`
- `raw/exploratory_top5.csv`
- `raw/grade0_sources.csv`
- `raw/grade_distribution.csv`
- `raw/latency_runs.csv`
- `raw/latency_summary.json`
- `raw/milestones_github.csv`
- `raw/milestones_inventory.csv`
- `raw/mobile_screens.csv`
- `raw/per_profile_test.csv`
- `raw/published_by_domain_age.csv`
- `raw/rank_grade_matrix.csv`
- `raw/repository.json`
- `raw/requirement_coverage.csv`
- `raw/test_inventory.csv`
- `raw/tests_backend_log.txt`
- `raw/tests_flutter_log.jsonl`
- `raw/tests_summary.json`
- `raw/workflow_rows.json`
- `raw/workflow_transcript.json`

## Figures (`figures/`, 300 dpi)

- `figures/alpha_curve.png`
- `figures/grade_distribution.png`
- `figures/per_profile_test_ndcg5.png`
- `figures/published_heatmap.png`
- `figures/rank_grade_matrix.png`

## UNKNOWN items

- `02_environment.md:18`: | Phone | UNKNOWN, Android UNKNOWN (SDK UNKNOWN) | `adb shell getprop` |
- `08_mobile_and_repository.md:120`: Exported responses or scorer output (CSV, JSON, XLSX or TXT among them): none. **UNKNOWN**: no reader-test responses or scorer output are in the repository (the test and the caregiver sessions have no
