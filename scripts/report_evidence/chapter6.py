"""Section 5: Chapter 6 inputs.

5a open issues, TODO/FIXME comments and known defects; 5b limitations
stated in the README, docs and code; 5c decisions from pull request
"decisions" sections, grouped by theme; 5d handover steps with file
references. Read-only (git, gh and the files).
"""

import json
import re
from collections import defaultdict

from _common import ROOT, grep, line_of, run, table, write_csv, write_json, write_md

COMMAND = "backend\\venv\\Scripts\\python.exe scripts\\report_evidence\\chapter6.py"
THEMES = [
    (
        "Evaluation",
        r"\b(alpha|α|ndcg|label|held-?out|evaluation|tune|test set|provenance|metric)",
    ),
    (
        "Ranking and rules",
        r"\b(rank|score|rule|priority|weight|retriev|sbert|embedding|similarity)",
    ),
    (
        "Content and data",
        r"\b(activit|milestone|catalogue|csv|seed|source|publish|draft)",
    ),
    (
        "Security and privacy",
        r"\b(token|password|throttl|privacy|consent|permission|auth|delet)",
    ),
    ("Mobile app", r"\b(app|screen|flutter|widget|offline|tab|button)"),
]


def theme(text):
    for name, pat in THEMES:
        if re.search(pat, text, re.I):
            return name
    return "Other"


