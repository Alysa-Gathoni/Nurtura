# Report evidence pack: index

> Built 2026-11-21T22:33:26+03:00 at commit `48210e2`. Regenerate everything with `powershell -File scripts\report_evidence\run_all.ps1` from the repository root. Each page states the command, date and commit behind it.

Rules followed: facts come from a command, file and line, or query named on the page; anything that couldn't be verified says UNKNOWN. The database was only read: every row the scripts needed (fictional children, recommendations, the request transcript) was created inside a transaction that was rolled back. No secrets, real emails or names: they are `<redacted>`. Data is fictional.

## Answers by question

| # | Answer (short) | Page |
|---|---|---|
| 1a | Backend 714 tests, OK, 0 skipped locally; Flutter 200 passed. Latest CI on main: success. CI skips: {'Backend (Django, postgresql)': 3, 'Backend (Django, sqlite)': 5} (SBERT model absent in CI; PostgreSQL-only row-lock test on SQLite). | 01 |
| 1b | Windows 11 (10.0.26200); AMD Ryzen 5 5625U with Radeon Graphics; 7.4 GB RAM; Python 3.13.15; PostgreSQL 18.6; Flutter 3.47.4, Dart 3.13.3. pandas installed but not imported; torch only via sentence-transformers. Phone: SM-A145F (UNKNOWN if not connected). | 02 |
| 1c | `python manage.py seed_milestones`; 133 of 133 verified; all held-out milestones listed with their flag; Published activities by area × age table. | 03 |
| 1d | `bytea` column (`BinaryField`), NumPy dot product; FAISS, pgvector and experta are not imported anywhere; reason quoted from PR #20. | 03 |
| 1e | α = 1.0 ranks every eligible Published activity (rank() calls retrieve(limit=None)); file and line given. | 03 |
| 1f | Full tune curve and per-profile test table; test nDCG@5 α = 0.7 0.836 vs SBERT-only 0.582; labels by the researcher, with a second rater (registered nurse) on 257 rows: quadratic-weighted κ 0.661 [0.589, 0.718]; on the nurse's labels test nDCG@5 α = 0.7 0.737 vs SBERT-only 0.398; v1 document differs by design (54 activities). | 04 |
| 1g | Mean areas per top 5 at α = 0.7: 1.40; 96 distinct activities in the 20 top-5s (catalogue is 449, not 54); latency p50 33.8 ms, p95 65.1 ms, peak working set 603 MB, start-up 13.7 s. | 04, 05 |
| 1h | 22 screen files listed; offline cache = last batch per child in shared preferences; offline launch covered by widget tests; the "not a medical check" footer is not found; 16 phone screenshots in docs/evidence/e2e_2026-10-15. | 08 |
| 1i | https://github.com/Alysa-Gathoni/Nurtura; default branch main; tags pre-weekly-plan, sprint5-eval-v1, sprint6-explanations-v1, sprint9-eval-v2, sprint9-eval-v3, sprint9-eval-v3.1; 130 merged PRs; 130 closed issues; per-milestone table; contributors 1. | 08 |
| 1j | UNKNOWN: no reader-test responses or scorer output in the repository. | 08 |
| 2a | Activity and milestone inventories (CSV), heatmap, samples (activity, milestone, fictional child, recommendation row), preparation steps. | 03, 09 |
| 2b | Configuration table generated from the module constants and settings, each with file:line. | 03 |
| 2c | Three fictional profiles: rules fired with boosts, top five with similarity, priority, age weight and score, explanation text. | 06 |
| 2d | Five 300-dpi figures with their CSVs and computed one-line insights; grade-0 sources by area and age band. | 04, 09 |
| 2e | Test inventory (913 tests) and requirement coverage: {'Done (with a stated deviation)': 5, 'Done': 36, 'Partial': 6, 'Done (with a stated addition)': 1, 'Done (built); evidence pending': 3}. | 01 |
| 2f | Register → verify → log out → log in → privacy consent → create child → record milestone → POST and GET recommendations → completion → feedback, all in a rolled-back transaction; rows read back. | 07 |
| 3a | 14 models, 130 fields with type, null, blank, default, choices, constraints, indexes, foreign keys and on_delete; models match the migrations; Mermaid ER and class diagrams. | 10 |
| 3b | 43 endpoints with methods, view, permission and throttle; fictional examples from the workflow transcript. | 10 |
| 3c | Permissions observed by calling every endpoint and method as anonymous, own caregiver, other caregiver and administrator (58 rows). | 10 |
| 3d | 13 admin-registered models with columns, filters, search, actions and read-only fields; only active staff (Administrators) can enter. | 10 |
| 3e | 16 management commands with purpose, options and whether each writes. | 10 |
| 3f | Screens, tabs, navigation edges (Mermaid), API calls per service, and loading/empty/error handling per screen file. | 10 |
| 3g | The recommendation request in 15 steps, each with file and line. | 10 |
| 3h | 23 differences from the requirement text or the report, each with its evidence. | 10 |
| 3i | 88 pull requests merged since sprint6-explanations-v1. | 10 |
| 4a | 20 of 20 negative tests pass. | 11 |
| 4b | Authentication, roles, throttling, password validators, token lifetime, admin restriction, deletion, DEBUG, ALLOWED_HOSTS and secure-cookie settings with file references. | 11 |
| 4c | Python audit: 40 known vulnerabilities in 7 packages (black 26.5.1 -> 26.10.1, certifi 2026.7.22 -> 2026.10.18, djangorestframework 3.18.1 -> 3.18.2, filelock 4.0.4 -> 4.2.1, pyasn1 0.6.4 -> 0.6.5, setuptools 84.0.0 -> 84.1.0, virtualenv 21.13.0 -> 21.14.9), none upgraded here; Flutter pub outdated listed; secret scan: password/secret assignment with a literal 27; Django SECRET_KEY literal 1; no .env ever committed. | 11 |
| 4d | Consent recorded and enforced; no data export; cascading deletion; no soft delete. | 11 |
| 4e | No deployment files; nothing hosted (hosting details UNKNOWN); peak working set 603.0 MB, start-up 13.7 s; release APK signed with the debug key. | 11 |
| 5a | 2 open issue(s); 0 TODO/FIXME comments; known defects: none listed. | 12 |
| 5b | 59 stated limitations with file references. | 12 |
| 5c | 32 decisions from PR decision sections, grouped by theme, dated. | 12 |
| 5d | Handover: run, add and publish an activity, change α or a rule, rerun the evaluation. | 12 |

