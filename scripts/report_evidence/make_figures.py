"""2d evaluation figures and the 2a heatmap, from the CSVs in raw/.

Needs matplotlib, kept out of the app's dependencies:

    python -m venv scripts\\report_evidence\\.venv
    scripts\\report_evidence\\.venv\\Scripts\\python.exe -m pip install -r scripts\\report_evidence\\requirements-figures.txt
    scripts\\report_evidence\\.venv\\Scripts\\python.exe scripts\\report_evidence\\make_figures.py

Run the Django scripts first (evaluation.py, catalogue_and_config.py). Each
insight line is computed from the same CSV as its figure.
"""

import csv
import datetime
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "docs" / "report_evidence" / "raw"
FIG = ROOT / "docs" / "report_evidence" / "figures"
DPI = 300
COLOURS = {
    "hybrid": "#994A31",
    "baseline": "#5B7E92",
    0: "#BC5F55",
    1: "#CF9B33",
    2: "#6A8763",
    "unlabelled": "#B6A796",
}


def rows(name):
    with open(RAW / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def alpha_curve():
    data = [r for r in rows("alpha_curve.csv") if r["split"] == "tune"]
    base = next(r for r in data if r["ranking"] == "SBERT-only")
    pts = [
        (float(r["alpha"]), float(r["nDCG@5"]), float(r["nDCG@3"]))
        for r in data
        if r["alpha"]
    ]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.plot(
        [p[0] for p in pts],
        [p[1] for p in pts],
        marker="o",
        color=COLOURS["hybrid"],
        label="Hybrid nDCG@5",
    )
    ax.plot(
        [p[0] for p in pts],
        [p[2] for p in pts],
        marker="s",
        ls="--",
        color=COLOURS["hybrid"],
        alpha=0.6,
        label="Hybrid nDCG@3",
    )
    ax.axhline(
        float(base["nDCG@5"]),
        color=COLOURS["baseline"],
        ls=":",
        label="SBERT-only nDCG@5",
    )
    ax.axvline(0.7, color="grey", lw=0.8)
    ax.set_xlabel("α (weight of rule priority)")
    ax.set_ylabel("Mean over 11 tune children")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8)
    save(fig, "alpha_curve.png")
    best = max(pts, key=lambda p: p[1])
    at07 = next(p for p in pts if abs(p[0] - 0.7) < 1e-9)
    return f"Tune nDCG@5 is {min(p[1] for p in pts if p[0] >= 0.2):.3f}–{max(p[1] for p in pts if p[0] >= 0.2):.3f} for α 0.2–1.0 (highest {best[1]:.3f} at α = {best[0]:.1f}); α = 0.7 gives {at07[1]:.3f} against {float(base['nDCG@5']):.3f} for SBERT-only."


def per_profile():
    data = rows("per_profile_test.csv")
    kids = list(dict.fromkeys(r["child"] for r in data))
    get = {(r["child"], r["ranking"]): float(r["nDCG@5"]) for r in data}
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    x = range(len(kids))
    ax.bar(
        [i - 0.2 for i in x],
        [get[(k, "SBERT-only")] for k in kids],
        0.4,
        color=COLOURS["baseline"],
        label="SBERT-only",
    )
    ax.bar(
        [i + 0.2 for i in x],
        [get[(k, "alpha 0.7")] for k in kids],
        0.4,
        color=COLOURS["hybrid"],
        label="α = 0.7",
    )
    ax.set_xticks(list(x), [k + (" (gap)" if k == "H17" else "") for k in kids])
    ax.set_ylabel("nDCG@5")
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False, fontsize=8)
    save(fig, "per_profile_test_ndcg5.png")
    test = [k for k in kids if k != "H17"]
    better = sum(get[(k, "alpha 0.7")] > get[(k, "SBERT-only")] + 1e-9 for k in test)
    return f"α = 0.7 scores higher than SBERT-only for {better} of {len(test)} test children; H17 (content gap) is shown separately."


