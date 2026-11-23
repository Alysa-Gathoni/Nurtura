# Security, privacy and deployment

> Generated 2026-11-23T13:42:03+03:00 at commit `d932476` by `backend\venv\Scripts\python.exe scripts\report_evidence\security_privacy.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

## 4a. Negative tests

20 checks through DRF's test client against the real URL configuration and settings, with fictional users, inside one transaction that was rolled back. `raw/security_negative_tests.csv`. Passed: 20 of 20.

| Test | Request (redacted) | Expected | Actual | Result |
|---|---|---|---|---|
| Weak password | `POST /api/auth/register/ {"password": "password"}` | 400 | 400 | pass |
| Duplicate email | `POST /api/auth/register/ {"email": <existing>}` | 400 | 400 | pass |
| Six wrong logins in a minute | `POST /api/auth/login/ x6 {"password": <wrong>}` | 400 x5, then 429 | 400 400 400 400 400 429 | pass |
| No token | `GET /api/children/ (no Authorization)` | 401 | 401 | pass |
| Bad token | `GET /api/children/ (Authorization: Token <invalid>)` | 401 | 401 | pass |
| Another caregiver's child (GET) | `GET /api/children/<other's id>/` | 404 | 404 | pass |
| Another caregiver's child (PATCH) | `PATCH /api/children/<other's id>/` | 404 | 404 | pass |
| Another caregiver's child (DELETE) | `DELETE /api/children/<other's id>/` | 404 | 404 | pass |
| Child unchanged after those attempts | `SELECT the child` | still there, name unchanged | unchanged | pass |
| Administrator on the child API | `GET /api/children/ as administrator` | 403 | 403 | pass |
| Caregiver on the admin site | `GET /admin/ logged in as a caregiver` | 302 to the admin login (not 200) | 302 -> /admin/login/?next=/admin/ | pass |
| Role in the registration body | `POST /api/auth/register/ {"role": "administrator"}` | 201, role stays caregiver | 201, role caregiver | pass |
| Invalid JSON | `POST /api/children/ body `{not json`` | 400 | 400 | pass |
| Oversized JSON | `POST /api/children/ with a 2561 KB body (limit 2560 KB)` | 400 or 413, nothing saved | 400 | pass |
| SQL-like text in a field | `POST /api/children/ {"name": "Robert'); DROP TABLE profiles_childprofile;--"}` | 201, stored as plain text, table intact | 201, stored literally: True | pass |
| Unpublished activity | `POST /api/children/<id>/activities/<Draft id>/try/` | 404 | 404 | pass |
| Save an unpublished activity | `PUT /api/children/<id>/saved/<Draft id>/` | 404 | 404 | pass |
| Unauthorised publish (caregiver) | `POST /api/admin/activities/<id>/status/ {"status": "published"}` | 403 | 403 | pass |
| Publish skipping review (administrator) | `Draft -> Published directly` | 400 | 400 | pass |
| Draft still Draft | `SELECT content_status` | draft | draft | pass |

## 4b. Implementation summary

| Item | Value | Where |
|---|---|---|
| Authentication | ExpiringTokenAuthentication, SessionAuthentication | backend/nurtura_backend/settings.py:236 |
| Token lifecycle | expires after 30 days, 0:00:00; two-step email code at login | backend/nurtura_backend/settings.py:230; backend/profiles/authentication.py:36; backend/profiles/two_factor.py |
| Default permission | IsAuthenticated | backend/nurtura_backend/settings.py:242 |
| Roles | IsCaregiver, IsAdministrator, HasPrivacyConsent | backend/profiles/permissions.py:6 |
| Throttling | {'login': '5/minute', 'two_factor': '10/minute', 'password_reset': '5/minute', 'account_delete': '5/minute'} | backend/nurtura_backend/settings.py:246 |
| Password validators | UserAttributeSimilarityValidator, MinimumLengthValidator, CommonPasswordValidator, NumericPasswordValidator | backend/nurtura_backend/settings.py:148 |
| Admin restriction | is_staff follows the Administrator role; admin site needs an active staff user | backend/profiles/models.py:71 |
| Deletion rules | account deletion confirms with password (or email for Google accounts); child data cascades | backend/profiles/views.py:363; see 4d |
| DEBUG | default False unless DEBUG env is 1/true/yes (this run: True) | backend/nurtura_backend/settings.py:33 |
| ALLOWED_HOSTS | from env, default localhost,127.0.0.1 (this run: ['localhost', '127.0.0.1', '10.24.114.180']) | backend/nurtura_backend/settings.py:44 |
| SESSION_COOKIE_SECURE | False | backend/nurtura_backend/settings.py (not set: Django default) |
| CSRF_COOKIE_SECURE | False | backend/nurtura_backend/settings.py (not set: Django default) |
| SECURE_SSL_REDIRECT | False | backend/nurtura_backend/settings.py (not set: Django default) |
| SECURE_HSTS_SECONDS | 0 | backend/nurtura_backend/settings.py (not set: Django default) |
| DATA_UPLOAD_MAX_MEMORY_SIZE | 2621440 | backend/nurtura_backend/settings.py (not set: Django default) |

## 4c. Dependency audit and secret scan

- **Python dependency audit:** pip-audit 2.10.1, `pip-audit --path backend/venv/Lib/site-packages -s osv` (OSV database; nothing installed into the backend): 78 packages, 40 known vulnerabilities in 7 packages. `raw/pip_audit.json`, `raw/pip_audit_findings.csv`. No upgrades were made: this pack changes no dependencies.

| Package | Version | Known vulnerabilities | Fixed in | Required by |
|---|---|---|---|---|
| black | 26.5.1 | 1 | 26.10.1 | requirements-dev.txt (development only) |
| certifi | 2026.7.22 | 1 | 2026.10.18 | requirements.txt (server) |
| djangorestframework | 3.18.1 | 3 | 3.18.2 | requirements.txt (server) |
| filelock | 4.0.4 | 14 | 4.0.9, 4.2.1 | requirements.txt (server) |
| pyasn1 | 0.6.4 | 4 | 0.6.5 | requirements.txt (server) |
| setuptools | 84.0.0 | 1 | 84.1.0 | requirements.txt (server) |
| virtualenv | 21.13.0 | 16 | 21.14.10, 21.14.2, 21.14.4, 21.14.7, 21.14.9 | requirements-dev.txt (development only) |

- **Flutter:** 19 packages have a newer version available (`flutter pub outdated` lists only those; direct and transitive). `raw/flutter_pub_outdated.json`.
- **Git history secret scan** (every added line in every commit on every branch, `git log --all -p`; counts and paths only, no values):

| Pattern | Added lines | Paths | Note |
|---|---|---|---|
| private key block | 0 | — |  |
| AWS access key | 0 | — |  |
| Google API key | 0 | — |  |
| GitHub token | 0 | — |  |
| Slack token | 0 | — |  |
| password/secret assignment with a literal | 25 | backend/insights/test_admin_api.py, backend/profiles/test_api.py, backend/profiles/test_google_sign_in.py, backend/profiles/test_password_reset.py, backend/profiles/test_password_reset_two_step.py, backend/profiles/test_token_expiry.py, backend/profiles/test_two_factor.py, mobile/nurtura_app/test/auth_screen_test.dart, mobile/nurtura_app/test/forgot_password_test.dart, mobile/nurtura_app/test/google_sign_in_test.dart, mobile/nurtura_app/test/verify_code_screen_test.dart, scripts/report_evidence/sync_chapters.py, scripts/report_evidence/workflow_transcript.py |  |
| Django SECRET_KEY literal | 1 | backend/nurtura_backend/settings.py | only the `django-insecure-` development fallback, used when DEBUG is on; production reads SECRET_KEY from the environment (backend/nurtura_backend/settings.py:42) |

`.env` files ever committed: none. Matches of the generic "password/secret assignment" pattern are candidates to review, not confirmed secrets; `raw/secret_scan.json`.

## 4d. Data protection

| Item | Status | Evidence |
|---|---|---|
| Consent record | Implemented | `privacy_notice_version`, `privacy_agreed_at` on the user (backend/profiles/models.py:46); `POST /api/auth/privacy-consent/`; notice text in backend/profiles/privacy.py; tests backend/profiles/test_privacy.py |
| Consent enforced | Implemented | writes refused until agreed (backend/profiles/permissions.py:16) |
| Data export (caregiver downloads their data) | Not built | no export endpoint or view found (searched `export` in profiles, recommendations views, feedback) |
| Cascading deletion | Implemented | ChildProfile.caregiver -> User (CASCADE); DevelopmentalMilestone.child -> ChildProfile (CASCADE); LoginChallenge.user -> User (CASCADE); TrustedDevice.user -> User (CASCADE); FingerprintKey.user -> User (CASCADE); Recommendation.child -> ChildProfile (CASCADE); SavedActivity.child -> ChildProfile (CASCADE); Feedback.recommendation -> Recommendation (CASCADE); account deletion `DELETE /api/auth/me/` (tests backend/profiles/test_account_deletion.py) |
| No soft delete for child data | Implemented | no `is_deleted`/`deleted_at`/soft-delete fields in backend code: rows are deleted |

## 4e. Deployment

- **Deployment files in the repository:** none.
- **Hosting:** No deployment files in the repository; docs/known_limitations.md:51 says the backend is not hosted. URL, provider, region, instance, database, HTTPS and cost: UNKNOWN (nothing hosted).
- **Measured** (one development laptop, `05_latency.md`): peak working set 597.0 MB; start-up 18.7 s.

| Disk | Size |
|---|---|
| backend code + model (no venv) | 184.7 MB |
| SBERT model folder | 91.6 MB |
| backend venv | 1190.7 MB |
| database (pg_database_size) | 13 MB |
| debug APKs built locally | app-debug.apk 214.6 MB |

APK:

| Step | How | Where |
|---|---|---|
| Build (debug, development) | `flutter build apk --debug --dart-define=API_BASE_URL=http://127.0.0.1:8000` | mobile/nurtura_app/README.md |
| Build (release) | `flutter build apk --release --dart-define=API_BASE_URL=https://…` | docs/deployment_requirements.md:15 |
| Signing | the release build type is signed with the **debug** key | mobile/nurtura_app/android/app/build.gradle.kts:36 |
| Install | `adb install -r <apk>` or `flutter run -d <device>`; the phone reaches the laptop with `adb reverse tcp:8000 tcp:8000` | mobile/nurtura_app/README.md |
