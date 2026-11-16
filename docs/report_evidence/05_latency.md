# Latency repeat (exploratory)

> Generated 2026-11-16T11:42:25+03:00 at commit `87b0f45` by `backend\venv\Scripts\python.exe scripts\report_evidence\latency.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

In-process `generation.generate()` for the 20 held-out children, 5 repeats each, inside a rolled-back transaction (nothing saved). Model warm in this process. Raw: `raw/latency_runs.csv`, `raw/latency_summary.json`.

| Measure | Value |
|---|---|
| Requests | 100 |
| p50 | 57.3 ms |
| p95 | 88.9 ms |
| Slowest | 321.8 ms |
| New batch stored (first repeat) | n = 20, p50 60.8 ms |
| Identical batch returned (repeats 2–5) | n = 80, p50 53.5 ms |
| Start-up (script start → model loaded and one query encoded) | 21.0 s |
| Peak working set after model load | 559 MB |
| Peak working set at the end | 612 MB |

Machine: see `02_environment.md`. Not a load test, and not over HTTP; `docs/performance_recommendations.md` has the HTTP figures and the server cold start.