## Pages

| File | Covers | Script | Generated | Commit |
|---|---|---|---|---|
| `01_tests_and_requirements.md` | 1a, 2e, requirement coverage | `scripts/report_evidence/tests_and_ci.py` | 2026-11-21T22:26:01+03:00 | 48210e2 |
| `02_environment.md` | 1b | `scripts/report_evidence/environment.py` | 2026-11-21T22:27:15+03:00 | 48210e2 |
| `03_catalogue_dataset_config.md` | 1c, 1d, 1e, 2a, 2b | `scripts/report_evidence/catalogue_and_config.py` | 2026-11-21T22:27:53+03:00 | 48210e2 |
| `04_evaluation.md` | 1f, 1g (coverage, areas per top 5), 2d data | `scripts/report_evidence/evaluation.py` | 2026-11-21T22:28:19+03:00 | 48210e2 |
| `05_latency.md` | 1g (latency, memory, start-up) | `scripts/report_evidence/latency.py` | 2026-11-21T22:28:38+03:00 | 48210e2 |
| `06_explanation_examples.md` | 2c | `scripts/report_evidence/explanation_examples.py` | 2026-11-21T22:28:54+03:00 | 48210e2 |
| `07_workflow_transcript.md` | 2f | `scripts/report_evidence/workflow_transcript.py` | 2026-11-21T22:29:12+03:00 | 48210e2 |
| `08_mobile_and_repository.md` | 1h, 1i, 1j | `scripts/report_evidence/mobile_and_repo.py` | 2026-11-21T22:31:17+03:00 | 48210e2 |
| `09_figures.md` | 2d figures, 2a heatmap | `scripts/report_evidence/make_figures.py` | 2026-11-21T22:33:25+03:00 | 48210e2 |
| `10_chapters_1_to_4_sync.md` | 3a-3i | `scripts/report_evidence/sync_chapters.py` | 2026-11-21T22:31:41+03:00 | 48210e2 |
| `11_security_privacy_deployment.md` | 4a-4e | `scripts/report_evidence/security_privacy.py` | 2026-11-21T22:32:59+03:00 | 48210e2 |
| `12_chapter6_inputs.md` | 5a-5d | `scripts/report_evidence/chapter6.py` | 2026-11-21T22:33:22+03:00 | 48210e2 |

