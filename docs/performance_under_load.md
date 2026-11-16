# Performance under load: before and after #226

> **Last updated: 2026-11-16.** Both runs used the same laptop, the same Locust scenario (signed-in caregivers pausing 3–10 s between actions), a fresh scratch copy of the development database, 2-minute steps and the development server with `DEBUG` off. The method and the "before" run are in the load-test write-up (#224, `docs/load_test_results.md`). The "after" figures are in [load_test_after_226/](load_test_after_226/).

## What #226 changed

| Change | Why |
|---|---|
| **PostgreSQL connection pool** (psycopg 3, Django's built-in pooling; `DB_POOL_MAX_SIZE` 20 by default) | Before, every request in flight opened its own connection, and at 200 users PostgreSQL's 100 ran out: about half the requests failed. Now requests wait for one of a fixed number of connections. |
| **PyTorch limited to 2 threads per encode** (`SBERT_TORCH_THREADS`) | With 6 threads per encode, overlapping requests fought over the same cores. Query vectors are bit-identical at 1, 2 and 6 threads, and one query encodes as fast with 2 (23 ms) as with 6 (22 ms). |
| **Query embeddings cached** in memory (`SBERT_QUERY_CACHE_SIZE`, 2,048 by default) | A child's unchanged profile and repeated Explore searches no longer run SBERT again. Only single-text encodes are cached; embedding activities in batches is unchanged. |
| **Server errors logged** to the console (`LOGGING`) | Before, 500 errors left no trace with `DEBUG` off. |

None of this changes what is recommended. The held-out evaluation gives the same figures (test nDCG@5 0.836 against 0.582), and the provenance check matches.

## Results

| Users at once | Failed before → after | p50 before → after | p95 before → after | p99 before → after | Server CPU (cores) before → after |
|---|---|---|---|---|---|
| 10 | 0 → 0 | 85 → 24 ms | 270 → 180 ms | 370 → 280 ms | 0.4 → 0.07 |
| 25 | 0 → 0 | 79 → 20 ms | 220 → 87 ms | 480 → 150 ms | 1.0 → 0.08 |
| 50 | 0 → 0 | 110 → 22 ms | 280 → 97 ms | 880 → 1,500 ms | 1.7 → 0.16 |
| 100 | 0 → 0 | 150 → 31 ms | 460 → 120 ms | 1,400 → 380 ms | 3.3 → 0.36 |
| **200** | **1,242 (48%) → 0** | 1,200 → 44 ms | **16 s → 350 ms** | 25 s → 940 ms | 5.0 → 0.58 |

Generating new ideas, the slowest action:

| Users at once | p95 before → after |
|---|---|
| 100 | 1.8 s → 340 ms |
| 200 | 23 s (with failures) → 710 ms |

Peak server memory stayed at or below the earlier run: 0.94 GB at 100 users before, 0.52 GB after.

## How to read it

- **The errors are fixed.** The 200-user step now completes with no failures.
- **Response times fell at every step** except the p99 at 50 users. One slow burst in that step (up to 2.4 s) wasn't repeated at 100 or 200 users.
- **Most of the CPU saving is the thread limit.** With 6 threads, PyTorch's threads busy-wait for work; with 2, much less CPU is spent waiting. The effects of the three changes weren't measured separately.
- **The cache helps this test more than it may help real use.** Each simulated child keeps the same profile, and the Explore searches come from 8 phrases, so most queries repeat. Real profile queries also repeat (a child's profile changes rarely), but real searches vary more.

## Limits

The same as the first run: the development server on Windows, Locust on the same machine, 2-minute steps. Repeat on the host after deployment, with the production server's workers × `DB_POOL_MAX_SIZE` kept below PostgreSQL's `max_connections`.
