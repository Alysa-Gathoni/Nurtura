# Latency repeat (exploratory)

> Generated 2026-11-23T13:36:43+03:00 at commit `d932476` by `backend\venv\Scripts\python.exe scripts\report_evidence\latency.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

In-process `generation.generate()` for the 20 held-out children, 5 repeats each, inside a rolled-back transaction (nothing saved). Model warm in this process. Raw: `raw/latency_runs.csv`, `raw/latency_summary.json`.

| Measure | Value |
|---|---|
| Requests | 100 |
| p50 | 33.6 ms |
| p95 | 84.1 ms |
| Slowest | 236.3 ms |
| New batch stored (first repeat) | n = 20, p50 73.7 ms |
| Identical batch returned (repeats 2–5) | n = 80, p50 32.9 ms |
| Start-up (script start → model loaded and one query encoded) | 18.7 s |
| Peak working set after model load | 561 MB |
| Peak working set at the end | 597 MB |

Machine: see `02_environment.md`. Not a load test, and not over HTTP; `docs/performance_recommendations.md` has the HTTP figures and the server cold start.
