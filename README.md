# Nurtura

Nurtura is an AI-based recommendation system that suggests evidence-based early childhood developmental activities (prenatal to 36 months) matched to a child's age and developmental needs. A rule engine turns the milestones a caregiver records into developmental priorities, Sentence-BERT (SBERT) matches those needs to a curated activity library, a weighted ranking orders the results, and each recommendation comes with a plain-language explanation.

**Relationship to SOFIA:** Nurtura is the developmental-activity recommendation component of SOFIA, a larger platform built for Webmasters Kenya.

**Where things stand:** see [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) for the project in plain language, [docs/sprint_ii_review.md](docs/sprint_ii_review.md) for the current sprint status, and [docs/known_limitations.md](docs/known_limitations.md) for known limitations and open defects.

## Repository layout

```
nurtura/
├── backend/                Django + Django REST Framework API and admin
│   ├── nurtura_backend/        settings, URLs, admin branding tests
│   ├── profiles/               caregivers, children, milestones, rule engine, two-step sign-in
│   ├── activities/             activity library and content review workflow
│   ├── recommendations/        SBERT retrieval, weighted ranking, explanations, evaluation
│   ├── feedback/               "done" marks and ratings (FeedbackManager), admin review
│   ├── insights/               admin analytics: the app's admin API and the web admin's dashboard
│   ├── templates/, static/     admin theme and dashboard
│   ├── setup_sbert.py          downloads + verifies the SBERT model
│   └── models/                 cached SBERT model (gitignored, created by setup_sbert.py)
├── mobile/nurtura_app/     Flutter app (Android, iOS, web)
│   ├── lib/                    caregiver and administrator screens, state, services, theme
│   ├── test/                   widget and unit tests
│   └── integration_test/       end-to-end test against the real backend
├── data/                   activity dataset, milestone catalogue, evaluation labels (see data/README.md)
├── docs/                   project documentation (index below)
├── .github/workflows/      CI (Django checks and tests, Flutter analyze + test)
└── Makefile                shortcuts for the commands below
```

## Prerequisites

| Tool | Version used | Notes |
|---|---|---|
| Git | 2.x | |
| Python | 3.13 | |
| Flutter | 3.47 (stable) | run `flutter doctor`; Android SDK (for a phone or emulator) and/or Chrome |
| PostgreSQL | 18 | used for development and the full test suite; SQLite is a fallback for basic checks when `DB_NAME` is unset |
| Android phone or emulator | Android 7+ | optional; for running the app on a device. `adb` comes with the Android SDK |

## Backend setup

From the repo root:

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:

| Shell | Command |
|---|---|
| Windows PowerShell | `venv\Scripts\Activate.ps1` |
| Windows Git Bash | `source venv/Scripts/activate` |
| macOS / Linux / WSL | `source venv/bin/activate` |

Then:

```bash
pip install -r requirements.txt       # includes PyTorch; large download
cp .env.example .env                  # Windows PowerShell: copy .env.example .env
python setup_sbert.py                 # downloads all-MiniLM-L6-v2 to backend/models/ (~90 MB)
python manage.py migrate
python manage.py createsuperuser      # your administrator account
python manage.py runserver            # http://127.0.0.1:8000
```

> **Slow or unreliable connection?** If pip reports `No matching distribution found ... (from versions: none)` for a package that clearly exists, it is usually a network timeout, not a missing package. Retry with:
> `pip install --timeout 600 --retries 20 --resume-retries 50 -r requirements.txt`

### From an empty database to working recommendations

A fresh database has no activities or milestones. Run these once, in order, with the venv active (from `backend/` unless noted):

1. **Load the activity library and milestone catalogue:** `make seed-data` from the repo root, or:
   ```bash
   cd ../data/scripts && python clean_activities.py "../raw/activities_batch*.csv" ../processed/activities_clean.csv && cd ../../backend
   python manage.py seed_activities      # activities arrive as Draft
   python manage.py seed_milestones      # CDC/WHO milestone catalogue
   ```
