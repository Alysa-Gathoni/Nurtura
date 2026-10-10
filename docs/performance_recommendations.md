# Recommendations endpoint: latency on one development machine

> **These numbers come from one development laptop, running Django's development server on Windows.** They show the order of magnitude and the effect of the model warm-up. They are not a production benchmark, and a different machine, operating system, or production server (e.g. gunicorn behind a proxy) will give different figures.

- **Measured:** 2026-10-10, on branch `docs/61-performance-note` (code at `b45f1aa`: the endpoint from #52 plus the warm-up from #58). The ranking configuration is the one evaluated at tag `sprint5-eval-v1`.
- **Script:** `backend/scripts/measure_recommendation_latency.py` (#61). Run it from `backend/` with the real model and the development database.

## Environment

| | |
|---|---|
| Machine | HP 245 14 inch G9 Notebook PC |
| CPU | AMD Ryzen 5 5625U, 6 cores / 12 threads; no GPU used (PyTorch CPU build) |
| Memory | 7.4 GB |
| OS | Windows 11 Pro 10.0.26200 |
| Python | 3.13.15 (CPython) |
| PyTorch | 2.14.0+cpu, 6 threads |
| sentence-transformers | 6.1.0 (model `all-MiniLM-L6-v2`, 384 dimensions) |
| Django / DRF | 6.1.1 / 3.18.1 |
| Database | PostgreSQL 18.6, local |
| Catalogue | 54 Published, embedded activities |

## Method

- **Children:** all **20 held-out children** (`recommendations/heldout.py`), with **5 repeats** each, interleaved (child 1 to 20, then again, five times).
  - In each repeat, every child gets one POST and then one GET.
  - The first POST per child stores a new batch (**201**, n = 20). Repeats 2–5 find an identical batch and return it (**200**, n = 80). Both paths run the full ranking.
- **A. End to end over HTTP:** `manage.py runserver` with its autoreloader and the warm-up on. The client sends real HTTP requests to 127.0.0.1 with token authentication, and the timing covers the full request (the server's work plus local HTTP overhead).
- **B. In process:** Django's test client calls the view directly, in a rolled-back transaction, with no HTTP. This isolates the endpoint's own work. The model was loaded before timing began.
- **C. Cold start:**
  - Three server starts with the warm-up **off** and three with it **on**.
  - **Startup** is the time from launching `runserver` until its port accepts connections.
  - **First POST** is the first request after that, for a child with no stored batch.
- **Percentiles:** p50 and p95 are linear-interpolation percentiles (`numpy.percentile`).
- **Test data:** temporary caregivers, tokens and children for A and C were created in the development database and deleted afterwards. B was rolled back.

## Warm latency (20 children × 5 repeats)

| | A. End to end (HTTP, dev server) p50 / p95 | B. In process p50 / p95 |
|---|---|---|
| POST, new batch stored (n = 20) | 120 / 146 ms | 28 / 34 ms |
| POST, identical batch returned (n = 80) | 112 / 143 ms | 27 / 34 ms |
| **POST, all (n = 100)** | **113 / 146 ms** | **28 / 34 ms** |
| **GET (n = 100)** | **65 / 89 ms** | **4.2 / 4.4 ms** |

- **A POST in process takes 23–36 ms in all.** That covers running the rule engine, encoding the profile query and scoring every eligible activity; the parts weren't timed separately. Storing a batch adds almost nothing: the new-batch and repeat paths are within 1 ms at p50.
- **About 60 ms of each HTTP request is overhead.** That's the development server and local HTTP on Windows: compare the GET at 65 ms over HTTP with 4 ms in process. The development server isn't built for speed, so the HTTP column is a cautious upper bound for this machine, not a target.
- **The worst single request** was a 316 ms POST over HTTP. It was a one-off in 100; the p95 is 146 ms.

## Cold start

| Warm-up (`NURTURA_MODEL_WARMUP`) | Startup | First POST | Runs |
|---|---|---|---|
| Off (the behaviour before #58) | 2.1 s | **13.9–15.2 s** | 3 |
| **On (default)** | **17.1–17.7 s** | **0.14–0.15 s** | 3 |

- **Without the warm-up**, the first request after each start pays for importing PyTorch and sentence-transformers and loading the model, about 14–15 s.
- **With it**, that cost moves to server start, and the server only accepts connections once the model is loaded, so the first caregiver's request takes about the same time as any other.
- **Model loads:** the model loads **once per serving process**. Management commands (`migrate`, `test`, `check`, …) never load it.

## Limits of these numbers

- **One machine.** These figures come from one laptop and one operating system, with nothing else under deliberate load, so background activity on the laptop adds noise. There are 100 samples per row; p95 over 100 samples rests on the slowest few requests.
- **Development server only.** A production server and network were not measured.
- **Small catalogue.** Ranking cost grows with the number of eligible activities, which is 46 post-natal or 8 prenatal here. The figures will rise as the catalogue grows.
- **No concurrent clients.** Requests were sent one at a time. Simultaneous requests for the *same* child wait for each other by design: the child row is locked during generation (#52).