def grades():
    data = rows("grade_distribution.csv")
    fig, ax = plt.subplots(figsize=(5, 3.2))
    bottom = [0] * len(data)
    for g in ("grade_0", "grade_1", "grade_2"):
        vals = [int(r[g]) for r in data]
        ax.bar(
            [r["split"] for r in data],
            vals,
            bottom=bottom,
            color=COLOURS[int(g[-1])],
            label=g.replace("_", " "),
        )
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylabel("Labelled rows")
    ax.legend(frameon=False, fontsize=8)
    save(fig, "grade_distribution.png")
    total = sum(int(r["rows"]) for r in data)
    zeros = sum(int(r["grade_0"]) for r in data)
    return f"{total} labelled rows; {zeros} ({100 * zeros / total:.0f}%) graded 0 (not relevant)."


def matrix():
    data = [r for r in rows("rank_grade_matrix.csv") if r["children"] == "test"]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.2), sharey=True)
    for ax, ranking in zip(axes, ("alpha 0.7", "SBERT-only")):
        part = [r for r in data if r["ranking"] == ranking]
        bottom = [0] * 5
        for g in ("grade_0", "grade_1", "grade_2", "unlabelled"):
            vals = [int(r[g]) for r in part]
            key = "unlabelled" if g == "unlabelled" else int(g[-1])
            ax.bar(
                [int(r["rank"]) for r in part],
                vals,
                bottom=bottom,
                color=COLOURS[key],
                label=g.replace("_", " "),
            )
            bottom = [b + v for b, v in zip(bottom, vals)]
        ax.set_title("α = 0.7" if ranking == "alpha 0.7" else "SBERT-only", fontsize=10)
        ax.set_xlabel("Rank")
    axes[0].set_ylabel("Test children (8)")
    axes[1].legend(frameon=False, fontsize=8)
    save(fig, "rank_grade_matrix.png")
    z = {
        k: sum(int(r["grade_0"]) for r in data if r["ranking"] == k)
        for k in ("alpha 0.7", "SBERT-only")
    }
    src = rows("grade0_sources.csv")
    wrong_band = sum(
        1
        for s in src
        if s["ranking"] == "SBERT-only"
        and s["age_band_vs_child"] not in ("same band", "prenatal")
    )
    base_total = sum(1 for s in src if s["ranking"] == "SBERT-only")
    hybrid_same = sum(
        1
        for s in src
        if s["ranking"] == "alpha 0.7" and s["age_band_vs_child"] == "same band"
    )
    hybrid_total = sum(1 for s in src if s["ranking"] == "alpha 0.7")
    return f"Grade-0 slots in the test top 5: {z['alpha 0.7']} at α = 0.7, {z['SBERT-only']} for SBERT-only. Across all 20 children, {wrong_band} of SBERT-only's {base_total} grade-0 results are from another age band; {hybrid_same} of α = 0.7's {hybrid_total} are from the child's own band."


