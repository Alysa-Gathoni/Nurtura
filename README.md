# Nurtura

Nurtura is an AI-based recommendation system that suggests evidence-based early childhood developmental activities (prenatal to 36 months) matched to a child's age and developmental needs. It uses SBERT sentence embeddings to match caregivers' needs to a curated activity library.

**Relationship to SOFIA:** Nurtura is the developmental-activity recommendation component of SOFIA, a larger platform built for Webmasters Kenya.

## Repository layout

```
nurtura/
├── backend/            Django + Django REST Framework API
│   ├── nurtura_backend/    project settings and URLs
│   ├── profiles/           child / caregiver profiles
│   ├── activities/         activity library
│   ├── recommendations/    SBERT-based recommendation logic
│   ├── feedback/           caregiver feedback on activities
│   ├── setup_sbert.py      downloads + verifies the SBERT model
│   └── models/             cached SBERT model (gitignored, created by setup_sbert.py)
├── mobile/nurtura_app/ Flutter app (Android, iOS, web)
├── data/               activity dataset + cleaning script (see data/README.md)
├── docs/               project documentation
├── .github/workflows/  CI (Django checks, Flutter analyze + test)
└── Makefile            shortcuts for the commands below
```

## Prerequisites

| Tool | Version used | Notes |
|---|---|---|
| Git | 2.x | |
| Python | 3.13 | |
| Flutter | 3.47 (stable) | run `flutter doctor`; Android SDK and/or Chrome needed |
| PostgreSQL | 18 | optional for basic checks; the backend falls back to SQLite when `DB_NAME` is unset |

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
python manage.py runserver            # http://127.0.0.1:8000
```

> **Slow or unreliable connection?** If pip reports `No matching distribution found ... (from versions: none)` for a package that clearly exists, it is usually a network timeout, not a missing package. Retry with:
> `pip install --timeout 600 --retries 20 --resume-retries 50 -r requirements.txt`

### Environment variables (`backend/.env`)

`.env` is gitignored; never commit it. `.env.example` lists every variable:

| Variable | Purpose |
|---|---|
| `DEBUG` | `True` for local development |
| `SECRET_KEY` | Django secret key. Required when `DEBUG` is not `True` |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `DB_NAME` | PostgreSQL database name. **Leave empty to use SQLite** |
| `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection |

### PostgreSQL (optional for basic checks)

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

- **Caregiver**: uses the mobile app through the API. Anyone can register as a caregiver.
- **Administrator**: manages the activity repository (including publishing) in the Django admin at `/admin/`. Only administrators can sign in to the admin.

Create the first administrator with `python manage.py createsuperuser`; it is given the Administrator role automatically. Further administrators can be added from the admin's Users page.

### API

All endpoints are under `/api/` and, apart from register and login, need an `Authorization: Token <token>` header.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register/` | Create a caregiver account (`username`, `email`, `password`); returns a token. Each email can only be used once (case-insensitive) |
| POST | `/api/auth/login/` | Exchange `username` and `password` for a token. Limited to 5 attempts per minute per client (`429 Too Many Requests` after that) |
| POST | `/api/auth/logout/` | Invalidate the current token |
| GET | `/api/auth/me/` | Current user, including `role` |
| GET, POST | `/api/children/` | List or create the caregiver's own child profiles (`concerns` is a list of domains the caregiver is worried about, e.g. `["Sensory"]`) |
| GET, PATCH, PUT, DELETE | `/api/children/<id>/` | One of the caregiver's own child profiles |

## Mobile setup

Start the backend first (`python manage.py runserver`), then:

```bash
cd mobile/nurtura_app
flutter pub get
flutter run -d chrome        # or: flutter devices, then flutter run -d <device-id>
```

The app calls the API at `http://127.0.0.1:8000` (web and desktop) or `http://10.0.2.2:8000` (Android emulator, which reaches your computer at that address). To use another server, pass `--dart-define=API_BASE_URL=https://your-server`. In development the backend accepts browser requests from any `localhost` port (CORS), so `flutter run -d chrome` works without extra setup.

App identifier: `com.sofia.nurtura_app` (Android), `com.sofia.nurturaApp` (iOS).

### End-to-end test (real backend, real browser)

`integration_test/app_flow_test.dart` drives the app in Chrome against the running backend: it registers a new caregiver, logs out and back in, creates an expecting and a born child profile, searches the milestone catalogue and records a milestone. Screenshots are saved to `build/e2e_screenshots/`.

1. Start the backend: `cd backend && python manage.py runserver`
2. Download the [ChromeDriver](https://googlechromelabs.github.io/chrome-for-testing/) that matches your Chrome version and start it: `chromedriver --port=4444`
3. From `mobile/nurtura_app`, using an email that isn't registered yet:
   ```bash
   flutter drive -d web-server --browser-name=chrome --no-headless \
     --driver=test_driver/integration_test.dart \
     --target=integration_test/app_flow_test.dart \
     --dart-define=E2E_EMAIL=new-tester@nurtura.test
   ```

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
| Backend checks | `make test` (runs all checks) | `cd backend && python manage.py check && python manage.py makemigrations --check --dry-run && python manage.py test` |
| Flutter checks | (included in `make test`) | `cd mobile/nurtura_app && flutter analyze && flutter test` |
| Format Python | (automatic on commit) | `pre-commit run --all-files` |
| Apply migrations | | `cd backend && python manage.py migrate` |
| Verify SBERT model | | `cd backend && python setup_sbert.py` |

## Continuous integration

`.github/workflows/ci.yml` runs on every push to `main` and on pull requests:

- **Backend:** installs `backend/requirements.txt` (with CPU-only PyTorch), then runs `manage.py check` and `makemigrations --check --dry-run` against SQLite.
- **Mobile:** `flutter pub get`, `flutter analyze`, `flutter test`.

## Data

See [data/README.md](data/README.md) for the activity schema, controlled vocabularies and cleaning workflow. Activities must be traceable to WHO, CDC, UNICEF, Montessori or Pathways.org guidance.
