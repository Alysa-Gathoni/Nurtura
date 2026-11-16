"""1h mobile facts, 1i repository numbers, 1j reader-test outputs.

Needs only git and gh (no Django). Contributor logins are redacted.
"""

import json
import re
import sys
from collections import Counter, defaultdict

from _common import APP, ROOT, grep, run, table, write_csv, write_json, write_md

COMMAND = "python scripts\\report_evidence\\mobile_and_repo.py"


def gh_json(args):
    out = run(["gh", *args])
    return json.loads(out) if out.strip() else None


def main():
    # ---- 1h ----
    screens = []
    for path in sorted((APP / "lib" / "screens").rglob("*.dart")):
        rel = path.relative_to(ROOT).as_posix()
        first = (
            run(["git", "log", "--diff-filter=A", "--format=%as %s", "--", rel])
            .strip()
            .splitlines()
        )
        cls = re.findall(
            r"^class (\w+) extends (?:StatelessWidget|StatefulWidget)",
            path.read_text(encoding="utf-8"),
            re.M,
        )
        screens.append(
            {
                "file": rel,
                "widgets": " ".join(cls[:3]),
                "added": first[-1] if first else "UNKNOWN",
            }
        )
    write_csv("mobile_screens.csv", screens)

    cache = (
        (APP / "lib" / "state" / "recommendation_cache.dart")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    cache_doc = [
        f"{i}: {l.strip()}"
        for i, l in enumerate(cache, 1)
        if l.strip().startswith("///") or "_prefix" in l
    ][:12]
    offline_tests = [
        f"{f}:{n}: {t[:110]}"
        for f, n, t in grep(
            r"testWidgets\(",
            [
                "mobile/nurtura_app/test/offline_launch_test.dart",
                "mobile/nurtura_app/test/offline_recommendations_test.dart",
            ],
        )
    ]
    footer_terms = [
        "not a medical",
        "medical check",
        "ideas, not",
        "health check",
        "footer",
    ]
    footer_hits = [
        h
        for term in footer_terms
        for h in grep(re.escape(term), ["mobile/nurtura_app/lib"], re.I)
    ]
    shots = [
        l
        for l in run(["git", "ls-files"]).splitlines()
        if re.search(r"\.(png|jpe?g)$", l, re.I)
        and not re.match(
            r"mobile/nurtura_app/(android|ios|web|windows|macos|linux)/", l
        )
    ]

    # ---- 1i ----
    repo = gh_json(["repo", "view", "--json", "url,defaultBranchRef,createdAt"])
    tags = (
        run(["git", "tag", "--list", "--format=%(refname:short) %(creatordate:short)"])
        .strip()
        .splitlines()
    )
    # Asking for commits in the list query exceeds GitHub's GraphQL node limit,
    # so each PR's commit count comes from the REST API.
    prs = (
        gh_json(
            [
                "pr",
                "list",
                "--state",
                "merged",
                "--limit",
                "1000",
                "--json",
                "number,milestone,mergedAt,body",
            ]
        )
        or []
    )
    issues = (
        gh_json(
            [
                "issue",
                "list",
                "--state",
                "closed",
                "--limit",
                "1000",
                "--json",
                "number,milestone,closedAt",
            ]
        )
        or []
    )
    owner_repo = repo["url"].split("github.com/")[1]
    for p in prs:
        count = run(
            ["gh", "api", f"repos/{owner_repo}/pulls/{p['number']}", "--jq", ".commits"]
        ).strip()
        p["commits"] = [None] * int(count) if count.isdigit() else []
    milestones = (
        gh_json(["api", f"repos/{owner_repo}/milestones?state=all&per_page=100"]) or []
    )
    # Milestones are set on issues; a PR without one takes the milestone of
    # the issue it closes ("Closes #n" in its body).
    issue_ms = {i["number"]: (i.get("milestone") or {}).get("title") for i in issues}
    for p in prs:
        if not p.get("milestone"):
            m = re.search(
                r"(?:closes|fixes|resolves) #(\d+)", p.get("body") or "", re.I
            )
            title = issue_ms.get(int(m.group(1))) if m else None
            if title:
                p["milestone"] = {"title": title}
    by_ms_issues = Counter(
        (i.get("milestone") or {}).get("title", "(none)") for i in issues
    )
    by_ms_prs = Counter((p.get("milestone") or {}).get("title", "(none)") for p in prs)
    by_ms_commits = defaultdict(int)
    for p in prs:
        by_ms_commits[(p.get("milestone") or {}).get("title", "(none)")] += len(
            p.get("commits") or []
        )
    ms_rows = [
        {
            "milestone": m["title"],
            "state": m["state"],
            "created": m["created_at"][:10],
            "closed": (m.get("closed_at") or "")[:10] or "open",
            "due": (m.get("due_on") or "")[:10],
            "closed_issues": by_ms_issues.get(m["title"], 0),
            "merged_prs": by_ms_prs.get(m["title"], 0),
            "commits_in_merged_prs": by_ms_commits.get(m["title"], 0),
        }
        for m in sorted(milestones, key=lambda m: m["created_at"])
    ]
    ms_rows.append(
        {
            "milestone": "(no milestone)",
            "state": "",
            "created": "",
            "closed": "",
            "due": "",
            "closed_issues": by_ms_issues.get("(none)", 0),
            "merged_prs": by_ms_prs.get("(none)", 0),
            "commits_in_merged_prs": by_ms_commits.get("(none)", 0),
        }
    )
    write_csv("milestones_github.csv", ms_rows)

    runs = (
        gh_json(
            [
                "run",
                "list",
                "--limit",
                "1000",
                "--json",
                "conclusion,status,headBranch,createdAt",
            ]
        )
        or []
    )
    done = [r for r in runs if r["status"] == "completed"]
    concl = Counter(r["conclusion"] for r in done)
    contributors = gh_json(["api", f"repos/{owner_repo}/contributors"]) or []
    commits_main = run(["git", "rev-list", "--count", "origin/main"]).strip()
    write_json(
        "repository.json",
        {
            "url": repo["url"],
            "default_branch": repo["defaultBranchRef"]["name"],
            "tags": tags,
            "merged_prs": len(prs),
            "closed_issues": len(issues),
            "commits_on_main": commits_main,
            "ci_conclusions": concl,
            "contributors": [
                {"login": "<redacted>", "contributions": c["contributions"]}
                for c in contributors
            ],
        },
    )

    # ---- 1j ----
    candidates = [
        l
        for l in run(["git", "ls-files"]).splitlines()
        if re.search(r"(reader|questionnaire|response|scor)", l, re.I)
    ]
    exports = [c for c in candidates if re.search(r"\.(csv|json|xlsx|txt)$", c, re.I)]

    pass_rate = (
        f"{100 * concl.get('success', 0) / len(done):.1f}%" if done else "UNKNOWN"
    )
    body = f"""## 1h. Mobile app

Screens in `mobile/nurtura_app/lib/screens/` on `main` (every file on `main` is merged). First commit that added each file: `raw/mobile_screens.csv`.

{table(['File', 'Widgets', 'Added (date, commit subject)'], [[s['file'].replace('mobile/nurtura_app/lib/screens/', ''), s['widgets'], s['added'][:90]] for s in screens])}

**Offline cache** (`mobile/nurtura_app/lib/state/recommendation_cache.dart`):

{chr(10).join('- line ' + l for l in cache_doc)}

**Launching offline:** covered by these widget tests:

{chr(10).join('- ' + t for t in offline_tests) or '- UNKNOWN'}

**"Activity ideas, not a medical check" footer:** {'found: ' + '; '.join(f'{f}:{n}' for f, n, _ in footer_hits) if footer_hits else 'not found in `mobile/nurtura_app/lib` (searched: ' + ', '.join(f'"{t}"' for t in footer_terms) + ', case-insensitive). Treat it as not built.'}

**Screenshots in the repository:** {len(shots)} files:

{chr(10).join('- `' + s + '`' for s in shots) or '- none'}

## 1i. Repository

{table(['Item', 'Value', 'How'], [
    ['URL', repo['url'], '`gh repo view`'],
    ['Default branch', repo['defaultBranchRef']['name'], '`gh repo view`'],
    ['Tags', ', '.join(tags) or 'none', '`git tag`'],
    ['Merged pull requests', len(prs), '`gh pr list --state merged`'],
    ['Closed issues', len(issues), '`gh issue list --state closed`'],
    ['Commits on main', commits_main, '`git rev-list --count origin/main`'],
    ['CI runs (completed, last ' + str(len(runs)) + ')', f"{dict(concl)}; pass rate {pass_rate}", '`gh run list`'],
    ['Contributors (GitHub)', f"{len(contributors)} (logins redacted; contributions: {[c['contributions'] for c in contributors]})", '`gh api repos/.../contributors`'],
])}

Milestones (`raw/milestones_github.csv`). Milestones are set on issues; a merged PR counts towards its own milestone or, if it has none, the milestone of the issue it closes. Commits are those in those PRs. No milestone has been closed on GitHub, so there are no close dates.

{table(['Milestone', 'State', 'Created', 'Closed', 'Closed issues', 'Merged PRs', 'Commits in merged PRs'], [[m['milestone'], m['state'], m['created'], m['closed'], m['closed_issues'], m['merged_prs'], m['commits_in_merged_prs']] for m in ms_rows])}

## 1j. Reader-test and questionnaire outputs

Files whose names mention reader, questionnaire, response or scoring: {', '.join('`' + c + '`' for c in candidates)}.

Exported responses or scorer output (CSV, JSON, XLSX or TXT among them): {', '.join(exports) if exports else 'none. **UNKNOWN**: no reader-test responses or scorer output are in the repository (the test and the caregiver sessions have not been run, or their exports were kept out of git).'}
"""
    write_md(
        "08_mobile_and_repository.md",
        body,
        "Mobile app, repository and reader test",
        COMMAND,
    )
    print(
        len(screens), "screens;", len(prs), "merged PRs;", len(issues), "closed issues"
    )


if __name__ == "__main__":
    main()