def heatmap():
    data = rows("published_by_domain_age.csv")
    ages = [k for k in data[0] if k != "domain"]
    vals = [[int(r[a]) for a in ages] for r in data]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    im = ax.imshow(vals, cmap="YlOrBr")
    ax.set_xticks(range(len(ages)), ages, rotation=30, ha="right")
    ax.set_yticks(range(len(data)), [r["domain"] for r in data])
    for i, row in enumerate(vals):
        for j, v in enumerate(row):
            ax.text(j, i, v, ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Published activities")
    save(fig, "published_heatmap.png")
    flat = [v for r in vals for v in r]
    return f"{sum(flat)} Published activities; every area × age cell has between {min(flat)} and {max(flat)}."


# v3 figures (#270): white background, black and grey only, print-sized text.
GREY = {
    "full": "#000000",
    "hybrid": "#7A7A7A",
    "sbert": "#BDBDBD",
    0: "#000000",
    1: "#8C8C8C",
    2: "#D9D9D9",
    "ungraded": "#FFFFFF",
}
PRINT = {
    "font.size": 11,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "text.color": "black",
    "axes.labelcolor": "black",
    "axes.edgecolor": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
}


def number(text):
    return float(text) if text not in ("", None) else None


def v3_alpha_curve():
    data = rows("v3_alpha_grid.csv")
    pts = [r for r in data if r["alpha"]]
    base = {r["setting"]: r for r in data if not r["alpha"]}
    with plt.rc_context(PRINT):
        fig, ax = plt.subplots(figsize=(6.5, 4))
        for split, style, marker in (("tune", "-", "o"), ("test", "--", "s")):
            known = [
                (float(r["alpha"]), number(r[f"{split}_ndcg5"]))
                for r in pts
                if number(r[f"{split}_ndcg5"]) is not None
            ]
            ax.plot(
                [a for a, _ in known],
                [v for _, v in known],
                ls=style,
                marker=marker,
                color="black",
                mfc="white" if split == "test" else "black",
                label=f"v3 ranking, {split}",
            )
        for name, ls in (("SBERT only", ":"), ("Hybrid retrieval only", "-.")):
            ax.axhline(
                number(base[name]["test_ndcg5"]),
                color="#555555",
                ls=ls,
                lw=1,
                label=f"{name}, test",
            )
        ax.axvline(0.7, color="#999999", lw=0.8)
        ax.text(0.71, 0.96, "α = 0.7 (app)", color="black", fontsize=9, va="top")
        ax.set_xlabel("α (weight of rule priority)")
        ax.set_ylabel("Mean nDCG@5")
        ax.set_xlim(-0.03, 1.03)
        ax.set_ylim(0, 1)
        ax.legend(frameon=False, loc="lower left")
        save(fig, "v3_alpha_curve.png")
    missing = [r["alpha"] for r in pts if number(r["tune_ndcg5"]) is None]
    at07 = next(r for r in pts if r["alpha"] == "0.7")
    return (
        f"At β = 0.25, α = 0.7 gives tune {float(at07['tune_ndcg5']):.3f} and test "
        f"{float(at07['test_ndcg5']):.3f}; SBERT only gives test "
        f"{float(base['SBERT only']['test_ndcg5']):.3f}. Not plotted (ungraded pairs, "
        f"UNKNOWN): α {', '.join(missing) or 'none'}."
    )


def v3_per_profile():
    data = rows("v3_per_profile_by_rater.csv")
    kids = list(dict.fromkeys(r["child"] for r in data))
    get = {(r["child"], r["rater"]): r for r in data}
    with plt.rc_context(PRINT):
        fig, axes = plt.subplots(2, 1, figsize=(7, 5.6), sharex=True)
        for ax, rater in zip(axes, ("researcher", "nurse")):
            x = range(len(kids))
            for offset, key, label in (
                (-0.27, "sbert_only", "SBERT only"),
                (0, "hybrid_only", "Hybrid retrieval only"),
                (0.27, "full", "v3, α = 0.7"),
            ):
                ax.bar(
                    [i + offset for i in x],
                    [number(get[(k, rater)][key]) or 0 for k in kids],
                    0.27,
                    color=GREY[
                        {
                            "sbert_only": "sbert",
                            "hybrid_only": "hybrid",
                            "full": "full",
                        }[key]
                    ],
                    edgecolor="black",
                    linewidth=0.5,
                    label=label,
                )
            ax.set_ylabel(f"nDCG@5\n({rater})")
            ax.set_ylim(0, 1.05)
        axes[1].set_xticks(
            list(range(len(kids))), [k + (" (gap)" if k == "H17" else "") for k in kids]
        )
        axes[0].legend(
            frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.22)
        )
        save(fig, "v3_per_profile.png")
    test = [k for k in kids if k != "H17"]
    better = {
        rater: sum(
            float(get[(k, rater)]["full"]) > float(get[(k, rater)]["sbert_only"]) + 1e-9
            for k in test
        )
        for rater in ("researcher", "nurse")
    }
    return (
        f"v3 (α = 0.7) beats SBERT only for {better['researcher']} of {len(test)} test "
        f"children on the researcher's grades and {better['nurse']} of {len(test)} on "
        "the nurse's; H17 (content gap) is shown separately."
    )


