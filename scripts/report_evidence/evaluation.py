"""1f held-out evaluation tables, 1g exploratory measures, 2d figure data.

Runs evaluate_alpha_grid --markdown --report-alpha 0.7 (saved verbatim),
then recomputes every table from the same rankings and the v2 labels so the
figure data match the command. Rankings come from the 20 constructed
held-out children, created inside a transaction that is rolled back.

The v2 record is the frozen sprint9-eval-v2 state, which ranked with SBERT
only, so it runs with RETRIEVAL_BETA=1 (the app uses 0.25 since #250). The
TF-IDF comparison (#248), which chose the app's beta, is run separately with
compare_tfidf --markdown --extra-labels and summarised on the same page.
"""

import csv
import os
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


TFIDF_EXTRA = "data/evaluation/tfidf_extra.csv"


def tfidf_rows(text, heading):
    """{(ranking, beta label): nDCG@5} from one compare_tfidf table."""
    rows, inside = {}, False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.startswith("## " + heading)
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if inside and len(cells) == 8 and cells[0] in ("similarity-only", "alpha 0.7"):
            rows[(cells[0], cells[1])] = float(cells[7])
    return rows


def main():
    # The frozen v2 record ranked with SBERT only (see the module docstring).
    os.environ["RETRIEVAL_BETA"] = "1"
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

    # ---- second rater (#218) ----
    from recommendations.evaluation import ndcg_at_k
    from recommendations.statistics import (
        GRADES,
        KAPPA_WEIGHTS,
        cohen_kappa,
        confusion,
        kappa_bootstrap_ci,
        paired,
    )

    by_child = {
        c: [
            (g, labels.rater2[c][a])
            for a, g in grades.items()
            if a in labels.rater2.get(c, {})
        ]
        for c, grades in labels.relevance.items()
    }
    pairs = [p for ps in by_child.values() for p in ps]
    rater_text = "`relevance_rater2` is empty in the sheet: one rater only."
    if pairs:
        kappas = {}
        for w in KAPPA_WEIGHTS:
            value = cohen_kappa(pairs, w)
            low, high = (
                kappa_bootstrap_ci(by_child, w) if value is not None else (None, None)
            )
            kappas[w] = {"kappa": value, "ci_low": low, "ci_high": high}
        matrix = confusion(pairs)
        write_csv(
            "rater_confusion.csv",
            [
                {"first_rater": g, **{f"second_{h}": n for h, n in zip(GRADES, row)}}
                for g, row in zip(GRADES, matrix)
            ],
        )
        test_ids = [c.child_id for c in heldout.HELDOUT_CHILDREN if c.split == "test"]
        per_rater = []
        for c in test_ids:
            row = {"child": c}
            for who, grades in (("first", labels.relevance), ("second", labels.rater2)):
                for m, name in (
                    (REPORTED_ALPHA, "alpha_0.7"),
                    (heldout.BASELINE, "sbert_only"),
                ):
                    row[f"{who}_{name}"] = ndcg_at_k(
                        rankings[c][m], grades.get(c, {}), 5
                    )
            per_rater.append(row)
        write_csv("per_profile_test_by_rater.csv", per_rater)
        second = paired(
            [r["second_alpha_0.7"] for r in per_rater],
            [r["second_sbert_only"] for r in per_rater],
        )
        agreement = {
            "rows_both": len(pairs),
            "children": sum(1 for ps in by_child.values() if ps),
            "second_rater": "a registered nurse, independent of the project (role only, with their agreement)",
            "exact": mean(a == b for a, b in pairs),
            "kappa": kappas,
            "confusion_rows_first_cols_second": matrix,
            "test_second_rater": {
                "alpha_0.7": second.mean_a,
                "sbert_only": second.mean_b,
                "difference": second.mean_diff,
                "ci": [second.ci_low, second.ci_high],
                "better_tied_worse": [second.improved, second.tied, second.worse],
                "wilcoxon_p": second.p_value,
            },
        }
        write_json("rater_agreement.json", agreement)
        q = kappas["quadratic"]
        rater_text = f"""Since #218, a second rater (a registered nurse, independent of the project) has graded {len(pairs)} rows blind in `relevance_rater2` (`docs/eval_v2_statistics.md:{line_of('docs/eval_v2_statistics.md', '^## Agreement between raters')}`). Raw: `raw/rater_agreement.json`, `raw/rater_confusion.csv`, `raw/per_profile_test_by_rater.csv`. Bootstrap intervals resample children (10,000, seed 2026).

{table(['Measure', 'Value', '95% CI'], [[f"Cohen's kappa, {w}", fmt(k['kappa']), '-' if k['ci_low'] is None else f"[{k['ci_low']:.3f}, {k['ci_high']:.3f}]"] for w, k in kappas.items()] + [['Exact agreement', fmt(agreement['exact']), '-']])}

Rows: first rater (researcher); columns: second rater (nurse).

{table(['', *(f'Second {g}' for g in GRADES)], [[f'First {g}', *row] for g, row in zip(GRADES, matrix)])}

Test set on the second rater's labels: α = 0.7 {fmt(second.mean_a)} against SBERT-only {fmt(second.mean_b)}, difference {second.mean_diff:+.3f} [{second.ci_low:+.3f}, {second.ci_high:+.3f}], {second.improved}/{second.tied}/{second.worse} better/tied/worse, Wilcoxon p = {fmt(second.p_value)}. Quadratic-weighted κ (main figure): {fmt(q['kappa'])}.

{table(['Child', 'Researcher α = 0.7', 'Researcher SBERT-only', 'Nurse α = 0.7', 'Nurse SBERT-only'], [[r['child'], fmt(r['first_alpha_0.7']), fmt(r['first_sbert_only']), fmt(r['second_alpha_0.7']), fmt(r['second_sbert_only'])] for r in per_rater])}"""

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

