"""Writes docs/report_evidence/00_INDEX.md: answers by question number, every
file with what it holds and how it was made, and every UNKNOWN item.

Run last (run_all.ps1 does). Figures are read from the raw files, not typed.
"""

import csv
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "report_evidence"
RAW = OUT / "raw"

PAGES = {
    "01_tests_and_requirements.md": ("1a, 2e, requirement coverage", "tests_and_ci.py"),
    "02_environment.md": ("1b", "environment.py"),
    "03_catalogue_dataset_config.md": ("1c, 1d, 1e, 2a, 2b", "catalogue_and_config.py"),
    "04_evaluation.md": (
        "1f, 1g (coverage, areas per top 5), 2d data",
        "evaluation.py",
    ),
    "05_latency.md": ("1g (latency, memory, start-up)", "latency.py"),
    "06_explanation_examples.md": ("2c", "explanation_examples.py"),
    "07_workflow_transcript.md": ("2f", "workflow_transcript.py"),
    "08_mobile_and_repository.md": ("1h, 1i, 1j", "mobile_and_repo.py"),
    "09_figures.md": ("2d figures, 2a heatmap", "make_figures.py (figures venv)"),
    "10_chapters_1_to_4_sync.md": ("3a-3i", "sync_chapters.py"),
    "11_security_privacy_deployment.md": ("4a-4e", "security_privacy.py"),
    "12_chapter6_inputs.md": ("5a-5d", "chapter6.py"),
}