The commit is the one checked out when the page was generated; the scripts themselves are added by this pull request.

## Raw outputs (`raw/`)

- `raw/activities_inventory.csv`
- `raw/activity_frequency_alpha_0.7.csv`
- `raw/admin_site.csv`
- `raw/alpha_curve.csv`
- `raw/alpha_grid_markdown.txt`
- `raw/api_endpoints.csv`
- `raw/changes_since_sprint6.csv`
- `raw/chapter6_summary.json`
- `raw/ci_runs.json`
- `raw/ci_skips.json`
- `raw/class_diagram.mmd`
- `raw/configuration.csv`
- `raw/dataset_samples.json`
- `raw/decision_log.csv`
- `raw/deployment.json`
- `raw/deviations.csv`
- `raw/engine_mentions.json`
- `raw/environment.json`
- `raw/er_diagram.mmd`
- `raw/explanation_profiles.json`
- `raw/explanation_rules_fired.csv`
- `raw/explanation_top5.csv`
- `raw/exploratory_top5.csv`
- `raw/flutter_pub_outdated.json`
- `raw/grade0_sources.csv`
- `raw/grade_distribution.csv`
- `raw/latency_runs.csv`
- `raw/latency_summary.json`
- `raw/limitations.csv`
- `raw/management_commands.csv`
- `raw/milestones_github.csv`
- `raw/milestones_inventory.csv`
- `raw/mobile_navigation.mmd`
- `raw/mobile_screens.csv`
- `raw/mobile_screens_map.csv`
- `raw/mobile_services.json`
- `raw/model_fields.csv`
- `raw/model_tables.csv`
- `raw/open_issues.csv`
- `raw/per_profile_test.csv`
- `raw/per_profile_test_by_rater.csv`
- `raw/permission_probe.csv`
- `raw/pip_audit.json`
- `raw/pip_audit_findings.csv`
- `raw/published_by_domain_age.csv`
- `raw/rank_grade_matrix.csv`
- `raw/rater_agreement.json`
- `raw/rater_confusion.csv`
- `raw/repository.json`
- `raw/request_flow.csv`
- `raw/requirement_coverage.csv`
- `raw/secret_scan.json`
- `raw/security_implementation.csv`
- `raw/security_negative_tests.csv`
- `raw/test_inventory.csv`
- `raw/tests_backend_log.txt`
- `raw/tests_flutter_log.jsonl`
- `raw/tests_summary.json`
- `raw/tfidf_comparison_markdown.txt`
- `raw/todo_fixme.csv`
- `raw/workflow_rows.json`
- `raw/workflow_transcript.json`

## Figures (`figures/`, 300 dpi)

- `figures/alpha_curve.png`
- `figures/grade_distribution.png`
- `figures/per_profile_test_ndcg5.png`
- `figures/published_heatmap.png`
- `figures/rank_grade_matrix.png`

## UNKNOWN items

- `08_mobile_and_repository.md:121`: Exported responses or scorer output (CSV, JSON, XLSX or TXT among them): none. **UNKNOWN**: no reader-test responses or scorer output are in the repository (the test and the caregiver sessions have no
- `11_security_privacy_deployment.md:94`: - **Hosting:** No deployment files in the repository; docs/known_limitations.md:49 says the backend is not hosted. URL, provider, region, instance, database, HTTPS and cost: UNKNOWN (nothing hosted).
