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

## Mobile setup

```bash
cd mobile/nurtura_app
flutter pub get
flutter run -d chrome        # or: flutter devices, then flutter run -d <device-id>
```

App identifier: `com.sofia.nurtura_app` (Android), `com.sofia.nurturaApp` (iOS).

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
| Clean activity data | `make seed-data` | `cd data/scripts && python clean_activities.py ../raw/activities_batch1.csv ../processed/activities_clean.csv` |
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
