"""1f held-out evaluation tables, 1g exploratory measures, 2d figure data.

Runs evaluate_alpha_grid --markdown --report-alpha 0.7 (saved verbatim),
then recomputes every table from the same rankings and the v2 labels so the
figure data match the command. Rankings come from the 20 constructed
held-out children, created inside a transaction that is rolled back.
"""

import csv
import re
from collections import Counter, defaultdict

from _common import (
    BACKEND,
    ROOT,
    django_setup,
    line_of,
    rolled_back,
    table,
    write_csv,
    write_json,
    write_md,
    write_text,
)

COMMAND = "backend\\venv\\Scripts\\python.exe scripts\\report_evidence\\evaluation.py"
REPORTED_ALPHA = 0.7


def fmt(x):
    return "n/a" if x is None else f"{x:.3f}"


def main():
    django_setup()
    from io import StringIO

    from django.contrib.auth import get_user_model
    from django.core.management import call_command

    from activities.models import DevelopmentalActivity
    from recommendations import heldout, ranking
    from recommendations.evaluation import METRICS, load_heldout_labels, mean, score_all
    from recommendations.management.commands.evaluate_alpha_grid import DEFAULT_LABELS

    out = StringIO()
    call_command(
        "evaluate_alpha_grid",
        "--markdown",
        "--report-alpha",
        str(REPORTED_ALPHA),
        stdout=out,
    )
    write_text("alpha_grid_markdown.txt", out.getvalue())

    labels = load_heldout_labels(DEFAULT_LABELS)
    names = [n for n, _ in METRICS]
    split_of = {c.child_id: c.split for c in heldout.HELDOUT_CHILDREN}
    children = [c.child_id for c in heldout.HELDOUT_CHILDREN]
    age_of = {c.child_id: c.age_months for c in heldout.HELDOUT_CHILDREN}

    rankings = {}
    with rolled_back():
        caregiver = get_user_model().objects.create_user(
            username="evaluation-evidence@nurtura.invalid"
        )
        for child in heldout.HELDOUT_CHILDREN:
            profile = heldout.create_child(child, caregiver)
            _, rankings[child.child_id] = heldout.rankings_for(profile)
    activity = {
        a.activity_id: a
        for a in DevelopmentalActivity.objects.filter(
            activity_id__in={
                i for r in rankings.values() for ids in r.values() for i in ids[:5]
            }
        )
    }
    methods = [heldout.BASELINE, *heldout.ALPHAS]

    def label_of(m):
        return "SBERT-only" if m == heldout.BASELINE else f"alpha {m:.1f}"

    scores = {
        c: {m: score_all(rankings[c][m], labels.relevance.get(c, {})) for m in methods}
        for c in children
    }

    # Tuning curve (and test means), every metric
    curve = []
    for split in ("tune", "test"):
        ids = [c for c in children if split_of[c] == split]
        for m in methods:
            curve.append(
                {
                    "split": split,
                    "ranking": label_of(m),
                    "alpha": "" if m == heldout.BASELINE else m,
                    **{n: mean(scores[c][m][n] for c in ids) for n in names},
                }
            )
    write_csv("alpha_curve.csv", curve)

    # Per-profile test table and H17
    per = []
    for c in children:
        if split_of[c] in ("test", "gap"):
            for m in (REPORTED_ALPHA, heldout.BASELINE):
                per.append(
                    {
                        "child": c,
                        "split": split_of[c],
                        "ranking": label_of(m),
                        **scores[c][m],
                    }
                )
    write_csv("per_profile_test.csv", per)

    # Label counts and grade distribution per split
    with open(DEFAULT_LABELS, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    dist = []
    for split in heldout.SPLITS:
        r = [x for x in rows if x["split"] == split]
        g = Counter(x["relevance"].strip() for x in r)
        dist.append(
            {
                "split": split,
                "children": len({x["child_id"] for x in r}),
                "rows": len(r),
                "grade_0": g.get("0", 0),
                "grade_1": g.get("1", 0),
                "grade_2": g.get("2", 0),
                "blank": g.get("", 0),
            }
        )
    write_csv("grade_distribution.csv", dist)

    # Rank x grade matrix and grade-0 sources (test children; all children too)
    matrix, sources = [], []
    for scope, ids in (
        ("test", [c for c in children if split_of[c] == "test"]),
        ("all 20", children),
    ):
        for m in (REPORTED_ALPHA, heldout.BASELINE):
            for rank in range(1, 6):
                g = Counter()
                for c in ids:
                    a = rankings[c][m][rank - 1]
                    g[labels.relevance.get(c, {}).get(a, "unlabelled")] += 1
                matrix.append(
                    {
                        "children": scope,
                        "ranking": label_of(m),
                        "rank": rank,
                        "grade_0": g.get(0, 0),
                        "grade_1": g.get(1, 0),
                        "grade_2": g.get(2, 0),
                        "unlabelled": g.get("unlabelled", 0),
                    }
                )
    for m in (REPORTED_ALPHA, heldout.BASELINE):
        for c in children:
            for rank, a in enumerate(rankings[c][m][:5], 1):
                if labels.relevance.get(c, {}).get(a) == 0:
                    act = activity[a]
                    child_b = ranking.child_bracket(age_of[c])
                    act_b = ranking.BRACKET_INDEX.get(act.age_range)
                    rel = (
                        "prenatal"
                        if child_b is None
                        else (
                            "same band"
                            if act_b == child_b
                            else f"{act_b - child_b:+d} band(s)"
                        )
                    )
                    sources.append(
                        {
                            "ranking": label_of(m),
                            "child": c,
                            "split": split_of[c],
                            "rank": rank,
                            "activity_id": a,
                            "domain": act.developmental_domain,
                            "age_range": act.age_range,
                            "age_band_vs_child": rel,
                        }
                    )
    write_csv("rank_grade_matrix.csv", matrix)
    write_csv("grade0_sources.csv", sources)

    # 1g exploratory: domains per top 5, coverage, frequency (alpha 0.7 and baseline)
    explore, freq = [], Counter()
    for c in children:
        top = rankings[c][REPORTED_ALPHA][:5]
        base = rankings[c][heldout.BASELINE][:5]
        freq.update(top)
        explore.append(
            {
                "child": c,
                "split": split_of[c],
                "distinct_domains_alpha_0.7": len(
                    {activity[a].developmental_domain for a in top}
                ),
                "distinct_domains_sbert_only": len(
                    {activity[a].developmental_domain for a in base}
                ),
                "top5_alpha_0.7": " ".join(top),
            }
        )
    write_csv("exploratory_top5.csv", explore)
    write_csv(
        "activity_frequency_alpha_0.7.csv",
        [
            {"activity_id": a, "name": activity[a].activity_name, "times_in_a_top5": n}
            for a, n in freq.most_common()
        ],
    )
    published = DevelopmentalActivity.objects.filter(content_status="published").count()

    # v1 document rows for comparison
    v1 = (
        (ROOT / "docs" / "sprint5_alpha_results.md")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    v1_rows = [
        f"line {i}: {l}"
        for i, l in enumerate(v1, 1)
        if re.match(r"^\| (SBERT-only|\*\*α = 0\.7)", l)
    ]

    tune = [r for r in curve if r["split"] == "tune"]
    body = f"""Labels: `{DEFAULT_LABELS.relative_to(ROOT).as_posix()}`. Raw command output: `raw/alpha_grid_markdown.txt` (`manage.py evaluate_alpha_grid --markdown --report-alpha 0.7`). The tables below are recomputed from the same rankings and labels.

## 1f. Tuning curve (11 tune children, mean of each metric)

`raw/alpha_curve.csv` (also holds the test-set means). Precision counts grade ≥ 1 or grade 2 in the top k.

{table(['Ranking', *names], [[r['ranking'], *[fmt(r[n]) for n in names]] for r in tune])}

## Test children: α = 0.7 against SBERT-only (and H17 separately)

`raw/per_profile_test.csv`.

{table(['Child', 'Split', 'Ranking', *names], [[r['child'], r['split'], r['ranking'], *[fmt(r[n]) for n in names]] for r in per])}

## Labels per split

{table(['Split', 'Children', 'Rows', 'Grade 0', 'Grade 1', 'Grade 2', 'Blank'], [[d['split'], d['children'], d['rows'], d['grade_0'], d['grade_1'], d['grade_2'], d['blank']] for d in dist])}

**Who produced the labels (repository evidence):** `docs/eval_v2_results.md:{line_of('docs/eval_v2_results.md', 'graded 0/1/2 by the researcher')}`: "graded 0/1/2 by the researcher, blind (no scores, ranks or areas shown)"; `:{line_of('docs/eval_v2_results.md', 'One rater')}`: one rater. `relevance_rater2` is {'empty' if not labels.rater2 else 'partly filled'} in the sheet.

## Difference from the sprint5-eval-v1 results document

`docs/sprint5_alpha_results.md` reports the **v1** evaluation (54 activities, 205 labels; reproducible from tag `sprint5-eval-v1`). This page reports **v2** (current catalogue, `{DEFAULT_LABELS.name}`). The figures differ by design. v1 rows for comparison:

{chr(10).join('- ' + r for r in v1_rows)}

## 1g. Exploratory measures (labelled as such: not part of the fixed protocol)

- **Distinct areas in each child's top 5:** `raw/exploratory_top5.csv`. Mean at α = 0.7: {mean(e['distinct_domains_alpha_0.7'] for e in explore):.2f}; SBERT-only: {mean(e['distinct_domains_sbert_only'] for e in explore):.2f}.
- **Catalogue coverage at α = 0.7:** {len(freq)} distinct activities across the 20 top-5 lists, out of {published} Published activities (not 54: the catalogue grew after v1). The most possible is 100 (20 × 5).
- **How often each activity appears:** `raw/activity_frequency_alpha_0.7.csv`; the most frequent appears in {freq.most_common(1)[0][1] if freq else 0} top-5 lists.

{table(['Child', 'Split', 'Areas in top 5 (α = 0.7)', 'Areas (SBERT-only)'], [[e['child'], e['split'], e['distinct_domains_alpha_0.7'], e['distinct_domains_sbert_only']] for e in explore])}

## 2d. Figure data

| Figure | Data |
|---|---|
| α curve with the SBERT-only line | `raw/alpha_curve.csv` (split = tune) |
| Per-profile test nDCG@5, baseline vs α = 0.7 | `raw/per_profile_test.csv` |
| Grade distribution by split | `raw/grade_distribution.csv` |
| Rank × grade matrix (error analysis) | `raw/rank_grade_matrix.csv` |
| Where grade-0 results come from | `raw/grade0_sources.csv` |

Grade-0 results in the top 5 (all 20 children), by area and by age band relative to the child:

{table(['Ranking', 'Grade-0 slots', 'By area', 'By age band'], [[m, sum(1 for s in sources if s['ranking'] == m), dict(Counter(s['domain'] for s in sources if s['ranking'] == m)), dict(Counter(s['age_band_vs_child'] for s in sources if s['ranking'] == m))] for m in (label_of(REPORTED_ALPHA), 'SBERT-only')])}
"""
    write_md("04_evaluation.md", body, "Held-out evaluation (v2)", COMMAND)
    print("ok", len(sources), "grade-0 slots")


if __name__ == "__main__":
    main()
