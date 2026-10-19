# Deployment requirements (preparation for Sprint III)

> **Last updated: 2026-10-19,** for `main` at `cddefe5`. Sprint II asks for deployment requirements and dependencies to be identified; Sprint III hosts the system. Nothing here is deployed yet, and the hosting platform is still to be agreed with the supervisor and Webmasters Kenya.

## What has to run

| Part | What it needs | Notes |
|---|---|---|
| **API and admin** (Django 6.1, Python 3.13) | A production WSGI server: `runserver` is for development only. Gunicorn on Linux is the usual choice; it isn't in `requirements.txt` yet | One process with the SBERT model loaded; more workers each load their own copy |
| **Database** | PostgreSQL (developed on 18) | A managed database, or PostgreSQL on the same server. Never SQLite in production |
| **SBERT model** (`all-MiniLM-L6-v2`) | 88 MB on disk, downloaded by `python setup_sbert.py` into `backend/models/` (or `SBERT_MODEL_PATH`) | Download it at build or deploy time; it isn't in the repository |
| **PyTorch** (CPU only) | Installed by `requirements.txt` | CI already installs the CPU-only build; no GPU is needed |
| **Static files** (admin CSS, the Nurtura admin theme) | `python manage.py collectstatic` into `STATIC_ROOT`, served by the web server or a package such as WhiteNoise (not installed yet) | Without this, the admin loses its styling in production |
| **Email** | SMTP for the sign-in codes | Gmail with an app password works for testing; a sending service or the client's domain for real use |
| **Mobile app** | A release build with the hosted address: `flutter build apk --release --dart-define=API_BASE_URL=https://…` | Needs a signing key, kept out of the repository. Release builds don't allow plain HTTP, so the API must be served over **HTTPS** |

## Measured resource use

- **Memory:** with the SBERT model loaded, the development server process had committed about **1.2 GB** (Windows, 2026-10-16). That rules out the 512 MB free tiers most hosts offer. Plan for **at least 2 GB of RAM**.
- **Start-up:** loading PyTorch and the model takes about 14–15 s. With `NURTURA_MODEL_WARMUP` on (the default when `DEBUG` is off), this happens at start-up instead of on the first request ([performance_recommendations.md](performance_recommendations.md)).
- **Disk:** the model (88 MB), plus PyTorch and the other Python packages (a few GB in a virtual environment).

## Settings for production

Environment variables, set as secrets on the host, never committed:

| Variable | Production value |
|---|---|
| `DEBUG` | `False` |
| `SECRET_KEY` | A long random value (the app refuses to start without one when `DEBUG` is off) |
| `ALLOWED_HOSTS` | The host name(s), e.g. `api.example.org` |
| `CORS_ALLOWED_ORIGINS` | Only needed if a web build of the app calls the API from a browser |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | The production database |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | The sending account |
| `NURTURA_MODEL_WARMUP` | Leave unset (on by default when `DEBUG` is off) |
| `RANKING_ALPHA` | Leave unset (uses the evaluated 0.7) |

Django's own check, run with `DEBUG=False` (`python manage.py check --deploy`), reported four warnings on 2026-10-19. All are HTTPS settings to switch on once the site is served over HTTPS:

| Warning | Setting to add |
|---|---|
| security.W004 | `SECURE_HSTS_SECONDS` |
| security.W008 | `SECURE_SSL_REDIRECT = True` |
| security.W012 | `SESSION_COOKIE_SECURE = True` |
| security.W016 | `CSRF_COOKIE_SECURE = True` |

Behind a proxy or load balancer, the admin's login form also needs `CSRF_TRUSTED_ORIGINS` set to the site's `https://` address.

## First deployment, in order

1. Create the database, set the environment variables, install the requirements and run `python setup_sbert.py`.
2. `python manage.py migrate`, then `python manage.py collectstatic`.
3. `python manage.py createsuperuser` for the first administrator.
4. Load and publish the content: `seed_activities` and `seed_milestones`, review and publish in the admin, `load_plain_aims`, then `embed_activities` (see the README). Alternatively, restore a database copy from development.
5. Start the WSGI server behind HTTPS, and check `/admin/` and `/api/auth/me/` (a 401 without a token is correct).
6. Build the release app with the hosted `API_BASE_URL` and install it on a phone.

## Platform options to decide between

| Option | Fits | Watch out for |
|---|---|---|
| A virtual server with at least 2 GB RAM (for example AWS Lightsail or EC2) | Full control; PostgreSQL can run alongside or as a managed service (AWS RDS) | Setting up HTTPS, updates and backups yourself |
| A platform service (Render, Railway and similar) on a paid tier with enough memory | Deploys from GitHub; HTTPS included | Free tiers are too small for the model; check the memory limit |
| **Cloudflare** | Cloudflare **Tunnel** can put a server (even this laptop) behind a public HTTPS address, with no open ports | Cloudflare **Workers** can't run Django or PyTorch, so the API itself must run on a server |

Whichever is chosen, the data-protection split with Webmasters Kenya (IR-10) should be agreed first. Real caregivers' data would then be on that host ([data/README.md](../data/README.md), "Access, privacy and ethics").
