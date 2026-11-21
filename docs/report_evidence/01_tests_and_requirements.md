# Tests, CI and requirement coverage

> Generated 2026-11-21T23:32:44+03:00 at commit `45ea972` by `backend\venv\Scripts\python.exe scripts\report_evidence\tests_and_ci.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

## 1a. Test totals

| Suite | Tests run | Result | Skipped | Time |
|---|---|---|---|---|
| Backend (`manage.py test -v 2`) | 714 | OK | 0 | 769.961 s |
| Flutter (`flutter test --reporter json`) | 200 | {'success': 200} | 0 | |

Skipped backend tests and the reason each gives:

| Test | Reason |
|---|---|
| none |  |

Skipped Flutter tests: none.

**Latest completed CI run on `main`:** CI, success, 2026-11-21T19:38:16Z (run 44941993266: Merge pull request #265 from <redacted>/docs/264-evidence-refresh).

**Skipped in that CI run (from its log):** Backend (Django, sqlite): 5, Backend (Django, postgresql): 3. CI runs without `-v`, so the log has counts only; the conditions in the code explain them:

| Test class | File | Runs only if | Reason given |
|---|---|---|---|
| RealSbertModelTests | backend/recommendations/test_embeddings.py:230 | `settings.SBERT_MODEL_PATH.exists()` | SBERT model not downloaded (run setup_sbert.py); skipped in CI |
| ConcurrentPostTests | backend/recommendations/test_recommendations_api.py:737 | `connection.vendor == "postgresql"` | Row locking needs PostgreSQL; SQLite serialises writes differently |
| RealModelRetrievalTests | backend/recommendations/test_retrieval.py:274 | `settings.SBERT_MODEL_PATH.exists()` | SBERT model not downloaded (run setup_sbert.py); skipped in CI |
| RealModelSpotCheckTests | backend/recommendations/test_spot_check.py:169 | `settings.SBERT_MODEL_PATH.exists()` | SBERT model not downloaded (run setup_sbert.py); skipped in CI |

**CI conclusions over the last 200 runs (all branches):** {'success': 198, 'failure': 2}.

Raw: `raw/tests_backend_log.txt`, `raw/tests_flutter_log.jsonl`, `raw/ci_runs.json`, `raw/ci_skips.json`, `raw/tests_summary.json`. Locally the SBERT model is present and the database is PostgreSQL, so nothing is skipped.

## 2e. Test inventory

913 tests in `raw/test_inventory.csv` (suite, test, file:line, first assertion, level, type):

| Suite | Level | Tests |
|---|---|---|
| backend | integration | 568 |
| backend | unit | 146 |
| flutter | end-to-end | 1 |
| flutter | unit | 15 |
| flutter | widget | 183 |

- Level: backend `unit` = `SimpleTestCase` (no database); `integration` = `TestCase`/`APITestCase` (test database, often through the REST API). Flutter `widget` = `testWidgets`; `unit` = `test`; `end-to-end` = `integration_test/`.
- Type: `api` uses the REST client; `command` calls a management command; `ui` is a widget test; `logic` is the rest.
- The parsed count can differ slightly from the runner's count: parameterised loops and helper-built tests are counted once.

## Requirement coverage

From `docs/requirements_traceability.md` (statuses mapped: Met → Done; Met, with a deviation → Done with a stated deviation; Met, with an addition → Done with a stated addition; Partly met → Partial; Evidence pending → Done (built), evidence pending). Each cited test file was checked to exist. Full table: `raw/requirement_coverage.csv`.

| ID | Requirement | Status | Cited test files |
|---|---|---|---|
| FR-01 | Registration and authentication | Done (with a stated deviation) | profiles/test_api.py (found); test_two_factor.py (found); test_google_sign_in.py (found); test_token_expiry.py (found); auth_screen_test.dart (found); google_sign_in_test.dart (found) |
| FR-02 | Role management | Done | profiles/test_api.py (found) |
| FR-03 | Child profile management | Partial | profiles/tests.py (found); test_account_deletion.py (found); children_screen_test.dart (found); edit_and_delete_test.dart (found) |
| FR-04 | Developmental information recording | Partial | profiles/test_milestone_api.py (found); test_tracker.py (found); milestone_screen_test.dart (found); milestone_tracker_test.dart (found) |
| FR-05 | Developmental profile generation | Done (with a stated deviation) | profiles/test_rules.py (found); test_profile_scenarios.py (found); test_guidelines.py (found) |
| FR-06 | Activity repository management | Done | activities/tests.py (found); test_seed.py (found); admin_test.dart (found) |
| FR-07 | Activity information management | Done | activities/tests.py (found); test_load_plain_aims.py (found) |
| FR-08 | Personalised recommendation | Done | recommendations/generation.py (found); recommendations/test_recommendations_api.py (found) |
| FR-09 | Semantic retrieval | Done (with a stated addition) | recommendations/retrieval.py (found); lexical.py (found); recommendations/test_retrieval.py (found); test_embeddings.py (found); test_lexical.py (found) |
| FR-10 | Ranking and scoring | Done (with a stated deviation) | recommendations/ranking.py (found); recommendations/test_ranking.py (found) |
| FR-11 | Recommendation explanation | Done | recommendations/explanations.py (found); recommendations/test_explanations.py (found) |
| FR-12 | View recommendations | Done | recommendations_screen_test.dart (found); test_recommendations_api.py (found) |
| FR-13 | Activity details | Done | activity_detail_screen_test.dart (found); activity_details_and_polish_test.dart (found) |
| FR-14 | Completion tracking | Done | feedback/test_api.py (found); activity_progress_test.dart (found) |
| FR-15 | Caregiver feedback | Done | feedback/tests.py (found); test_api.py (found); test_observations.py (found); well_done_sheet_test.dart (found); feedback_options_test.dart (found) |
| FR-16 | Feedback review | Done | feedback/test_admin.py (found); admin_test.dart (found) |
| FR-17 | Request validation | Done | profiles/tests.py (found); test_milestone_api.py (found); children_screen_test.dart (found) |
| FR-18 | Recommendation storage | Done | recommendations/test_recommendations_api.py (found) |
| NFR-01 | Performance | Done | — |
| NFR-02 | Security | Done | profiles/test_api.py (found); test_token_expiry.py (found) |
| NFR-03 | Data privacy | Done | profiles/test_api.py (found); test_privacy.py (found); test_account_deletion.py (found); privacy_consent_test.dart (found) |
| NFR-04 | Data integrity | Done | recommendations/tests.py (found); test_recommendations_api.py (found) |
| NFR-05 | Reliability | Done | test_recommendations_api.py (found) |
| NFR-06 | Usability (SUS) | Done (built); evidence pending | — |
| NFR-07 | Accessibility | Done | accessibility_test.dart (found) |
| NFR-08 | Compatibility | Done (with a stated deviation) | — |
| NFR-09 | Maintainability | Done | — |
| NFR-10 | Explainability | Done (built); evidence pending | — |
| NFR-11 | Human oversight | Done | test_explanations.py (found); test_referral.py (found); test_tracker.py (found) |
| NFR-12 | Recommendation quality | Done (with a stated deviation) | — |
| NFR-13 | Caregiver satisfaction | Done (built); evidence pending | — |
| DR-01 | User data | Done | — |
| DR-02 | Child profile data | Partial | — |
| DR-03 | Developmental data | Partial | — |
| DR-04 | Activity data | Done | — |
| DR-05 | Recommendation data | Done | — |
| DR-06 | Completion data | Done | — |
| DR-07 | Feedback data | Done | — |
| DR-08 | Data validation | Done | activities/test_seed.py (found) |
| DR-09 | Preprocessing and embeddings | Done | test_embeddings.py (found) |
| DR-10 | Provenance and traceability | Done | — |
| DR-11 | Data protection | Partial | — |
| IR-01 | Mobile interface | Done | — |
| IR-02 | Administrator interface | Done | — |
| IR-03 | REST API | Done | — |
| IR-04 | JSON format | Done | — |
| IR-05 | Recommendation engine interface | Done | — |
| IR-06 | Processing stages | Done | — |
| IR-07 | Database interface | Done | — |
| IR-08 | Error handling | Done | profiles/test_api.py (found); email_failure_test.dart (found) |
| IR-09 | Secure communication | Partial | — |
