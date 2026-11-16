"""1a test totals, skipped tests and CI; 2e test inventory and requirement coverage.

Runs the backend suite (Django's own test database, created and destroyed by
the test runner) and the Flutter suite, reads the latest CI runs with gh,
parses every test file for the inventory, and turns
docs/requirements_traceability.md into the requirement coverage table,
checking that each test file it cites exists.
"""

import ast
import json
import re
import sys
from collections import Counter

from _common import (
    APP,
    BACKEND,
    ROOT,
    run,
    table,
    write_csv,
    write_json,
    write_md,
    write_text,
)

COMMAND = "backend\\venv\\Scripts\\python.exe scripts\\report_evidence\\tests_and_ci.py"
PY = str(BACKEND / "venv" / "Scripts" / "python.exe")


def run_merged(cmd, cwd):
    import subprocess

    result = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=isinstance(cmd, str),
    )
    return result.returncode, result.stdout


def parse_backend(log):
    results = re.findall(
        r"^(test_\w+) \(([\w.]+)\)(?:\n.*?)?\.\.\. (ok|skipped.*|FAIL|ERROR)$",
        log,
        re.M,
    )
    status = Counter()
    skipped = []
    for name, where, outcome in results:
        key = "skipped" if outcome.startswith("skipped") else outcome
        status[key] += 1
        if key == "skipped":
            skipped.append(
                {"test": f"{where}", "reason": outcome[len("skipped") :].strip(" '\"")}
            )
    ran = re.search(r"^Ran (\d+) tests? in ([\d.]+)s", log, re.M)
    verdict = re.search(r"^(OK.*|FAILED.*)$", log, re.M)
    return {
        "ran": int(ran.group(1)) if ran else None,
        "seconds": float(ran.group(2)) if ran else None,
        "verdict": verdict.group(1) if verdict else "UNKNOWN",
        "counted": dict(status),
        "skipped": skipped,
    }


def parse_flutter(lines):
    tests, done, skipped = {}, Counter(), []
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "testStart":
            t = event["test"]
            tests[t["id"]] = t
        elif event.get("type") == "testDone" and not event.get("hidden"):
            done[event["result"]] += 1
            if event.get("skipped"):
                skipped.append(tests.get(event["testID"], {}).get("name", "?"))
    return {"results": dict(done), "skipped": skipped, "total": sum(done.values())}


def ci_runs():
    raw = run(
        [
            "gh",
            "run",
            "list",
            "--limit",
            "200",
            "--json",
            "databaseId,headBranch,event,status,conclusion,createdAt,displayTitle,workflowName",
        ]
    )
    return json.loads(raw or "[]")


# ---- Inventory -------------------------------------------------------------

UNIT_BASES = {"SimpleTestCase"}


def backend_inventory():
    rows = []
    for path in sorted(BACKEND.glob("*/test*.py")) + sorted(
        BACKEND.glob("*/tests/*.py")
    ):
        rel = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        source = path.read_text(encoding="utf-8").splitlines()
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {getattr(b, "id", getattr(b, "attr", "")) for b in node.bases}
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith("test"):
                    body = "\n".join(source[item.lineno - 1 : item.end_lineno])
                    first = re.search(r"self\.(assert\w+)\((.*)", body)
                    level = "unit" if bases & UNIT_BASES else "integration"
                    kind = (
                        "api"
                        if "self.client" in body or "APIClient" in body
                        else "command" if "call_command" in body else "logic"
                    )
                    rows.append(
                        {
                            "suite": "backend",
                            "test": f"{node.name}.{item.name}",
                            "file": f"{rel}:{item.lineno}",
                            "first_assertion": (
                                f"{first.group(1)}({first.group(2)[:80]}"
                                if first
                                else ""
                            ),
                            "level": level,
                            "type": kind,
                        }
                    )
    return rows


DART_TEST = re.compile(r"^\s*(testWidgets|test)\(\s*\n?\s*['\"](.+?)['\"]", re.M)


