"""Count open connections to the scratch database every second (#224).

Usage (backend venv): python count_connections.py SECONDS OUT.json
Records the peak number of connections to nurtura_loadtest, and any
connection error seen while sampling (for example "too many clients").
"""

import json
import os
import sys
import time
from pathlib import Path

try:  # psycopg 3 since #226; psycopg2 before
    import psycopg as pg
except ImportError:
    import psycopg2 as pg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


def main():
    seconds, out = float(sys.argv[1]), sys.argv[2]
    load_dotenv(ROOT / "backend" / ".env")
    kwargs = dict(
        dbname="postgres",
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )
    conn = pg.connect(**kwargs)  # opened before the load, so it keeps a slot
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SHOW max_connections")
    limit = int(cur.fetchone()[0])
    counts, errors = [], []
    end = time.time() + seconds
    while time.time() < end:
        cur.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE datname = 'nurtura_loadtest'"
        )
        counts.append(cur.fetchone()[0])
        try:  # can a new client still connect?
            pg.connect(**kwargs).close()
        except pg.OperationalError as exc:
            errors.append(str(exc).strip().splitlines()[0])
        time.sleep(1)
    result = {
        "max_connections": limit,
        "peak_connections_to_scratch_db": max(counts),
        "seconds_sampled": len(counts),
        "new_connection_errors": len(errors),
        "first_error": errors[0] if errors else None,
    }
    Path(out).write_text(json.dumps(result), encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
