# Latency repeat (exploratory)

> Generated 2026-11-21T22:28:38+03:00 at commit `48210e2` by `backend\venv\Scripts\python.exe scripts\report_evidence\latency.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

In-process `generation.generate()` for the 20 held-out children, 5 repeats each, inside a rolled-back transaction (nothing saved). Model warm in this process. Raw: `raw/latency_runs.csv`, `raw/latency_summary.json`.

| Measure | Value |
|---|---|
| Requests | 100 |
| p50 | 33.8 ms |
| p95 | 65.1 ms |
| Slowest | 235.3 ms |
| New batch stored (first repeat) | n = 20, p50 61.0 ms |
| Identical batch returned (repeats 2–5) | n = 80, p50 33.1 ms |
| Start-up (script start → model loaded and one query encoded) | 13.7 s |
| Peak working set after model load | 565 MB |
| Peak working set at the end | 603 MB |

Machine: see `02_environment.md`. Not a load test, and not over HTTP; `docs/performance_recommendations.md` has the HTTP figures and the server cold start.