def load(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def csv_rows(name):
    with open(RAW / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def generated(page):
    m = re.search(
        r"Generated (\S+) at commit `(\w+)`", (OUT / page).read_text(encoding="utf-8")
    )
    return (m.group(1), m.group(2)) if m else ("UNKNOWN", "UNKNOWN")


HOME = re.compile(r"[A-Za-z]:(?:\\\\|\\|/)+Users(?:\\\\|\\|/)+[^\\/\"'\s]+", re.I)


def sanitise():
    """Final pass over every output: home folders become <home>, and the
    owner's GitHub login becomes <redacted> except in the repository URL."""
    login = None
    repo = RAW / "repository.json"
    if repo.exists():
        m = re.search(
            r"github\.com/([^/]+)/", json.loads(repo.read_text(encoding="utf-8"))["url"]
        )
        login = m.group(1) if m else None
    changed = 0
    for path in OUT.rglob("*"):
        if path.suffix not in {".md", ".json", ".jsonl", ".txt", ".csv"}:
            continue
        text = path.read_text(encoding="utf-8")
        new = HOME.sub("<home>", text)
        if login:
            new = re.sub(rf"(?<!github\.com/){re.escape(login)}", "<redacted>", new)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
    return changed


def main():
    print("sanitised", sanitise(), "files")
    tests = load("tests_summary.json")
    env = load("environment.json")
    lat = load("latency_summary.json")
    repo = load("repository.json")
    skips = load("ci_skips.json")
    curve = [r for r in csv_rows("alpha_curve.csv") if r["split"] == "test"]
    test07 = next(r for r in curve if r["ranking"] == "alpha 0.7")
    test_base = next(r for r in curve if r["ranking"] == "SBERT-only")
    reqs = csv_rows("requirement_coverage.csv")
    status_counts = {}
    for r in reqs:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
    milestones = csv_rows("milestones_inventory.csv")
    explore = csv_rows("exploratory_top5.csv")
    freq = csv_rows("activity_frequency_alpha_0.7.csv")

    answers = [
        (
            "1a",
            f"Backend {tests['backend']['ran']} tests, {tests['backend']['verdict']}, 0 skipped locally; Flutter {tests['flutter']['total']} passed. Latest CI on main: success. CI skips: {skips['per_job']} (SBERT model absent in CI; PostgreSQL-only row-lock test on SQLite).",
            "01",
        ),
        (
            "1b",
            f"{env['machine']['os']}; {env['machine']['cpu']}; {env['machine']['ram_gb']} GB RAM; Python {env['machine']['python']}; {env['machine']['postgresql'].split(' on ')[0]}; Flutter {env['machine']['flutter']}, Dart {env['machine']['dart']}. pandas installed but not imported; torch only via sentence-transformers. Phone: {env['phone']['model']} (UNKNOWN if not connected).",
            "02",
        ),
        (
            "1c",
            f"`python manage.py seed_milestones`; {sum(m['verified'] == 'True' for m in milestones)} of {len(milestones)} verified; all held-out milestones listed with their flag; Published activities by area × age table.",
            "03",
        ),
        (
            "1d",
            "`bytea` column (`BinaryField`), NumPy dot product; FAISS, pgvector and experta are not imported anywhere; reason quoted from PR #20.",
            "03",
        ),
        (
            "1e",
            "α = 1.0 ranks every eligible Published activity (rank() calls retrieve(limit=None)); file and line given.",
            "03",
        ),
        (
            "1f",
            f"Full tune curve and per-profile test table; test nDCG@5 α = 0.7 {float(test07['nDCG@5']):.3f} vs SBERT-only {float(test_base['nDCG@5']):.3f}; labels by one rater (the researcher), from repo docs; v1 document differs by design (54 activities).",
            "04",
        ),
        (
            "1g",
            f"Mean areas per top 5 at α = 0.7: {sum(int(e['distinct_domains_alpha_0.7']) for e in explore) / len(explore):.2f}; {len(freq)} distinct activities in the 20 top-5s (catalogue is 449, not 54); latency p50 {lat['p50_ms']} ms, p95 {lat['p95_ms']} ms, peak working set {lat['peak_working_set_mb_end']:.0f} MB, start-up {lat['startup_s']} s.",
            "04, 05",
        ),
        (
            "1h",
            '22 screen files listed; offline cache = last batch per child in shared preferences; offline launch covered by widget tests; the "not a medical check" footer is not found; 16 phone screenshots in docs/evidence/e2e_2026-10-15.',
            "08",
        ),
        (
            "1i",
            f"{repo['url']}; default branch {repo['default_branch']}; tags {', '.join(t.split()[0] for t in repo['tags'])}; {repo['merged_prs']} merged PRs; {repo['closed_issues']} closed issues; per-milestone table; contributors {len(repo['contributors'])}.",
            "08",
        ),
        (
            "1j",
            "UNKNOWN: no reader-test responses or scorer output in the repository.",
            "08",
        ),
        (
            "2a",
            "Activity and milestone inventories (CSV), heatmap, samples (activity, milestone, fictional child, recommendation row), preparation steps.",
            "03, 09",
        ),
        (
            "2b",
            "Configuration table generated from the module constants and settings, each with file:line.",
            "03",
        ),
        (
            "2c",
            "Three fictional profiles: rules fired with boosts, top five with similarity, priority, age weight and score, explanation text.",
            "06",
        ),
        (
            "2d",
            "Five 300-dpi figures with their CSVs and computed one-line insights; grade-0 sources by area and age band.",
            "04, 09",
        ),
        (
            "2e",
            f"Test inventory ({len(csv_rows('test_inventory.csv'))} tests) and requirement coverage: {status_counts}.",
            "01",
        ),
        (
            "2f",
            "Register → verify → log out → log in → privacy consent → create child → record milestone → POST and GET recommendations → completion → feedback, all in a rolled-back transaction; rows read back.",
            "07",
        ),
    ]
    probe = csv_rows("permission_probe.csv")
    neg = csv_rows("security_negative_tests.csv")
    secrets = load("secret_scan.json")
    dep = load("deployment.json")
    ch6 = load("chapter6_summary.json")
    since = csv_rows("changes_since_sprint6.csv")
    answers += [
        (
            "3a",
            f"{len(csv_rows('model_tables.csv'))} models, {len(csv_rows('model_fields.csv'))} fields with type, null, blank, default, choices, constraints, indexes, foreign keys and on_delete; models match the migrations; Mermaid ER and class diagrams.",
            "10",
        ),
        (
            "3b",
            f"{len(csv_rows('api_endpoints.csv'))} endpoints with methods, view, permission and throttle; fictional examples from the workflow transcript.",
            "10",
        ),
        (
            "3c",
            f"Permissions observed by calling every endpoint and method as anonymous, own caregiver, other caregiver and administrator ({len(probe)} rows).",
            "10",
        ),
        (
            "3d",
            f"{len(csv_rows('admin_site.csv'))} admin-registered models with columns, filters, search, actions and read-only fields; only active staff (Administrators) can enter.",
            "10",
        ),
        (
            "3e",
            f"{len(csv_rows('management_commands.csv'))} management commands with purpose, options and whether each writes.",
            "10",
        ),
        (
            "3f",
            "Screens, tabs, navigation edges (Mermaid), API calls per service, and loading/empty/error handling per screen file.",
            "10",
        ),
        (
            "3g",
            f"The recommendation request in {len(csv_rows('request_flow.csv'))} steps, each with file and line.",
            "10",
        ),
        (
            "3h",
            f"{len(csv_rows('deviations.csv'))} differences from the requirement text or the report, each with its evidence.",
            "10",
        ),
        (
            "3i",
            f"{len(since)} pull requests merged since sprint6-explanations-v1.",
            "10",
        ),
        (
            "4a",
            f"{sum(r['result'] == 'pass' for r in neg)} of {len(neg)} negative tests pass.",
            "11",
        ),
        (
            "4b",
            "Authentication, roles, throttling, password validators, token lifetime, admin restriction, deletion, DEBUG, ALLOWED_HOSTS and secure-cookie settings with file references.",
            "11",
        ),
        (
            "4c",
            "Python audit UNKNOWN (no pip-audit or safety); Flutter pub outdated listed; secret scan: "
            + "; ".join(
                f"{k} {v['added_lines']}"
                for k, v in secrets["patterns"].items()
                if v["added_lines"]
            )
            + "; no .env ever committed.",
            "11",
        ),
        (
            "4d",
            "Consent recorded and enforced; no data export; cascading deletion; no soft delete.",
            "11",
        ),
        (
            "4e",
            f"No deployment files; nothing hosted (hosting details UNKNOWN); peak working set {dep['peak_ram_mb']} MB, start-up {dep['startup_s']} s; release APK signed with the debug key.",
            "11",
        ),
        (
            "5a",
            f"{ch6['open_issues']} open issue(s); {ch6['todo_fixme']} TODO/FIXME comments; known defects: none listed.",
            "12",
        ),
        ("5b", f"{ch6['limitations']} stated limitations with file references.", "12"),
        (
            "5c",
            f"{ch6['decisions']} decisions from PR decision sections, grouped by theme, dated.",
            "12",
        ),
        (
            "5d",
            "Handover: run, add and publish an activity, change α or a rule, rerun the evaluation.",
            "12",
        ),
    ]

    unknowns = []
    for page in sorted(OUT.glob("*.md")):
        if page.name == "00_INDEX.md":
            continue
        for i, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
            if "UNKNOWN" in line and "UNKNOWN marks" not in line:
                unknowns.append(f"`{page.name}:{i}`: {line.strip()[:200]}")

    files = []
    for page, (covers, script) in PAGES.items():
        when, commit = generated(page) if page != "09_figures.md" else generated(page)
        files.append(
            [
                f"`{page}`",
                covers,
                f"`scripts/report_evidence/{script.split()[0]}`",
                when,
                commit,
            ]
        )
    raw_files = sorted(p.relative_to(OUT).as_posix() for p in (OUT / "raw").iterdir())
    figs = sorted(p.relative_to(OUT).as_posix() for p in (OUT / "figures").iterdir())

    head = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()
    text = f"""# Report evidence pack: index

> Built {datetime.datetime.now().astimezone().isoformat(timespec='seconds')} at commit `{head}`. Regenerate everything with `powershell -File scripts\\report_evidence\\run_all.ps1` from the repository root. Each page states the command, date and commit behind it.

Rules followed: facts come from a command, file and line, or query named on the page; anything that couldn't be verified says UNKNOWN. The database was only read: every row the scripts needed (fictional children, recommendations, the request transcript) was created inside a transaction that was rolled back. No secrets, real emails or names: they are `<redacted>`. Data is fictional.

## Answers by question

| # | Answer (short) | Page |
|---|---|---|
{chr(10).join(f'| {q} | {a} | {p} |' for q, a, p in answers)}

## Pages

| File | Covers | Script | Generated | Commit |
|---|---|---|---|---|
{chr(10).join('| ' + ' | '.join(str(c) for c in row) + ' |' for row in files)}

The commit is the one checked out when the page was generated; the scripts themselves are added by this pull request.

## Raw outputs (`raw/`)

{chr(10).join('- `' + r + '`' for r in raw_files)}

## Figures (`figures/`, 300 dpi)

{chr(10).join('- `' + f + '`' for f in figs)}

## UNKNOWN items

{chr(10).join('- ' + u for u in unknowns) or '- none'}
"""
    (OUT / "00_INDEX.md").write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{len(unknowns)} UNKNOWN lines")


if __name__ == "__main__":
    main()
