# Latency repeat (exploratory)

> Generated 2026-11-23T10:50:21+03:00 at commit `36a36a4` by `backend\venv\Scripts\python.exe scripts\report_evidence\latency.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

In-process `generation.generate()` for the 20 held-out children, 5 repeats each, inside a rolled-back transaction (nothing saved). Model warm in this process. Raw: `raw/latency_runs.csv`, `raw/latency_summary.json`.

| Measure | Value |
|---|---|
| Requests | 100 |
| p50 | 39.1 ms |
| p95 | 84.8 ms |
| Slowest | 233.4 ms |
| New batch stored (first repeat) | n = 20, p50 72.1 ms |
| Identical batch returned (repeats 2–5) | n = 80, p50 38.7 ms |
| Start-up (script start → model loaded and one query encoded) | 15.8 s |
| Peak working set after model load | 565 MB |
| Peak working set at the end | 605 MB |

Machine: see `02_environment.md`. Not a load test, and not over HTTP; `docs/performance_recommendations.md` has the HTTP figures and the server cold start.
