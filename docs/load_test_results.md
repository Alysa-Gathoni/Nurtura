# Load test: the backend under concurrent caregivers

> **Last updated: 2026-11-16** (#224). Every figure is from the runs on that day; the raw Locust and sampler files are in [load_test/](load_test/).

## Summary

- **Up to 100 caregivers at once: no errors.** At 100, p95 is **460 ms** over all requests, **1.8 s** for generating new ideas.
- **200 at once: about half the requests failed** (500 errors). The cause is PostgreSQL's connection limit (100), not the CPU or memory. The development server opens one database connection per request in flight.
- **Server memory peaked at about 0.94 GB at 100 users** (1.2 GB at 200).
- **Server errors aren't logged.** With `DEBUG` off and no `LOGGING` or `ADMINS` set, Django sends 500 errors' details nowhere. The failures were diagnosed by counting database connections instead.

These are **indicative figures from a laptop running the development server**, not a production server. Repeat the test once the backend is hosted.

## Set-up

| Item | Value |
|---|---|
| Machine | The development laptop: AMD Ryzen 5 5625U (12 logical cores), 7.4 GB RAM, Windows 11. Locust ran on the same machine. |
| Server | `manage.py runserver 127.0.0.1:8001 --noreload` (threaded; one process), `DEBUG=False`, SBERT warmed up at start (`NURTURA_MODEL_WARMUP=1`). Started in 20–28 s. |
| Database | PostgreSQL 18.6, `max_connections` = 100. A **scratch copy** of the development database (`nurtura_loadtest`, made with `CREATE DATABASE … TEMPLATE`, dropped afterwards). The development database was never written to. |
| Users | Fictional caregivers `loadtest-NNN@nurtura.invalid`, created in the scratch copy with a token, the privacy notice agreed, and one child each (ten profiles from pregnancy to 30 months, with concerns, interests and a recorded milestone). |
| Tool | Locust 2.47.0. Each user pauses 3–10 s between actions, like a person reading a screen. |
| Steps | 10, 25, 50, 100 and 200 concurrent users, 2 minutes each, added 5 per second (10 per second for 200). |

Actions and weights (out of 24):

| Action | Endpoint | Weight |
|---|---|---|
| Open Today's ideas (generate a first batch if there is none) | `GET /api/children/<id>/recommendations/` | 10 |
| Ask for new ideas | `POST /api/children/<id>/recommendations/` | 2 |
| Browse Explore | `GET /api/children/<id>/activities/` | 3 |
| Search Explore (SBERT) | `GET /api/children/<id>/activities/?q=…` | 3 |
| Open the milestone tracker | `GET /api/children/<id>/tracker/` | 3 |
| Search milestones | `GET /api/reference-milestones/?search=…` | 2 |
| Give feedback, then view the options | `PUT …/feedback/`, `GET …/options/` | 1 |

Sign-in, registration and password endpoints weren't tested: they are throttled to 5–10 requests per minute per client by design.

## Results by step

| Users | Requests | Failed | Requests/s | p50 | p95 | p99 | Max | Peak server memory | Mean CPU (cores) |
|---|---|---|---|---|---|---|---|---|---|
| 10 | 203 | 0 | 1.7 | 85 ms | 270 ms | 370 ms | 0.6 s | 545 MB | 0.4 |
| 25 | 480 | 0 | 4.0 | 79 ms | 220 ms | 480 ms | 1.4 s | 286 MB* | 1.0 |
| 50 | 968 | 0 | 8.1 | 110 ms | 280 ms | 880 ms | 1.9 s | 704 MB | 1.7 |
| **100** | 1,793 | **0** | 15.1 | 150 ms | **460 ms** | 1.4 s | 2.8 s | **939 MB** | 3.3 |
| **200** | 2,564 | **1,242 (48%)** | 21.2 | 1.2 s | 16 s | 25 s | 32 s | 1,208 MB | 5.0 |

\* Memory is the server's working set, sampled every second. Windows can trim a working set, so a single step can read low (25 users); the peak across the run is the safer figure.

Requests per second grow with the number of users up to 100, because each user pauses between actions. The server wasn't saturated at 100: it used about 3.3 of 12 cores.

### By action at 100 users

| Action | Requests | p50 | p95 | p99 |
|---|---|---|---|---|
| Open Today's ideas | 698 | 130 ms | 290 ms | 550 ms |
| Ask for new ideas (generate) | 172 | 290 ms | **1.8 s** | 2.8 s |
| Browse Explore | 227 | 170 ms | 390 ms | 600 ms |
| Search Explore (SBERT) | 221 | 200 ms | 1.0 s | 2.2 s |
| Milestone tracker | 223 | 120 ms | 230 ms | 300 ms |
| Milestone search | 138 | 89 ms | 230 ms | 400 ms |
| Feedback | 57 | 130 ms | 400 ms | 720 ms |
| Options after feedback | 57 | 160 ms | 450 ms | 600 ms |

The two actions that run SBERT on the request (generating ideas, searching Explore) are the slowest, as expected. Every per-step and per-action figure is in [load_test/endpoints.csv](load_test/endpoints.csv).

## What failed at 200 users, and why

Every failure at 200 users was a 500 error, on every endpoint. There was also one refused connection while users were being added. The server stayed up.

The server's log had no tracebacks (see the next section). A second 60-second run at 200 users counted connections every second ([connections_200_rerun.json](load_test/connections_200_rerun.json)):

- connections to the scratch database peaked at **96**, against `max_connections` = 100 (the rest are kept for superusers and the sampler);
- new connections were refused **4 times** with *"FATAL: remaining connection slots are reserved for roles with the SUPERUSER attribute"*.

So the limit is the database connection limit. `runserver` handles each request on its own thread with its own connection. Once about 100 requests are in flight at once (more likely as SBERT requests slow down under load), new requests can't connect and fail.

## Findings for deployment

| # | Finding | Action |
|---|---|---|
| 1 | **Connections, not CPU, are the first limit.** One connection per in-flight request runs out at about 100. | Use a production server with a **fixed number of workers and threads** (for example Gunicorn with 2–3 workers × 4 threads), so connections stay well below `max_connections`. Add PgBouncer or Django's connection reuse if more are needed. |
| 2 | **Server errors leave no trace** with `DEBUG` off: no `LOGGING`, no `ADMINS`. | Add a `LOGGING` setting that writes `django.request` errors to the console or a file, so a host's logs show them. |
| 3 | **Memory grows with load**, to about 0.94 GB at 100 users in one process. Each extra worker loads its own copy of SBERT. | Keep the "at least 2 GB of RAM" plan in [deployment_requirements.md](deployment_requirements.md). Size workers to memory, not cores. |
| 4 | **Generating ideas is the slowest action** (p95 1.8 s at 100 users). | Acceptable for a button press. If it matters later, cache the child's query embedding between requests. |

## Limitations

- **Development server on Windows.** `runserver` isn't built for production; Gunicorn on Linux behaves differently (worker processes, no thread per request). These figures show the shape, not production capacity.
- **One machine.** Locust and the server shared the laptop's CPU, and there was no network between them, so there was no network latency.
- **Short steps** (2 minutes) and a database copy of development size. Long-run effects (memory creep, table growth) weren't measured.
- **"Concurrent users" means users active at the same moment**, each acting every few seconds. It isn't the number of registered or daily caregivers.

## Reproducing

From the repository root (stop any `runserver` on the development database first):

```
backend\venv\Scripts\python.exe scripts\load_test\scratch_db.py create
set DB_NAME=nurtura_loadtest
backend\venv\Scripts\python.exe scripts\load_test\setup_users.py <outside-the-repo>\users.json 200
set DB_NAME=
python -m venv scripts\load_test\.venv
scripts\load_test\.venv\Scripts\python.exe -m pip install -r scripts\load_test\requirements.txt
powershell -File scripts\load_test\run_steps.ps1 -UsersFile <...>\users.json -OutDir <run dir>
scripts\load_test\.venv\Scripts\python.exe scripts\load_test\summarise.py <run dir> docs\load_test
backend\venv\Scripts\python.exe scripts\load_test\scratch_db.py drop
```

`setup_users.py` refuses to run unless `DB_NAME` is the scratch database. Keep the users file outside the repository: it holds the test users' tokens.
