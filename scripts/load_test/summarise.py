"""Summarise a load-test run into CSV and Markdown tables (#224).

Usage: python scripts/load_test/summarise.py RUN_DIR OUT_DIR
Reads Locust's step_<n>_stats.csv and peak_memory.py's memory_<n>.json for
every step in RUN_DIR and writes OUT_DIR/steps.csv (one row per step),
OUT_DIR/endpoints.csv (one row per step and endpoint) and
OUT_DIR/tables.md (both as Markdown), plus copies of the raw files.
"""

import csv
import json
import re
import shutil
import sys
from pathlib import Path


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    steps = sorted(
        int(m.group(1))
        for p in run.glob("step_*_stats.csv")
        if (m := re.match(r"step_(\d+)_stats\.csv", p.name))
    )
    step_rows, endpoint_rows = [], []
    for n in steps:
        with open(run / f"step_{n}_stats.csv", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        mem_path = run / f"memory_{n}.json"
        mem = (
            json.loads(mem_path.read_text(encoding="utf-8"))
            if mem_path.exists()
            else {}
        )
        for r in rows:
            entry = {
                "users": n,
                "endpoint": r["Name"],
                "requests": int(r["Request Count"]),
                "failures": int(r["Failure Count"]),
                "rps": round(num(r["Requests/s"]), 2),
                "p50_ms": num(r["50%"]),
                "p95_ms": num(r["95%"]),
                "p99_ms": num(r["99%"]),
                "max_ms": round(num(r["Max Response Time"])),
            }
            if r["Name"] == "Aggregated":
                step_rows.append(
                    {
                        **{k: v for k, v in entry.items() if k != "endpoint"},
                        "error_rate": (
                            round(entry["failures"] / entry["requests"], 4)
                            if entry["requests"]
                            else None
                        ),
                        "peak_rss_mb": mem.get("peak_rss_mb"),
                        "mean_cpu_percent_one_core": mem.get(
                            "mean_cpu_percent_one_core"
                        ),
                    }
                )
            else:
                endpoint_rows.append(entry)
        for p in run.glob(f"*_{n}*"):
            if p.suffix in (".csv", ".json"):
                # Tracebacks name the home folder; don't publish it.
                text = p.read_text(encoding="utf-8").replace(str(Path.home()), "<home>")
                (out / p.name).write_text(text, encoding="utf-8")
    for name in ("startup.txt",):
        if (run / name).exists():
            shutil.copy(run / name, out / name)

    def write(path, rows):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)

    write(out / "steps.csv", step_rows)
    write(out / "endpoints.csv", endpoint_rows)

    def md(rows, cols):
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        lines += [
            "| " + " | ".join("" if r[c] is None else str(r[c]) for c in cols) + " |"
            for r in rows
        ]
        return "\n".join(lines)

    text = (
        md(
            step_rows,
            [
                "users",
                "requests",
                "failures",
                "error_rate",
                "rps",
                "p50_ms",
                "p95_ms",
                "p99_ms",
                "max_ms",
                "peak_rss_mb",
                "mean_cpu_percent_one_core",
            ],
        )
        + "\n\n"
        + md(
            endpoint_rows,
            [
                "users",
                "endpoint",
                "requests",
                "failures",
                "p50_ms",
                "p95_ms",
                "p99_ms",
                "max_ms",
            ],
        )
        + "\n"
    )
    (out / "tables.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
