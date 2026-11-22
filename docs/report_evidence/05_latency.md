# Latency repeat (exploratory)

> Generated 2026-11-21T23:22:34+03:00 at commit `45ea972` by `backend\venv\Scripts\python.exe scripts\report_evidence\latency.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

In-process `generation.generate()` for the 20 held-out children, 5 repeats each, inside a rolled-back transaction (nothing saved). Model warm in this process. Raw: `raw/latency_runs.csv`, `raw/latency_summary.json`.

| Measure | Value |
|---|---|
| Requests | 100 |
| p50 | 72.8 ms |
| p95 | 129.2 ms |
| Slowest | 332.2 ms |
| New batch stored (first repeat) | n = 20, p50 124.8 ms |
| Identical batch returned (repeats 2–5) | n = 80, p50 71.0 ms |
| Start-up (script start → model loaded and one query encoded) | 31.1 s |
| Peak working set after model load | 563 MB |
| Peak working set at the end | 601 MB |

Machine: see `02_environment.md`. Not a load test, and not over HTTP; `docs/performance_recommendations.md` has the HTTP figures and the server cold start.