2. **Review and publish the activities** in the app's Activities tab (signed in as an administrator: open an activity, *Submit for review*, then *Publish*), or in bulk in the web admin (`/admin/` → Developmental activities: select them, run *Submit selected activities for review*, then *Publish selected activities*). Only Published activities can be recommended.
3. **Load the approved plain-language aims** used in explanations: `python manage.py load_plain_aims`.
4. **Embed the Published activities** for semantic search: `python manage.py embed_activities` (re-run after publishing or editing activities).

The app can then register caregivers, record milestones and generate recommendations.

### Environment variables (`backend/.env`)

`.env` is gitignored; never commit it. `.env.example` lists every variable with a safe placeholder:

| Variable | Purpose |
|---|---|
| `DEBUG` | `True` for local development |
| `SECRET_KEY` | Django secret key. Required when `DEBUG` is not `True` |
| `ALLOWED_HOSTS` | Comma-separated hostnames the server answers to |
| `CORS_ALLOWED_ORIGINS` | Browser origins allowed to call the API in production (any `localhost` port is allowed when `DEBUG=True`) |
| `DB_NAME` | PostgreSQL database name. **Leave empty to use SQLite** |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection |
| `NURTURA_MODEL_WARMUP` | `1` loads the SBERT model when the server starts so the first recommendation is fast; unset means off in development, on otherwise |
| `RANKING_ALPHA` | Weight of rule priority in the ranking. Leave unset to use the evaluated value, 0.7 |
| `SBERT_MODEL_PATH` | Where the SBERT model is stored. Leave unset for `backend/models/` |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | SMTP for the two-step sign-in codes. **Leave `EMAIL_HOST` empty in development**: codes are then printed in the `runserver` output |
| `GOOGLE_OAUTH_CLIENT_IDS` | The **web** OAuth client ID(s) for Continue with Google, comma-separated. Empty turns Google sign-in off (see "Continue with Google" below) |

### PostgreSQL

After installing PostgreSQL, create a database and user (choose your own password):

```sql
-- psql -U postgres
CREATE USER nurtura_user WITH PASSWORD 'your-own-password';
CREATE DATABASE nurtura_db OWNER nurtura_user;
```

Then set `DB_NAME=nurtura_db`, `DB_USER`, `DB_PASSWORD`, `DB_HOST=localhost` and `DB_PORT=5432` in `backend/.env` and run `python manage.py migrate`.

To run `python manage.py test` against PostgreSQL, the database user also needs permission to create the temporary test database:

```sql
ALTER USER nurtura_user CREATEDB;
```

### Users and roles

There are two roles:

