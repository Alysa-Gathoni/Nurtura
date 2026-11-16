| users | requests | failures | error_rate | rps | p50_ms | p95_ms | p99_ms | max_ms | peak_rss_mb | mean_cpu_percent_one_core |
|---|---|---|---|---|---|---|---|---|---|---|
| 10 | 203 | 0 | 0.0 | 1.72 | 85.0 | 270.0 | 370.0 | 554 | 545.2 | 35.5 |
| 25 | 480 | 0 | 0.0 | 4.04 | 79.0 | 220.0 | 480.0 | 1420 | 285.7 | 100.2 |
| 50 | 968 | 0 | 0.0 | 8.13 | 110.0 | 280.0 | 880.0 | 1923 | 704.3 | 172.9 |
| 100 | 1793 | 0 | 0.0 | 15.07 | 150.0 | 460.0 | 1400.0 | 2809 | 939.0 | 329.0 |
| 200 | 2564 | 1242 | 0.4844 | 21.16 | 1200.0 | 16000.0 | 25000.0 | 32387 | 1208.1 | 495.7 |

| users | endpoint | requests | failures | p50_ms | p95_ms | p99_ms | max_ms |
|---|---|---|---|---|---|---|---|
| 10 | GET Explore (browse) | 28 | 0 | 100.0 | 220.0 | 270.0 | 272 |
| 10 | GET Explore (search, SBERT) | 21 | 0 | 110.0 | 170.0 | 550.0 | 554 |
| 10 | GET milestone search | 18 | 0 | 57.0 | 180.0 | 180.0 | 179 |
| 10 | GET milestone tracker | 26 | 0 | 66.0 | 310.0 | 310.0 | 312 |
| 10 | GET options after feedback | 11 | 0 | 84.0 | 180.0 | 180.0 | 182 |
| 10 | GET recommendations (Today) | 69 | 0 | 75.0 | 220.0 | 320.0 | 321 |
| 10 | POST recommendations (generate) | 19 | 0 | 150.0 | 390.0 | 390.0 | 389 |
| 10 | PUT feedback | 11 | 0 | 79.0 | 220.0 | 220.0 | 223 |
| 25 | GET Explore (browse) | 45 | 0 | 84.0 | 190.0 | 250.0 | 246 |
| 25 | GET Explore (search, SBERT) | 62 | 0 | 97.0 | 270.0 | 350.0 | 352 |
| 25 | GET milestone search | 43 | 0 | 51.0 | 160.0 | 230.0 | 226 |
| 25 | GET milestone tracker | 41 | 0 | 59.0 | 130.0 | 140.0 | 145 |
| 25 | GET options after feedback | 12 | 0 | 98.0 | 190.0 | 190.0 | 189 |
| 25 | GET recommendations (Today) | 212 | 0 | 68.0 | 190.0 | 230.0 | 266 |
| 25 | POST recommendations (generate) | 53 | 0 | 140.0 | 1100.0 | 1400.0 | 1420 |
| 25 | PUT feedback | 12 | 0 | 74.0 | 130.0 | 130.0 | 127 |
| 50 | GET Explore (browse) | 111 | 0 | 120.0 | 270.0 | 1800.0 | 1923 |
| 50 | GET Explore (search, SBERT) | 130 | 0 | 150.0 | 410.0 | 1100.0 | 1319 |
| 50 | GET milestone search | 74 | 0 | 64.0 | 240.0 | 1800.0 | 1849 |
| 50 | GET milestone tracker | 102 | 0 | 79.0 | 190.0 | 870.0 | 1784 |
| 50 | GET options after feedback | 45 | 0 | 130.0 | 220.0 | 250.0 | 252 |
| 50 | GET recommendations (Today) | 381 | 0 | 94.0 | 210.0 | 880.0 | 1816 |
| 50 | POST recommendations (generate) | 80 | 0 | 210.0 | 410.0 | 550.0 | 551 |
| 50 | PUT feedback | 45 | 0 | 94.0 | 260.0 | 280.0 | 282 |
| 100 | GET Explore (browse) | 227 | 0 | 170.0 | 390.0 | 600.0 | 698 |
| 100 | GET Explore (search, SBERT) | 221 | 0 | 200.0 | 1000.0 | 2200.0 | 2591 |
| 100 | GET milestone search | 138 | 0 | 89.0 | 230.0 | 400.0 | 567 |
| 100 | GET milestone tracker | 223 | 0 | 120.0 | 230.0 | 300.0 | 400 |
| 100 | GET options after feedback | 57 | 0 | 160.0 | 450.0 | 600.0 | 597 |
| 100 | GET recommendations (Today) | 698 | 0 | 130.0 | 290.0 | 550.0 | 820 |
| 100 | POST recommendations (generate) | 172 | 0 | 290.0 | 1800.0 | 2800.0 | 2809 |
| 100 | PUT feedback | 57 | 0 | 130.0 | 400.0 | 720.0 | 720 |
| 200 | GET Explore (browse) | 284 | 130 | 860.0 | 3500.0 | 9300.0 | 10303 |
| 200 | GET Explore (search, SBERT) | 228 | 120 | 3000.0 | 22000.0 | 27000.0 | 28170 |
| 200 | GET milestone search | 175 | 93 | 600.0 | 3200.0 | 6800.0 | 9034 |
| 200 | GET milestone tracker | 217 | 107 | 720.0 | 2900.0 | 7600.0 | 10266 |
| 200 | GET options after feedback | 74 | 28 | 5500.0 | 7400.0 | 7800.0 | 7795 |
| 200 | GET recommendations (Today) | 842 | 409 | 750.0 | 3500.0 | 7500.0 | 7997 |
| 200 | POST recommendations (generate) | 669 | 323 | 6300.0 | 23000.0 | 27000.0 | 32387 |
| 200 | PUT feedback | 75 | 32 | 940.0 | 6700.0 | 8200.0 | 8215 |
