"""Create or drop the scratch database for the load test (#224).

Usage (from the repository root, with the backend venv):
    backend\\venv\\Scripts\\python.exe scripts\\load_test\\scratch_db.py create
    backend\\venv\\Scripts\\python.exe scripts\\load_test\\scratch_db.py drop

"create" copies the development database (DB_NAME in backend/.env) into
nurtura_loadtest with CREATE DATABASE ... TEMPLATE, so the load test has the
same activities, milestones and embeddings without ever writing to the
development database. PostgreSQL refuses the copy while anything else is
connected to the development database: stop runserver first.
"""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = "nurtura_loadtest"


def connect():
    load_dotenv(ROOT / "backend" / ".env")
    conn = psycopg2.connect(
        dbname="postgres",
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )
    conn.autocommit = True  # CREATE/DROP DATABASE can't run in a transaction
    return conn


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action not in ("create", "drop"):
        sys.exit("Usage: scratch_db.py create|drop")
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(f'DROP DATABASE IF EXISTS "{SCRATCH}"')
        if action == "create":
            source = os.getenv("DB_NAME")
            if not source:
                sys.exit("DB_NAME isn't set in backend/.env")
            cur.execute(f'CREATE DATABASE "{SCRATCH}" TEMPLATE "{source}"')
    finally:
        conn.close()
    print(f"{'created' if action == 'create' else 'dropped'} {SCRATCH}")


if __name__ == "__main__":
    main()
