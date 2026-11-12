"""Shared helpers for the report evidence scripts.

Every script writes into docs/report_evidence/ and never changes the
database: reads are plain SELECTs, and anything that needs rows (fictional
children, recommendations, a request transcript) runs inside a transaction
that is always rolled back.

Run the Django scripts with the backend's Python, from the repository root:

    backend\\venv\\Scripts\\python.exe scripts\\report_evidence\\<script>.py
"""

import csv
import datetime
import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
APP = ROOT / "mobile" / "nurtura_app"
OUT = ROOT / "docs" / "report_evidence"
RAW = OUT / "raw"


def django_setup():
    """Import the backend as manage.py does (settings from backend/.env)."""
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nurtura_backend.settings")
    # Never send real email from an evidence script.
    os.environ["EMAIL_HOST"] = ""
    import django

    django.setup()


class Rollback(Exception):
    pass


@contextmanager
def rolled_back():
    """A transaction that is always rolled back: nothing is saved."""
    from django.db import transaction

    try:
        with transaction.atomic():
            yield
            raise Rollback
    except Rollback:
        pass


def commit_hash():
    return run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT).strip()


def run(cmd, cwd=ROOT, check=False):
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if check and result.returncode:
        raise RuntimeError(f"{cmd} failed: {result.stderr}")
    return result.stdout


def stamp():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def write_csv(name, rows, fields=None):
    RAW.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    fields = fields or (list(rows[0].keys()) if rows else [])
    path = RAW / name
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_json(name, data):
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / name
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def write_text(name, text, raw=True):
    folder = RAW if raw else OUT
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


def write_md(name, body, title, command):
    """A summary page with the provenance header every page carries."""
    header = (
        f"# {title}\n\n"
        f"> Generated {stamp()} at commit `{commit_hash()}` by `{command}`. "
        "Figures come from that run; UNKNOWN marks anything the script couldn't "
        "verify.\n\n"
    )
    path = OUT / name
    path.write_text(header + body.rstrip() + "\n", encoding="utf-8")
    return path


EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact(value):
    """Replace emails with <redacted>; leaves *.invalid test addresses alone."""
    if isinstance(value, str):
        return EMAIL.sub(
            lambda m: m.group(0) if m.group(0).endswith(".invalid") else "<redacted>",
            value,
        )
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def grep(pattern, paths, flags=0):
    """[(file relative to ROOT, line number, text)] for a regex over files."""
    rx = re.compile(pattern, flags)
    hits = []
    for base in paths:
        base = ROOT / base
        files = [base] if base.is_file() else sorted(base.rglob("*"))
        for f in files:
            if not f.is_file() or any(
                part
                in {
                    "venv",
                    ".venv",
                    "__pycache__",
                    "build",
                    ".dart_tool",
                    "node_modules",
                    "report_evidence",
                }
                for part in f.parts
            ):
                continue
            if f.suffix not in {
                ".py",
                ".dart",
                ".md",
                ".txt",
                ".yml",
                ".yaml",
                ".toml",
                ".xml",
                ".gradle",
                ".kts",
                ".json",
                ".csv",
                "",
            }:
                continue
            try:
                lines = f.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(lines, 1):
                if rx.search(line):
                    hits.append((f.relative_to(ROOT).as_posix(), i, line.strip()))
    return hits


def line_of(path, pattern):
    """First line number in path (relative to ROOT) matching pattern, or None."""
    rx = re.compile(pattern)
    for i, line in enumerate((ROOT / path).read_text(encoding="utf-8").splitlines(), 1):
        if rx.search(line):
            return i
    return None