def v3_grade_by_rank():
    data = [r for r in rows("v3_rank_grade_matrix.csv") if r["children"] == "all 20"]
    settings_ = list(dict.fromkeys(r["setting"] for r in data))
    with plt.rc_context(PRINT):
        fig, axes = plt.subplots(1, 2, figsize=(8, 3.6), sharey=True)
        for ax, setting in zip(axes, settings_):
            part = [r for r in data if r["setting"] == setting]
            bottom = [0] * len(part)
            for g, key in (
                ("grade_2", 2),
                ("grade_1", 1),
                ("grade_0", 0),
                ("ungraded", "ungraded"),
            ):
                vals = [int(r[g]) for r in part]
                ax.bar(
                    [int(r["rank"]) for r in part],
                    vals,
                    bottom=bottom,
                    color=GREY[key],
                    edgecolor="black",
                    linewidth=0.5,
                    label=g.replace("_", " "),
                )
                bottom = [b + v for b, v in zip(bottom, vals)]
            ax.set_title(
                "v3, α = 0.7" if setting.startswith("alpha") else setting, fontsize=11
            )
            ax.set_xlabel("Rank position")
        axes[0].set_ylabel("Profiles (all 20)")
        axes[1].legend(frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
        save(fig, "v3_grade_by_rank.png")
    zero = {
        s: sum(int(r["grade_0"]) for r in data if r["setting"] == s) for s in settings_
    }
    return (
        "Grade-0 slots in the top 5 across all 20 profiles: "
        + ", ".join(f"{s}: {n}" for s, n in zero.items())
        + "."
    )


def main():
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()
    figures = [
        (
            "alpha_curve.png",
            "α curve with the SBERT-only line (tune)",
            "raw/alpha_curve.csv",
            alpha_curve(),
        ),
        (
            "per_profile_test_ndcg5.png",
            "Per-profile test nDCG@5, SBERT-only vs α = 0.7",
            "raw/per_profile_test.csv",
            per_profile(),
        ),
        (
            "grade_distribution.png",
            "Grade distribution by split",
            "raw/grade_distribution.csv",
            grades(),
        ),
        (
            "rank_grade_matrix.png",
            "Rank × grade, test children (error analysis)",
            "raw/rank_grade_matrix.csv, raw/grade0_sources.csv",
            matrix(),
        ),
        (
            "published_heatmap.png",
            "Published activities by area × age band",
            "raw/published_by_domain_age.csv",
            heatmap(),
        ),
        (
            "v3_alpha_curve.png",
            "v3 (β = 0.25): nDCG@5 against α, tune and test, with both similarity-only baselines",
            "raw/v3_alpha_grid.csv",
            v3_alpha_curve(),
        ),
        (
            "v3_per_profile.png",
            "v3: per-profile nDCG@5 (8 test children and H17), both raters",
            "raw/v3_per_profile_by_rater.csv",
            v3_per_profile(),
        ),
        (
            "v3_grade_by_rank.png",
            "v3: grade by rank position, all 20 profiles, α = 0.7 and SBERT only",
            "raw/v3_rank_grade_matrix.csv",
            v3_grade_by_rank(),
        ),
    ]
    lines = [
        "# Figures\n",
        f"> Generated {datetime.datetime.now().astimezone().isoformat(timespec='seconds')} at commit `{commit}` by `scripts\\report_evidence\\.venv\\Scripts\\python.exe scripts\\report_evidence\\make_figures.py`. PNG at {DPI} dpi.\n",
        "| Figure | Shows | Data | Insight |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| `figures/{f}` | {what} | `{csv_}` | {insight} |"
        for f, what, csv_, insight in figures
    ]
    lines.append("")
    lines += [f"![{what}](figures/{f})\n" for f, what, _, _ in figures]
    (ROOT / "docs" / "report_evidence" / "09_figures.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(i for *_, i in figures))


if __name__ == "__main__":
    main()
