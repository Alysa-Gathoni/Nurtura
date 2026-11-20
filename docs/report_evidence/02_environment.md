# Environment and versions

> Generated 2026-11-21T00:47:02+03:00 at commit `82ba4a5` by `backend\venv\Scripts\python.exe scripts\report_evidence\environment.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

## 1b. Machine

| Item | Value | How |
|---|---|---|
| OS | Windows 11 (10.0.26200) | `platform` |
| CPU | AMD Ryzen 5 5625U with Radeon Graphics | `Get-CimInstance Win32_Processor` |
| Logical cores | 12 | `os.cpu_count()` |
| RAM | 7.4 GB | `Get-CimInstance Win32_ComputerSystem` |
| Disk C: | 475.9 GB total, 218.1 GB free | `shutil.disk_usage` |
| Python | 3.13.15 | backend venv |
| PostgreSQL | PostgreSQL 18.6 on x86_64-windows, compiled by msvc-19.44.35228, 64-bit | `SELECT version()` |
| Flutter | 3.47.4 | `flutter --version --machine` |
| Dart | 3.13.3 | `flutter --version --machine` |
| Phone | SM-A145F, Android 15 (SDK 35) | `adb shell getprop`, read on 2026-11-16 (no phone attached at this run) |

## Libraries

Versions from the backend venv (`importlib.metadata`). "Imported by app code" searches `backend/` for `import <module>` / `from <module>` outside test files.

| Library | Version | Imported by app code | Where (first files) |
|---|---|---|---|
| Django | 6.1.1 | yes | backend/activities/admin.py:1, backend/activities/admin.py:2, backend/activities/admin.py:3 |
| djangorestframework | 3.18.1 | yes | backend/activities/api.py:16, backend/activities/api.py:17, backend/activities/api.py:18 |
| psycopg2-binary | 2.9.13 | no | used through Django's database ENGINE `django.db.backends.postgresql` (no direct import) |
| psycopg | 3.3.9 | no | — |
| torch | 2.14.0 | yes | backend/recommendations/embeddings.py:81 |
| sentence-transformers | 6.1.0 | yes | backend/recommendations/embeddings.py:78, backend/recommendations/management/commands/compare_embedding_model.py:56, backend/setup_sbert.py:32 |
| numpy | 2.5.3 | yes | backend/activities/classifier.py:28, backend/recommendations/beyond_accuracy.py:23, backend/recommendations/browse.py:21 |
| scikit-learn | 1.9.1 | yes | backend/activities/classifier.py:58, backend/activities/classifier.py:97, backend/activities/classifier.py:103 |
| pandas | 3.0.6 | no | — |
| scipy | 1.18.1 | yes | backend/recommendations/statistics.py:19 |

Raw: `raw/environment.json`.