def main():
    # ---- 5a ----
    issues = json.loads(
        run(
            [
                "gh",
                "issue",
                "list",
                "--state",
                "open",
                "--limit",
                "500",
                "--json",
                "number,title,labels,milestone,createdAt",
            ]
        )
        or "[]"
    )
    issue_rows = [
        {
            "issue": i["number"],
            "title": i["title"],
            "labels": ", ".join(l["name"] for l in i["labels"]),
            "milestone": (i.get("milestone") or {}).get("title", ""),
            "opened": i["createdAt"][:10],
        }
        for i in issues
    ]
    write_csv(
        "open_issues.csv",
        issue_rows,
        ["issue", "title", "labels", "milestone", "opened"],
    )
    todos = [
        {"file": f, "line": n, "text": t[:160]}
        for f, n, t in grep(
            r"\b(TODO|FIXME|XXX|HACK)\b",
            ["backend", "mobile/nurtura_app/lib", "mobile/nurtura_app/test", "scripts"],
        )
        if (f.endswith(".py") or f.endswith(".dart"))
        and "/venv/" not in f
        and "backend/models/" not in f
    ]
    write_csv("todo_fixme.csv", todos, ["file", "line", "text"])
    kl = (
        (ROOT / "docs" / "known_limitations.md")
        .read_text(encoding="utf-8")
        .splitlines()
    )

    def section(title):
        out, inside = [], False
        for i, line in enumerate(kl, 1):
            if line.startswith("## "):
                inside = line[3:].strip() == title
                continue
            if inside and line.strip() and not line.startswith(">"):
                out.append((i, line.strip()))
        return out

    defects = section("Outstanding defects")

    # ---- 5b ----
    limits = []
    for i, line in enumerate(kl, 1):
        if (
            line.startswith("- **")
            or line.startswith("| ")
            and not line.startswith("|---")
            and not line.startswith("| Item")
        ):
            limits.append(
                {
                    "source": f"docs/known_limitations.md:{i}",
                    "text": re.sub(r"\s+", " ", line.strip("-| "))[:260],
                }
            )
    for f, n, t in grep(r"(?i)\blimitation", ["README.md", "docs"]):
        if f != "docs/known_limitations.md" and "report_evidence" not in f:
            limits.append({"source": f"{f}:{n}", "text": t[:260]})
    for f, n, t in grep(
        r"(?i)(limitation|not yet supported|future work|known issue|not handled)",
        ["backend", "mobile/nurtura_app/lib"],
    ):
        if (
            (f.endswith(".py") or f.endswith(".dart"))
            and "/venv/" not in f
            and "backend/models/" not in f
            and "/test" not in f
        ):
            limits.append({"source": f"{f}:{n}", "text": t[:260]})
    write_csv("limitations.csv", limits)

    # ---- 5c ----
    prs = json.loads(
        run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "merged",
                "--limit",
                "1000",
                "--json",
                "number,title,mergedAt,body",
            ]
        )
        or "[]"
    )
    decisions = []
    for p in prs:
        lines = (p.get("body") or "").splitlines()
        inside = False
        for line in lines:
            if re.match(r"^#{1,6} ", line):
                inside = bool(re.search(r"decision", line, re.I))
                continue
            if inside and re.match(r"^\s*([-*]|\d+\.)\s+", line):
                text = re.sub(r"^\s*([-*]|\d+\.)\s+", "", line).strip()
                decisions.append(
                    {
                        "pr": p["number"],
                        "merged": p["mergedAt"][:10],
                        "pr_title": p["title"],
                        "theme": theme(text + " " + p["title"]),
                        "decision": text[:300],
                    }
                )
    decisions.sort(key=lambda d: (d["theme"], d["merged"]))
    write_csv("decision_log.csv", decisions)
    by_theme = defaultdict(list)
    for d in decisions:
        by_theme[d["theme"]].append(d)

    # ---- 5d ----
    r = "README.md"
    steps = [
        [
            "Run the backend",
            "`cd backend`, activate the venv, `pip install -r requirements-dev.txt`, `python setup_sbert.py`, `python manage.py migrate`, then `make run-backend` (or `NURTURA_MODEL_WARMUP=1 python manage.py runserver`)",
            f"{r}:{line_of(r, 'pip install -r requirements')}; Makefile:{line_of('Makefile', '^run-backend')}",
        ],
        [
            "Run the app",
            "`cd mobile/nurtura_app`, `flutter pub get`, `adb reverse tcp:8000 tcp:8000`, `flutter run -d <device> --dart-define=API_BASE_URL=http://127.0.0.1:8000`",
            "mobile/nurtura_app/README.md",
        ],
        [
            "Add an activity",
            "In the app as an administrator: Activities → add; or the web admin. New activities start as Draft",
            f"backend/activities/api.py:{line_of('backend/activities/api.py', 'class') or 1}; backend/activities/models.py:{line_of('backend/activities/models.py', 'content_status')}",
        ],
        [
            "Publish it",
            "Draft → Under Review → Published (skipping review is refused); then `python manage.py embed_activities` if the app didn't embed it",
            f"backend/activities/models.py:{line_of('backend/activities/models.py', 'content_status')}; backend/recommendations/management/commands/embed_activities.py",
        ],
        [
            "Bulk-load activities",
            "`python manage.py seed_activities` (validates every row; new rows are Draft)",
            "backend/activities/management/commands/seed_activities.py",
        ],
        [
            "Change α",
            "Set `RANKING_ALPHA` in `backend/.env` and restart; stored batches record the α they used",
            f"backend/nurtura_backend/settings.py:{line_of('backend/nurtura_backend/settings.py', '^RANKING_ALPHA')}",
        ],
        [
            "Change a rule or its weight",
            "Edit the constants or `Rule` objects, then run the tests; the ranking version changes",
            f"backend/profiles/rules/guidelines.py:{line_of('backend/profiles/rules/guidelines.py', '^NOT_YET_DEFICIT')}",
        ],
        [
            "Rerun the evaluation",
            "`python manage.py evaluate_alpha_grid --check-provenance`, then `evaluate_alpha_grid --markdown --report-alpha 0.7`, `evaluate_statistics`, `evaluate_beyond_accuracy`. A changed rule, α, activity or embedding makes the provenance check fail: label the new pool first",
            f"data/evaluation/README.md:{line_of('data/evaluation/README.md', 'provenance') or 1}",
        ],
        [
            "Regenerate this evidence pack",
            "`powershell -File scripts\\report_evidence\\run_all.ps1`",
            "scripts/report_evidence/run_all.ps1",
        ],
    ]

    write_json(
        "chapter6_summary.json",
        {
            "open_issues": len(issue_rows),
            "todo_fixme": len(todos),
            "defect_lines": len(defects),
            "limitations": len(limits),
            "decisions": len(decisions),
        },
    )
    body = f"""## 5a. Open issues, TODO/FIXME and known defects

**Open issues** (`gh issue list --state open`; `raw/open_issues.csv`): {len(issue_rows)}.

{table(['#', 'Title', 'Labels', 'Milestone', 'Opened'], [[i['issue'], i['title'], i['labels'], i['milestone'], i['opened']] for i in issue_rows]) if issue_rows else 'None.'}

**TODO / FIXME / XXX / HACK comments** in backend, app and scripts code (`raw/todo_fixme.csv`): {len(todos)}.

{table(['File', 'Line', 'Text'], [[t['file'], t['line'], t['text']] for t in todos]) if todos else 'None found.'}

**Known defects** (`docs/known_limitations.md`, "Outstanding defects"):

{chr(10).join(f'- line {i}: {t}' for i, t in defects) or '- none listed'}

## 5b. Stated limitations

{len(limits)} statements (`raw/limitations.csv`): every item in `docs/known_limitations.md`, lines that say "limitation" elsewhere in the README and docs, and code comments that state a limitation.

{table(['Source', 'Statement'], [[l['source'], l['text'].replace('|', '/')] for l in limits])}

## 5c. Decision log

From the "decisions" sections of merged pull requests ({len({d['pr'] for d in decisions})} PRs, {len(decisions)} decisions), grouped by theme by keyword. `raw/decision_log.csv`.

{chr(10).join(f"### {t}{chr(10)}{chr(10)}" + table(['Merged', 'PR', 'Decision'], [[d['merged'], f"#{d['pr']}", d['decision'].replace('|', '/')] for d in ds]) + chr(10) for t, ds in sorted(by_theme.items()))}

## 5d. Handover

{table(['Task', 'How', 'Where'], steps)}
"""
    write_md("12_chapter6_inputs.md", body, "Chapter 6 inputs", COMMAND)
    print(
        len(issue_rows),
        "open issues;",
        len(todos),
        "TODO/FIXME;",
        len(limits),
        "limitations;",
        len(decisions),
        "decisions",
    )


if __name__ == "__main__":
    main()