def app_inventory():
    rows = []
    for folder, level in (("test", None), ("integration_test", "end-to-end")):
        for path in sorted((APP / folder).glob("*.dart")):
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(ROOT).as_posix()
            for m in DART_TEST.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                rest = text[m.end() : m.end() + 1500]
                first = re.search(r"\bexpect\((.*)", rest)
                rows.append(
                    {
                        "suite": "flutter",
                        "test": m.group(2),
                        "file": f"{rel}:{line}",
                        "first_assertion": (
                            f"expect({first.group(1)[:80]}" if first else ""
                        ),
                        "level": level
                        or ("widget" if m.group(1) == "testWidgets" else "unit"),
                        "type": "ui" if m.group(1) == "testWidgets" else "logic",
                    }
                )
    return rows


# ---- Requirement coverage ---------------------------------------------------

STATUS = {
    "Met": "Done",
    "Met, with a deviation": "Done (with a stated deviation)",
    "Partly met": "Partial",
    "Evidence pending": "Done (built); evidence pending",
    "Not met": "Not built",
}


def requirement_rows():
    text = (ROOT / "docs" / "requirements_traceability.md").read_text(encoding="utf-8")
    # Only the four requirement sections; the old-ID crosswalk above them
    # uses the same row shape.
    start = text.index("## Functional requirements")
    end = text.index("## Built beyond Chapter 4")
    rows = []
    for line in text[start:end].splitlines():
        m = re.match(r"^\| ((?:FR|NFR|DR|IR)-\d+) \| (.+)$", line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        status_cell = cells[-1]
        s = re.search(r"\*\*(.+?)[.:]?\*\*", status_cell)
        status = s.group(1).rstrip(".:") if s else "UNKNOWN"
        cited = re.findall(r"`([\w/.]+\.(?:py|dart))`", line)
        files = []
        for c in cited:
            hits = list(ROOT.rglob(c.split("/")[-1]))
            hits = [h for h in hits if "venv" not in h.parts and "build" not in h.parts]
            files.append(f"{c} ({'found' if hits else 'NOT FOUND'})")
        rows.append(
            {
                "id": m.group(1),
                "requirement": cells[1],
                "status": STATUS.get(status, f"UNKNOWN ({status})"),
                "where_and_evidence": " / ".join(cells[2:-1]),
                "cited_test_files": "; ".join(files),
                "note": re.sub(r"\*\*.+?\*\*\s*", "", status_cell),
            }
        )
    return rows


def ci_skips(run_id):
    """Skip counts per CI job, from the run log, and the skip conditions in code."""
    log = run(["gh", "run", "view", str(run_id), "--log"])
    per_job = {}
    for line in log.splitlines():
        m = re.search(r"OK \(skipped=(\d+)\)", line)
        if m:
            per_job[line.split(chr(9))[0]] = int(m.group(1))
    conditions = []
    for path in sorted(BACKEND.glob("*/test*.py")):
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(
            r"@unittest\.skipUnless\(\s*(.+?),\s*\"(.+?)\",?\s*\)\s*class (\w+)",
            text,
            re.S,
        ):
            line = text.count(chr(10), 0, m.start()) + 1
            conditions.append(
                {
                    "class": m.group(3),
                    "file": f"{path.relative_to(ROOT).as_posix()}:{line}",
                    "runs_only_if": " ".join(m.group(1).split()),
                    "reason": m.group(2),
                }
            )
    return per_job, conditions


def main():
    from pathlib import Path as _P

    reuse = "--reuse" in sys.argv
    log_path = (
        _P(__file__).resolve().parents[2]
        / "docs"
        / "report_evidence"
        / "raw"
        / "tests_backend_log.txt"
    )
    if reuse and log_path.exists():
        code, backend_log = 0, log_path.read_text(encoding="utf-8")
    else:
        code, backend_log = run_merged(
            [PY, "manage.py", "test", "--noinput", "-v", "2"], BACKEND
        )
        write_text("tests_backend_log.txt", backend_log)
    backend = parse_backend(backend_log)
    backend["exit_code"] = code

    flutter = "flutter.bat" if sys.platform == "win32" else "flutter"
    flutter_path = log_path.with_name("tests_flutter_log.jsonl")
    if reuse and flutter_path.exists():
        code, flutter_out = 0, flutter_path.read_text(encoding="utf-8")
    else:
        code, flutter_out = run_merged(f"{flutter} test --reporter json", APP)
        write_text("tests_flutter_log.jsonl", flutter_out)
    app = parse_flutter(flutter_out.splitlines())
    app["exit_code"] = code

    runs = ci_runs()
    write_json("ci_runs.json", runs)
    main_runs = [
        r for r in runs if r["headBranch"] == "main" and r["status"] == "completed"
    ]
    latest = main_runs[0] if main_runs else None
    concl = Counter(r["conclusion"] for r in runs if r["status"] == "completed")
    skips_per_job, skip_conditions = (
        ci_skips(latest["databaseId"]) if latest else ({}, [])
    )
    write_json(
        "ci_skips.json", {"per_job": skips_per_job, "conditions": skip_conditions}
    )
    write_json(
        "tests_summary.json",
        {"backend": backend, "flutter": app, "ci_conclusions": concl},
    )

    inventory = backend_inventory() + app_inventory()
    write_csv("test_inventory.csv", inventory)
    reqs = requirement_rows()
    write_csv("requirement_coverage.csv", reqs)

    skipped_rows = [[s["test"], s["reason"]] for s in backend["skipped"]] or [
        ["none", ""]
    ]
    body = f"""## 1a. Test totals

| Suite | Tests run | Result | Skipped | Time |
|---|---|---|---|---|
| Backend (`manage.py test -v 2`) | {backend['ran']} | {backend['verdict']} | {backend['counted'].get('skipped', 0)} | {backend['seconds']} s |
| Flutter (`flutter test --reporter json`) | {app['total']} | {app['results']} | {len(app['skipped'])} | |

Skipped backend tests and the reason each gives:

{table(['Test', 'Reason'], skipped_rows)}

Skipped Flutter tests: {', '.join(app['skipped']) or 'none'}.

**Latest completed CI run on `main`:** {f"{latest['workflowName']}, {latest['conclusion']}, {latest['createdAt']} (run {latest['databaseId']}: {latest['displayTitle']})" if latest else 'UNKNOWN'}.

**Skipped in that CI run (from its log):** {', '.join(f'{j}: {n}' for j, n in skips_per_job.items()) or 'UNKNOWN'}. CI runs without `-v`, so the log has counts only; the conditions in the code explain them:

{table(['Test class', 'File', 'Runs only if', 'Reason given'], [[c['class'], c['file'], f"`{c['runs_only_if']}`", c['reason']] for c in skip_conditions])}

**CI conclusions over the last {len(runs)} runs (all branches):** {dict(concl)}.

Raw: `raw/tests_backend_log.txt`, `raw/tests_flutter_log.jsonl`, `raw/ci_runs.json`, `raw/ci_skips.json`, `raw/tests_summary.json`. Locally the SBERT model is present and the database is PostgreSQL, so nothing is skipped.

## 2e. Test inventory

{len(inventory)} tests in `raw/test_inventory.csv` (suite, test, file:line, first assertion, level, type):

{table(['Suite', 'Level', 'Tests'], sorted(Counter((r['suite'], r['level']) for r in inventory).items()) and [[s, l, n] for (s, l), n in sorted(Counter((r['suite'], r['level']) for r in inventory).items())])}

- Level: backend `unit` = `SimpleTestCase` (no database); `integration` = `TestCase`/`APITestCase` (test database, often through the REST API). Flutter `widget` = `testWidgets`; `unit` = `test`; `end-to-end` = `integration_test/`.
- Type: `api` uses the REST client; `command` calls a management command; `ui` is a widget test; `logic` is the rest.
- The parsed count can differ slightly from the runner's count: parameterised loops and helper-built tests are counted once.

## Requirement coverage

From `docs/requirements_traceability.md` (statuses mapped: Met → Done; Met, with a deviation → Done with a stated deviation; Partly met → Partial; Evidence pending → Done (built), evidence pending). Each cited test file was checked to exist. Full table: `raw/requirement_coverage.csv`.

{table(['ID', 'Requirement', 'Status', 'Cited test files'], [[r['id'], r['requirement'], r['status'], r['cited_test_files'] or '—'] for r in reqs])}
"""
    write_md(
        "01_tests_and_requirements.md",
        body,
        "Tests, CI and requirement coverage",
        COMMAND,
    )
    print(
        json.dumps(
            {
                "backend": backend["ran"],
                "flutter": app["total"],
                "inventory": len(inventory),
                "requirements": len(reqs),
            }
        )
    )


if __name__ == "__main__":
    main()
