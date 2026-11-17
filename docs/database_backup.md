# Backing up and restoring the database

> **Last updated: 2026-11-17** (#233).

The PostgreSQL database holds everything that isn't in the repository:
- the reviewed and Published activities, with their review history;
- the milestone catalogue and its `verified` flags;
- the stored SBERT embeddings;
- caregiver accounts, children, recommendations, completions and feedback.

A backup is the only way back if the database is lost or damaged.

## Rules

- **Never commit a backup or upload it anywhere public.** It contains account emails and password hashes, and any caregiver data.
- **Keep backups outside the repository** and outside cloud-synced folders (OneDrive), with a second copy on separate storage (for example a USB drive).
- **Check every backup** by restoring it (below). A backup that has never been restored isn't known to work.

## When to take one

- Before tagging a version (for example before the caregiver sessions).
- Before and after the caregiver sessions.
- Before deployment, and before any bulk change to the activities (`seed_activities`, `load_plain_aims`, publishing a batch).

## Take a backup

From PowerShell (it asks for the database user's password; the names are those in `backend/.env`):

```
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -h localhost -U nurtura_user -Fc --no-owner -f "<backup folder>\nurtura_db_<date>.dump" nurtura_db
```

`-Fc` is PostgreSQL's compressed custom format, which `pg_restore` reads. `--no-owner` lets the backup be restored under a different database user, for example on a host.

## Check it, or restore it

Restore into a **new, empty** database. Never restore over the live one.

```
& "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -h localhost -U nurtura_user nurtura_db_restored
& "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" -h localhost -U nurtura_user --no-owner -d nurtura_db_restored "<backup folder>\nurtura_db_<date>.dump"
```

- **To check it:** compare row counts with the live database. Main tables: `activities_developmentalactivity`, `profiles_referencemilestone`, `recommendations_activityembedding`, `profiles_user`, `profiles_childprofile`, `recommendations_recommendation`, `feedback_feedback`, `feedback_completedactivity`. Then drop the copy with `dropdb`.
- **To use it:** set `DB_NAME=nurtura_db_restored` in `backend/.env` and restart the backend. The evaluation's provenance check (`evaluate_alpha_grid --check-provenance`) should still match if the backup was taken from the frozen state.

## Backups taken

| Date | Database | Checked | Kept |
|---|---|---|---|
| 2026-11-17 | `nurtura_db` (development) | Restored into a temporary database with no errors. Row counts matched: activities 449, milestones 133, embeddings 449, users 8, children 7, recommendations 50, feedback 3, completions 2. | On the development laptop, outside the repository, with a README on restoring it |
