# Latency repeat (exploratory)

> Generated 2026-11-23T00:22:39+03:00 at commit `3966c02` by `backend\venv\Scripts\python.exe scripts\report_evidence\latency.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

In-process `generation.generate()` for the 20 held-out children, 5 repeats each, inside a rolled-back transaction (nothing saved). Model warm in this process. Raw: `raw/latency_runs.csv`, `raw/latency_summary.json`.

| Measure | Value |
|---|---|
| Requests | 100 |
| p50 | 38.0 ms |
| p95 | 90.6 ms |
| Slowest | 224.7 ms |
| New batch stored (first repeat) | n = 20, p50 86.2 ms |
| Identical batch returned (repeats 2–5) | n = 80, p50 37.2 ms |
| Start-up (script start → model loaded and one query encoded) | 15.6 s |
| Peak working set after model load | 564 MB |
| Peak working set at the end | 604 MB |

Machine: see `02_environment.md`. Not a load test, and not over HTTP; `docs/performance_recommendations.md` has the HTTP figures and the server cold start.