- **Caregiver**: uses the mobile app through the API. Anyone can register as a caregiver, with an email and password (a new phone needs a 6-digit code sent by email) or with **Continue with Google** (no code; the Google account's verified email is used). It's one account per email either way: someone who registered with email can later use Google, and an account made with Google can set a password with *Forgot password?*.
- **Administrator**: uses the same mobile app, with the same two-step sign-in. An administrator account opens the admin screens instead of the caregiver ones:
  - **Dashboard:** use over 7, 30 or 90 days, outcomes, system health (with *Update search index*), work waiting, library coverage, recent changes, ratings and milestone progress. Aggregates only, no family details.
  - **Activities:** search and filter the library, add activities as Draft, edit them, and move them through review. Editing reviewed content returns it to Draft.
  - **Feedback:** caregivers' ratings and comments against each activity, read-only, without the child's name or the caregiver's email.

  The Django admin at `/admin/` stays as a backup, with the same dashboard. It is also where users, tokens and milestone verification are managed. Only administrators can sign in to it.

Create the first administrator with `python manage.py createsuperuser`; it is given the Administrator role automatically. Further administrators can be added from the web admin's Users page.

### API

All endpoints are under `/api/` and, apart from registration and the sign-in steps, need an `Authorization: Token <token>` header. Caregivers only ever reach their own children; another caregiver's child is a 404, and administrators get 403.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register/` | Create a caregiver account (`username`, `email`, `password`, `device_id`). Returns a challenge, and a 6-digit code is emailed. Each email can only be used once (case-insensitive) |
| POST | `/api/auth/login/` | Sign in with `username`, `password` and `device_id`. The app sends the email as `username`; an account whose username is different (e.g. an administrator from `createsuperuser`) is found by its email. A trusted phone gets a token straight away; a new one gets a challenge and an emailed code. Limited to 5 attempts per minute per client |
| POST | `/api/auth/login/verify/` | Exchange the challenge and code for a token; `remember_device` trusts the phone for 30 days. Codes last 10 minutes and allow 5 tries |
| POST | `/api/auth/login/resend/` | Email a new code for a challenge (after 30 s; at most 3 times) |
| POST | `/api/auth/password-reset/` | Email a 6-digit code for choosing a new password (`email`). The reply is the same whether or not the email has an account. Limited to 5 per minute per client |
| POST | `/api/auth/password-reset/resend/` | Email a new reset code for a challenge (same limits as the login code) |
| POST | `/api/auth/password-reset/confirm/` | Set `new_password` with the `challenge` and `code` (the password rules apply). Signs the account out on every other device and returns a token for this one; `device_id` and `remember_device` work as at login |
| POST | `/api/auth/google/` | Continue with Google: exchange a Google ID token (`id_token`, plus `device_id` and `remember_device`) for a token. Signs in the account with the token's verified email, or creates a caregiver (201). Administrators are refused. 503 until `GOOGLE_OAUTH_CLIENT_IDS` is set |
| POST | `/api/auth/logout/` | Invalidate the current token |
| GET, DELETE | `/api/auth/me/` | GET the current user, including `role`, `privacy_consent_required` (a caregiver who hasn't agreed to the current privacy notice) and `privacy_agreed_at`. DELETE a caregiver's own account with everything it owns (children, milestones, recommendations, completions, ratings, codes, trusted phones), confirmed with `password` (or `email` for an account with no password); 204. Administrators get 403. Limited to 5 per minute |
| GET | `/api/privacy-notice/` | The current privacy notice (`version`, `title`, `sections`); public. Mirrored in [docs/privacy_notice.md](docs/privacy_notice.md) |
| POST | `/api/auth/privacy-consent/` | Agree to the notice: `version` must be the current one (otherwise 400). Until a caregiver has agreed, adding a child, changing one or recording a milestone is refused (403); reading and deleting are allowed |
| GET, POST | `/api/children/` | List or create the caregiver's own child profiles (`concerns` is a list of domains, e.g. `["Sensory"]`; a future date of birth is a due date) |
| GET, PATCH, PUT, DELETE | `/api/children/<id>/` | One of the caregiver's own child profiles |
| GET, POST | `/api/children/<id>/milestones/` | The child's recorded milestones, or record one (`reference`, `status`: `achieved`, `emerging` or `not_yet`) |
| GET | `/api/children/<id>/profile/` | The rule engine's developmental priorities for the child |
| GET | `/api/reference-milestones/?search=&domain=` | The CDC/WHO milestone catalogue |
| GET, POST | `/api/children/<id>/recommendations/` | GET the newest stored batch; POST ranks, explains and stores a new batch (or returns the identical newest one) |
| GET | `/api/children/<id>/candidates/?limit=10` | SBERT retrieval candidates before ranking (for inspection) |
| PUT, DELETE | `/api/recommendations/<id>/completion/` | Mark a recommended activity done (`status`: `completed` or `partially_completed`), or undo it |
| GET, PUT | `/api/recommendations/<id>/feedback/` | Read or submit the caregiver's rating (1–5) and comment |

The administrator endpoints are under `/api/admin/`; caregivers get 403.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/admin/overview/?range=30` | The dashboard's figures for the last 7, 30 or 90 days |
| POST | `/api/admin/search-index/` | Embed Published activities that aren't searchable yet (`embed_activities`) |
| GET, POST | `/api/admin/activities/?status=&domain=&search=` | List activities, or add one (always as Draft, with the next `ACT-` ID) |
| GET, PATCH | `/api/admin/activities/<id>/` | One activity; editing reviewed content returns it to Draft |
| POST | `/api/admin/activities/<id>/status/` | Move it through review (`status`: `draft`, `under_review` or `published`) |
| GET | `/api/admin/choices/` | Areas, ages, difficulty levels, sources, statuses and the allowed status moves |
| GET | `/api/admin/feedback/?rating=&domain=&activity=&limit=&offset=` | Ratings and comments against each activity, newest first, without family details |

## Mobile setup

Start the backend first (`python manage.py runserver`), then from `mobile/nurtura_app`:

```bash
flutter pub get
```

The server address is built into the app with `--dart-define=API_BASE_URL=...`. Without it, the app uses `http://127.0.0.1:8000` (web and desktop) or `http://10.0.2.2:8000` (Android emulator).

| Where | How |
|---|---|
| **Android phone over USB** (used for the demos) | Enable USB debugging, plug in, then `adb reverse tcp:8000 tcp:8000` (repeat after re-plugging) and `flutter run -d <device-id> --dart-define=API_BASE_URL=http://127.0.0.1:8000`. `flutter devices` lists device IDs |
| Android emulator | `flutter run -d <emulator-id>` |
| Chrome | `flutter run -d chrome` (any `localhost` port is allowed by CORS in development) |

App identifier: `com.sofia.nurtura_app` (Android), `com.sofia.nurturaApp` (iOS). The app is named **Nurtura** on the home screen.

### Continue with Google (optional, Android)

The button only appears in a build given the web client ID, and the backend only accepts Google tokens once it has the same ID. Setting it up is free (no billing account):

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project, then **APIs & Services → OAuth consent screen**: External, app name Nurtura, your support email, and the `email`, `profile` and `openid` scopes. While it's in *Testing*, add the Google accounts that will try it as test users (up to 100).
2. **Credentials → Create credentials → OAuth client ID → Android**: package name `com.sofia.nurtura_app` and the SHA-1 of the key the app is signed with. For debug builds on a laptop:
   ```bash
   keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android -keypass android
   ```
   Each laptop has its own debug key, and a release build needs the release key's SHA-1 too (add another Android client).
3. **Create credentials → OAuth client ID → Web application** (no URIs needed). This client ID is the one both sides use:
   - `backend/.env`: `GOOGLE_OAUTH_CLIENT_IDS=<web client ID>`, then restart the backend;
   - the app: add `--dart-define=GOOGLE_SERVER_CLIENT_ID=<web client ID>` to `flutter run` or `flutter build`.

Only the Google account's verified email is used and stored; Google's name and photo are not kept.

### End-to-end test (real backend)

`integration_test/app_flow_test.dart` drives the whole Sprint 8 round trip against the running backend: register (a person types the emailed code), log back in on the trusted phone, create an expecting and a born child profile, record a milestone, get ranked recommendations with explanations, mark one done, rate it, and check Progress and dark mode. It saves screenshots to `build/e2e_screenshots/`. Use an email that isn't registered yet (a Gmail `+alias` works).

On a phone over USB (after `adb reverse tcp:8000 tcp:8000`):

```bash
flutter drive -d <device-id> \
  --driver=test_driver/integration_test.dart \
  --target=integration_test/app_flow_test.dart \
  --dart-define=API_BASE_URL=http://127.0.0.1:8000 \
  --dart-define=E2E_EMAIL=someone-new@example.com
```

In Chrome, start [ChromeDriver](https://googlechromelabs.github.io/chrome-for-testing/) on port 4444 and use `-d chrome` instead. `flutter drive` replaces the app on the phone with a test build; run `flutter run` again afterwards.

## Git hooks

Black runs on staged Python files before each commit. Install the hook once per clone, with the backend venv active:

```bash
pre-commit install
```

If black reformats a file, the commit stops. Stage the changes (`git add`) and commit again.

## Common Commands

`make` works on macOS/Linux, WSL and Git Bash (if `make` is installed). On native Windows without `make`, use the raw commands. Run backend commands with the venv active.

| Task | Make | Raw command |
|---|---|---|
| One-time setup | `make setup` | see Backend and Mobile setup above, plus `pre-commit install` |
| Run backend | `make run-backend` | `cd backend && python manage.py runserver` |
| Run app | `make run-app DEVICE=chrome` | `cd mobile/nurtura_app && flutter run -d chrome` |
| Clean activity data | (first half of `make seed-data`) | `cd data/scripts && python clean_activities.py "../raw/activities_batch*.csv" ../processed/activities_clean.csv` |
| Load activities into the database | `make seed-data` (cleans, then loads) | `cd backend && python manage.py seed_activities` (add `--dry-run` to preview) |
| Load the guideline milestone catalogue | (part of `make seed-data`) | `cd backend && python manage.py seed_milestones` (add `--dry-run` to preview) |
| Load approved plain-language aims | | `cd backend && python manage.py load_plain_aims` (`--dry-run` to preview) |
| Embed Published activities for semantic retrieval | | `cd backend && python manage.py embed_activities` (re-run after publishing or editing activities; `--dry-run` to preview, `--force` to re-embed all) |
| Backend checks | `make test` (runs all checks) | `cd backend && python manage.py check && python manage.py makemigrations --check --dry-run && python manage.py test` |
| Flutter checks | (included in `make test`) | `cd mobile/nurtura_app && flutter analyze && flutter test` |
| Format Python | (automatic on commit) | `pre-commit run --all-files` |
| Apply migrations | | `cd backend && python manage.py migrate` |
| Verify SBERT model | | `cd backend && python setup_sbert.py` |
| Re-run the ranking evaluation | | `cd backend && python manage.py evaluate_alpha_grid` (see [docs/sprint5_alpha_results.md](docs/sprint5_alpha_results.md)) |
| Check nothing evaluated has changed | | `cd backend && python manage.py evaluate_alpha_grid --check-provenance` (run before any change to `backend/` during the explanation reader test) |
| Spot-check retrieval relevance (Sprint 4) | | `cd backend && python manage.py spot_check_retrieval` (`--markdown` for the report; nothing is saved) |
| Write the relevance-labelling template (Sprint 5) | | `cd backend && python manage.py export_relevance_template` (see [data/evaluation/README.md](data/evaluation/README.md)) |

## Continuous integration

`.github/workflows/ci.yml` runs on every push to `main` and on pull requests:

- **Backend:** installs `backend/requirements.txt` (with CPU-only PyTorch), then runs `manage.py check`, `makemigrations --check --dry-run` and `manage.py test`, plus the PostgreSQL-only concurrency test. Tests that need the SBERT model are skipped there, since the model isn't downloaded in CI.
- **Mobile:** `flutter pub get`, `flutter analyze`, `flutter test`.

## Documentation

| Document | What it covers |
|---|---|
| [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) | The project in plain language: pipeline, a worked example, results, status |
| [docs/sprint_ii_review.md](docs/sprint_ii_review.md) | Sprint II requirements against their evidence; tasks done and outstanding; next steps |
| [docs/testing_and_evaluation_record.md](docs/testing_and_evaluation_record.md) | Tests run, expected and actual results, defects and corrections, evaluation so far |
| [docs/known_limitations.md](docs/known_limitations.md) | Known limitations and outstanding defects |
| [docs/deployment_requirements.md](docs/deployment_requirements.md) | What hosting needs (Sprint III) |
| [docs/demo_checklist.md](docs/demo_checklist.md) | Running a live demo on a phone |
| [docs/sprint5_alpha_results.md](docs/sprint5_alpha_results.md) | The ranking evaluation (held-out children, nDCG, choice of α) |
| [docs/explanation_reader_test.md](docs/explanation_reader_test.md) | The explanation reader test (Sprint 6) |
| [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md) | The sprint plan and GitHub workflow |
| [data/README.md](data/README.md) | Activity data: schema, sources, cleaning, ethics |

## Data

See [data/README.md](data/README.md) for the activity schema, controlled vocabularies, cleaning workflow, sources and ethics. Activities must be traceable to WHO, CDC, UNICEF, Montessori or Pathways.org guidance.
