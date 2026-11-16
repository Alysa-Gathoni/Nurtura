# Latency repeat (exploratory)

> Generated 2026-11-12T21:58:59+03:00 at commit `1b4c11e` by `backend\venv\Scripts\python.exe scripts\report_evidence\latency.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

In-process `generation.generate()` for the 20 held-out children, 5 repeats each, inside a rolled-back transaction (nothing saved). Model warm in this process. Raw: `raw/latency_runs.csv`, `raw/latency_summary.json`.

| Measure | Value |
|---|---|
| Requests | 100 |
| p50 | 63.1 ms |
| p95 | 82.5 ms |
| Slowest | 358.1 ms |
| New batch stored (first repeat) | n = 20, p50 67.8 ms |
| Identical batch returned (repeats 2–5) | n = 80, p50 61.3 ms |
| Start-up (script start → model loaded and one query encoded) | 21.2 s |
| Peak working set after model load | 551 MB |
| Peak working set at the end | 580 MB |

Machine: see `02_environment.md`. Not a load test, and not over HTTP; `docs/performance_recommendations.md` has the HTTP figures and the server cold start.