**Who produced the labels (repository evidence):** `docs/eval_v2_results.md:{line_of('docs/eval_v2_results.md', 'graded 0/1/2 by the researcher')}`: "graded 0/1/2 by the researcher, blind (no scores, ranks or areas shown)"; first rater.

### Second rater

{rater_text}

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
    tfidf_out = StringIO()
    call_command(
        "compare_tfidf",
        "--markdown",
        "--extra-labels",
        str(ROOT / TFIDF_EXTRA),
        stdout=tfidf_out,
    )
    tfidf_text = tfidf_out.getvalue()
    write_text("tfidf_comparison_markdown.txt", tfidf_text)
    tune_t = tfidf_rows(tfidf_text, "Tune set")
    test_t = tfidf_rows(tfidf_text, "Test set (for the record)")
    betas = sorted({b for _, b in tune_t})
    chosen = re.search(r"^Chosen: (.+)\.$", tfidf_text, re.M)
    from django.conf import settings as dj_settings

    # The app's default, read from settings.py (this process runs at beta 1).
    settings_py = (BACKEND / "nurtura_backend" / "settings.py").read_text("utf-8")
    app_beta = float(
        re.search(r'getenv\("RETRIEVAL_BETA", "([0-9.]+)"\)', settings_py).group(1)
    )
    body += f"""
## TF-IDF alongside SBERT (#248) and the app's retrieval (#250)

The tables above are the frozen v2 record, ranked with SBERT only (β = 1, run here with `RETRIEVAL_BETA={dj_settings.RETRIEVAL_BETA:g}`). Since #250 the app's retrieval is `similarity = β × SBERT + (1 − β) × TF-IDF` with β = {app_beta:g} (`backend/nurtura_backend/settings.py:{line_of('backend/nurtura_backend/settings.py', '^RETRIEVAL_BETA')}`, `backend/recommendations/retrieval.py:{line_of('backend/recommendations/retrieval.py', '^def retrieval_beta')}`). The comparison below grades every top-5 pair: the v2 labels plus `{TFIDF_EXTRA}` (123 extra pairs, graded by the researcher; the nurse's grades are in `relevance_rater2`). Raw output: `raw/tfidf_comparison_markdown.txt` (`manage.py compare_tfidf --markdown --extra-labels {TFIDF_EXTRA}`). Mean nDCG@5:

{table(['β', 'Tune, similarity-only', 'Tune, α = 0.7', 'Test, similarity-only', 'Test, α = 0.7'], [[b, fmt(tune_t.get(('similarity-only', b))), fmt(tune_t.get(('alpha 0.7', b))), fmt(test_t.get(('similarity-only', b))), fmt(test_t.get(('alpha 0.7', b)))] for b in betas])}

The pre-registered rule's choice on these labels: {chosen.group(1) if chosen else 'UNKNOWN'}. The app uses β = {app_beta:g}, chosen deliberately: it is the rule's choice on the nurse's grades and within 0.004 of β = 0 on test under both raters (`docs/tfidf_comparison.md:{line_of('docs/tfidf_comparison.md', '^## Adopted')}`).
"""
    # v3 significance tests (#268), at the app's beta (this process runs at 1).
    from django.test.utils import override_settings

    v3_out = StringIO()
    with override_settings(RETRIEVAL_BETA=app_beta):
        call_command(
            "evaluate_v3_statistics",
            "--markdown",
            "--extra-labels",
            str(ROOT / TFIDF_EXTRA),
            stdout=v3_out,
        )
    v3_text = v3_out.getvalue()
    write_text("v3_statistics_markdown.txt", v3_text)
    v3_tables = re.sub(r"^## ", "### ", v3_text.split("## Paired", 1)[1], flags=re.M)
    body += f"""
## Significance tests for v3 (#268)

The app's configuration (β = {app_beta:g}, α = {REPORTED_ALPHA:g}) against SBERT only and against the v2 system (β = 1, α = {REPORTED_ALPHA:g}), on the same labels (v2 sheet plus `{TFIDF_EXTRA}`). Per-child nDCG@5 differences, bootstrap 95% CI (10,000 resamples of children, seed 2026), two-sided Wilcoxon signed-rank test; the 8 test children are primary. The plan was fixed in issue #268 before the run (`docs/eval_v3_statistics.md:{line_of('docs/eval_v3_statistics.md', '^## Plan')}`). β was chosen on the tune children, so tune figures against the v2 system aren't independent evidence. Raw output: `raw/v3_statistics_markdown.txt` (`manage.py evaluate_v3_statistics --markdown`).

### Paired{v3_tables}"""
    # Full evaluation of the current system (#270), at the app's beta.
    from _common import RAW

    full_out = StringIO()
    with override_settings(RETRIEVAL_BETA=app_beta):
        call_command(
            "evaluate_v3_full",
            "--markdown",
            "--extra-labels",
            str(ROOT / TFIDF_EXTRA),
            "--raw-dir",
            str(RAW),
            stdout=full_out,
        )
    full_text = full_out.getvalue()
    write_text("v3_full_markdown.txt", full_text)
    full_sections = re.sub(r"^## ", "### ", full_text, flags=re.M)
    body += f"""
## Full evaluation of the current system (v3)

The configuration the app uses (β = {app_beta:g}, α = {REPORTED_ALPHA:g}), evaluated in full with the v2 method, so Chapter 5 can report the current system (#270). The plan was committed before the run (`docs/eval_v3_full_plan.md:{line_of('docs/eval_v3_full_plan.md', '^## What is computed')}`). Labels: the v2 sheet plus `{TFIDF_EXTRA}`; researcher's grades unless stated. No grade is imputed and no ungraded pair counts as 0: figures that need one are UNKNOWN, and every ungraded pair is in `raw/v3_ungraded_pairs.csv` with empty grade columns. Command: `manage.py evaluate_v3_full --markdown --raw-dir docs/report_evidence/raw` (raw output `raw/v3_full_markdown.txt`). Raw tables: `raw/v3_alpha_grid.csv`, `raw/v3_test_results.csv`, `raw/v3_per_profile_by_rater.csv`, `raw/v3_rater_agreement.json`, `raw/v3_confusion.csv`, `raw/v3_beyond_accuracy.csv`, `raw/v3_rank_grade_matrix.csv`, `raw/v3_ablation.csv`, `raw/v3_explanation_check.json`, `raw/v3_label_coverage.csv`. Figures: `figures/v3_alpha_curve.png`, `figures/v3_per_profile.png`, `figures/v3_grade_by_rank.png` (see `09_figures.md`).
{full_sections}"""
    write_md("04_evaluation.md", body, "Held-out evaluation (v2 and v3)", COMMAND)
    print("ok", len(sources), "grade-0 slots")


if __name__ == "__main__":
    main()
