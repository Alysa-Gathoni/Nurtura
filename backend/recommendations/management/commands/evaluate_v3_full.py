"""Full offline evaluation of the current system, v3 (#270).

Usage (from backend/):
    python manage.py evaluate_v3_full [--labels PATH] [--extra-labels PATH]
        [--markdown] [--raw-dir PATH]

v3 is the configuration the app uses: retrieval mixing SBERT and TF-IDF at
settings.RETRIEVAL_BETA (0.25) and the ranking at settings.RANKING_ALPHA
(0.7). The plan was fixed in docs/eval_v3_full_plan.md (issue #270) before
the run. In short: the alpha grid with the pre-registered rule, test results
against two similarity-only baselines (SBERT only at beta 1; hybrid retrieval
only), per-profile results on both raters' labels, agreement between the
raters, beyond-accuracy measures, an ablation and an explanation check.

Label coverage: grades are never imputed and an ungraded pair never counts as
0. A per-child figure that needs an ungraded top-k pair is UNKNOWN, and so is
any mean or test using it. Every ungraded pair is listed (raw file
v3_ungraded_pairs.csv, with empty grade columns for both raters).

With --raw-dir, the tables are also written there as CSV and JSON. The
children are created inside a transaction that is rolled back, so nothing is
stored.
"""

import csv
import json
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings

from recommendations import generation, heldout, ranking
from recommendations.evaluation import (
    LabelError,
    load_heldout_labels,
    ndcg_at_k,
    precision_at_k,
    select_alpha,
)
from recommendations.explanation_check import check as check_explanations
from recommendations.retrieval import retrieve
from recommendations.statistics import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    GRADES,
    KAPPA_WEIGHTS,
    cohen_kappa,
    confusion,
    kappa_bootstrap_ci,
    paired,
)

from .alpha_sensitivity import DEFAULT_EXTRA
from .evaluate_alpha_grid import DEFAULT_LABELS, TOLERANCE
from .evaluate_statistics import fmt_p
from .evaluate_v3_statistics import merge_grades

USERNAME = "v3-full@nurtura.invalid"
K = 5
UNKNOWN = "UNKNOWN"
SBERT = "SBERT only"
HYBRID = "Hybrid retrieval only"
NO_AGE = "No age weight"
RATERS = (("researcher", "relevance"), ("nurse", "rater2"))
METRICS = (
    ("nDCG@5", lambda ids, g: ndcg_at_k(ids, g, 5), 5),
    ("nDCG@3", lambda ids, g: ndcg_at_k(ids, g, 3), 3),
    ("P@5>=1", lambda ids, g: precision_at_k(ids, g, 5, 1), 5),
    ("P@5=2", lambda ids, g: precision_at_k(ids, g, 5, 2), 5),
)


def alpha_name(alpha):
    return f"alpha {alpha:.1f}"


def strict_mean(values):
    """The mean, or None (UNKNOWN) if any value is unknown or there are none."""
    values = list(values)
    if not values or any(v is None for v in values):
        return None
    return sum(values) / len(values)


def fmt(value, digits=3):
    return UNKNOWN if value is None else f"{value:.{digits}f}"


class Command(BaseCommand):
    help = "Full offline evaluation of the current system (v3)."

    def add_arguments(self, parser):
        parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
        parser.add_argument("--extra-labels", type=Path, default=DEFAULT_EXTRA)
        parser.add_argument("--markdown", action="store_true")
        parser.add_argument("--raw-dir", type=Path)

    # ------------------------------------------------------------------ setup

    def handle(self, *args, **options):
        self.markdown = options["markdown"]
        self.raw_dir = options["raw_dir"]
        paths = [options["labels"]]
        if options["extra_labels"] and options["extra_labels"].exists():
            paths.append(options["extra_labels"])
        sheets = []
        for path in paths:
            try:
                sheets.append((path.name, load_heldout_labels(path)))
            except LabelError as exc:
                raise CommandError(
                    f"Can't use {path}:\n  " + "\n  ".join(exc.problems)
                ) from exc
        self.grades = {who: merge_grades(sheets, attr) for who, attr in RATERS}
        self.beta = float(settings.RETRIEVAL_BETA)
        self.alpha = float(settings.RANKING_ALPHA)
        if self.beta == 1.0:
            raise CommandError(
                "RETRIEVAL_BETA is 1, so the hybrid and SBERT-only retrieval are "
                "the same; run it at the app's beta."
            )
        self.full = alpha_name(self.alpha)
        self.no_priority = alpha_name(0.0)
        self.children = list(heldout.HELDOUT_CHILDREN)
        self.split = {
            s: [c.child_id for c in self.children if c.split == s]
            for s in heldout.SPLITS
        }
        self.age = {c.child_id: c.age_months for c in self.children}
        self.settings = [SBERT, HYBRID, *map(alpha_name, heldout.ALPHAS), NO_AGE]
        self._run()

        self._heading("Setting")
        self._line(
            f"v3: retrieval beta {self.beta:g} (settings.RETRIEVAL_BETA), alpha "
            f"{self.alpha:g}. Labels: " + ", ".join(p.name for p in paths) + ". "
            "Plan fixed before the run: docs/eval_v3_full_plan.md (#270)."
        )
        self._line(
            f"Bootstrap: {BOOTSTRAP_RESAMPLES:,} resamples of children, seed "
            f"{BOOTSTRAP_SEED}, percentile 95% interval. Wilcoxon: two-sided "
            "signed-rank test, zero differences dropped. Test children primary."
        )
        self._line(
            "No grade is imputed and no ungraded pair counts as 0: a figure "
            f"that needs an ungraded top-k pair is {UNKNOWN}."
        )
        self._coverage_section()
        self._alpha_section()
        self._test_section()
        self._per_profile_section()
        self._agreement_section()
        self._rater_comparison_section()
        self._beyond_section()
        self._ablation_section()
        self._explanation_section()

    def _run(self):
        """Rankings for every setting, and the stored batches' explanations."""
        self.rankings, self.activity, self.explanations = {}, {}, {}
        with transaction.atomic():
            caregiver = get_user_model().objects.create_user(username=USERNAME)
            for child in self.children:
                profile = heldout.create_child(child, caregiver)
                retrieval = retrieve(profile, limit=None)
                for c in retrieval.candidates:
                    self.activity[c.activity.activity_id] = c.activity
                cands, ev = retrieval.candidates, retrieval.evaluation
                order = {HYBRID: [c.activity.activity_id for c in cands]}
                for a in heldout.ALPHAS:
                    order[alpha_name(a)] = self._ids(
                        ranking.rank_candidates(cands, ev, a)
                    )
                order[NO_AGE] = self._ids(
                    ranking.rank_candidates(cands, ev, self.alpha, use_age=False)
                )
                with override_settings(RETRIEVAL_BETA=1.0):
                    sbert = retrieve(profile, limit=None)
                for c in sbert.candidates:
                    self.activity[c.activity.activity_id] = c.activity
                order[SBERT] = [c.activity.activity_id for c in sbert.candidates]
                self.rankings[child.child_id] = order

                stored = generation.generate(profile.pk, caregiver).recommendations
                profile.refresh_from_db()
                self.explanations[child.child_id] = check_explanations(
                    profile, [r.explanation for r in stored]
                )
            transaction.set_rollback(True)

    @staticmethod
    def _ids(ranked):
        return [r.activity.activity_id for r in ranked]

    # --------------------------------------------------------------- metrics

    def score(self, child, setting, metric="nDCG@5", rater="researcher"):
        """A metric for one child and setting, or None if a needed pair is ungraded."""
        _, fn, k = next(m for m in METRICS if m[0] == metric)
        ids = self.rankings[child][setting]
        grades = self.grades[rater].get(child, {})
        if any(a not in grades for a in ids[:k]):
            return None
        return fn(ids, grades)

    def mean_of(self, children, setting, metric="nDCG@5", rater="researcher"):
        return strict_mean(self.score(c, setting, metric, rater) for c in children)

    def compare(self, children, a, b, rater="researcher"):
        """paired() of setting a against b, or None if any value is unknown."""
        xs = [self.score(c, a, rater=rater) for c in children]
        ys = [self.score(c, b, rater=rater) for c in children]
        if any(v is None for v in xs + ys):
            return None
        return paired(xs, ys)

    def ungraded(self, children, setting, rater):
        return sum(
            1
            for c in children
            for a in self.rankings[c][setting][:K]
            if a not in self.grades[rater].get(c, {})
        )

    # -------------------------------------------------------------- sections

    def _coverage_section(self):
        self._heading("Label coverage (top-5 pairs)")
        rows, raw = [], []
        for setting in self.settings:
            row = [setting]
            for s in heldout.SPLITS:
                slots = K * len(self.split[s])
                for who, _ in RATERS:
                    missing = self.ungraded(self.split[s], setting, who)
                    raw.append(
                        {
                            "setting": setting,
                            "set": s,
                            "rater": who,
                            "top5_pairs": slots,
                            "graded": slots - missing,
                            "ungraded": missing,
                        }
                    )
                row.append(
                    f"{slots - self.ungraded(self.split[s], setting, 'researcher')}"
                    f"/{slots}"
                    f" ({self.ungraded(self.split[s], setting, 'nurse')} ungraded "
                    "by nurse)"
                )
            rows.append(row)
        self._table(["Setting", "Tune graded", "Test graded", "Gap (H17) graded"], rows)
        self._write_csv("v3_label_coverage.csv", raw)

        pairs = {}
        for c in self.rankings:
            for setting in self.settings:
                for a in self.rankings[c][setting][:K]:
                    missing = [
                        who for who, _ in RATERS if a not in self.grades[who].get(c, {})
                    ]
                    if missing:
                        entry = pairs.setdefault(
                            (c, a), {"settings": [], "missing": missing}
                        )
                        entry["settings"].append(setting)
        self.ungraded_pairs = [
            {
                "child": c,
                "split": heldout.HELDOUT_BY_ID[c].split,
                "activity_id": a,
                "activity_name": self.activity[a].activity_name,
                "child_age_months": self.age[c],
                "settings": "; ".join(e["settings"]),
                "missing_for": " and ".join(e["missing"]),
                "relevance": "",
                "relevance_rater2": "",
            }
            for (c, a), e in sorted(pairs.items())
        ]
        both = sum(
            1 for p in self.ungraded_pairs if p["missing_for"] == "researcher and nurse"
        )
        self._line("")
        self._line(
            f"Ungraded pairs across all settings: {len(self.ungraded_pairs)} "
            f"({both} need grading by both raters). Listed in "
            "raw/v3_ungraded_pairs.csv with empty grade columns."
        )
        self._write_csv(
            "v3_ungraded_pairs.csv",
            self.ungraded_pairs,
            fields=[
                "child",
                "split",
                "activity_id",
                "activity_name",
                "child_age_months",
                "settings",
                "missing_for",
                "relevance",
                "relevance_rater2",
            ],
        )

    def _alpha_section(self):
        self._heading("1. Alpha grid (mean nDCG@5, researcher's grades)")
        rows, raw = [], []
        curve = {}
        for setting in self.settings[:-1]:  # every alpha and both baselines
            tune = self.mean_of(self.split["tune"], setting)
            test = self.mean_of(self.split["test"], setting)
            if setting.startswith("alpha"):
                curve[float(setting.split()[1])] = tune
            rows.append(
                [
                    setting,
                    fmt(tune),
                    fmt(test),
                    str(self.ungraded(self.split["tune"], setting, "researcher")),
                    str(self.ungraded(self.split["test"], setting, "researcher")),
                ]
            )
            raw.append(
                {
                    "setting": setting,
                    "alpha": setting.split()[1] if setting.startswith("alpha") else "",
                    "tune_ndcg5": "" if tune is None else tune,
                    "test_ndcg5": "" if test is None else test,
                    "tune_ungraded": rows[-1][3],
                    "test_ungraded": rows[-1][4],
                }
            )
        self._table(
            ["Setting", "Tune", "Test", "Ungraded (tune)", "Ungraded (test)"], rows
        )
        self._write_csv("v3_alpha_grid.csv", raw)
        chosen, qualifying = select_alpha(curve, TOLERANCE)
        left_out = [a for a, v in curve.items() if v is None]
        self.rule = {
            "chosen": chosen,
            "qualifying": qualifying,
            "best": max((v for v in curve.values() if v is not None), default=None),
            "left_out": left_out,
        }
        self._line("")
        if chosen is None:
            self._line(f"The rule can't be applied: every tune mean is {UNKNOWN}.")
            return
        self._line(
            f"Rule (best tune mean, middle of the range within {TOLERANCE}): best "
            f"{self.rule['best']:.3f}; within {TOLERANCE}: "
            + ", ".join(f"{a:.1f}" for a in qualifying)
            + f"; chosen alpha {chosen:.1f}."
            + (
                " Left out (tune mean UNKNOWN): "
                + ", ".join(f"{a:.1f}" for a in left_out)
                + "."
                if left_out
                else ""
            )
        )

    def _test_section(self):
        self._heading(f"2. Test set at alpha {self.alpha:g} against both baselines")
        rows, raw = [], []
        for setting in (self.full, HYBRID, SBERT):
            vals = {
                name: self.mean_of(self.split["test"], setting, name)
                for name, _, _ in METRICS
            }
            rows.append([setting, *(fmt(vals[n]) for n, _, _ in METRICS)])
            raw.append(
                {
                    "setting": setting,
                    **{n: "" if v is None else v for n, v in vals.items()},
                }
            )
        self._table(["Setting", *(n for n, _, _ in METRICS)], rows)
        self._write_csv("v3_test_results.csv", raw)
        self._line("")
        self._line(
            "P@5>=1 counts grade 1 or 2 in the top 5; P@5=2 counts grade 2 only."
        )

    def _per_profile_section(self):
        self._heading("3. Per-profile nDCG@5 (8 test children and H17)")
        kids = self.split["test"] + self.split["gap"]
        rows, raw = [], []
        for c in kids:
            for who, _ in RATERS:
                vals = {
                    s: self.score(c, s, rater=who) for s in (self.full, HYBRID, SBERT)
                }
                rows.append(
                    [
                        c,
                        heldout.HELDOUT_BY_ID[c].split,
                        who,
                        fmt(vals[self.full]),
                        fmt(vals[HYBRID]),
                        fmt(vals[SBERT]),
                    ]
                )
                raw.append(
                    {
                        "child": c,
                        "split": heldout.HELDOUT_BY_ID[c].split,
                        "rater": who,
                        "full": "" if vals[self.full] is None else vals[self.full],
                        "hybrid_only": "" if vals[HYBRID] is None else vals[HYBRID],
                        "sbert_only": "" if vals[SBERT] is None else vals[SBERT],
                    }
                )
        self._table(["Child", "Split", "Rater", self.full, HYBRID, SBERT], rows)
        self._write_csv("v3_per_profile_by_rater.csv", raw)
        self._line("")
        for who, _ in RATERS:
            for base in (SBERT, HYBRID):
                r = self.compare(self.split["test"], self.full, base, who)
                self._line(
                    f"Test, {who}'s grades, {self.full} against {base}: "
                    + (
                        f"{r.improved}/{r.tied}/{r.worse} better/tied/worse."
                        if r
                        else f"{UNKNOWN} (ungraded pairs)."
                    )
                )

    def _agreement_section(self):
        self._heading("4. Agreement between raters (every row graded by both)")
        first, second = self.grades["researcher"], self.grades["nurse"]
        by_child = {
            c: [(g, second[c][a]) for a, g in grades.items() if a in second.get(c, {})]
            for c, grades in first.items()
        }
        pairs = [p for ps in by_child.values() for p in ps]
        if not pairs:
            self._line("No rows are graded by both raters.")
            return
        kappas = {}
        for w in KAPPA_WEIGHTS:
            value = cohen_kappa(pairs, w)
            low, high = (
                kappa_bootstrap_ci(by_child, w) if value is not None else (None, None)
            )
            kappas[w] = {"kappa": value, "ci_low": low, "ci_high": high}
        exact = sum(a == b for a, b in pairs) / len(pairs)
        matrix = confusion(pairs)
        self._line(
            f"{len(pairs)} rows ({sum(1 for p in by_child.values() if p)} children)."
        )
        self._line("")
        self._table(
            ["Measure", "Value", "95% CI"],
            [
                [
                    f"Cohen's kappa, {w}",
                    fmt(k["kappa"]),
                    (
                        "-"
                        if k["ci_low"] is None
                        else f"[{k['ci_low']:.3f}, {k['ci_high']:.3f}]"
                    ),
                ]
                for w, k in kappas.items()
            ]
            + [["Exact agreement", f"{exact:.3f}", "-"]],
        )
        self._line("")
        self._line("Rows: researcher; columns: nurse.")
        self._line("")
        self._table(
            ["", *(f"Nurse {g}" for g in GRADES), "Total"],
            [
                [f"Researcher {g}", *(str(n) for n in row), str(sum(row))]
                for g, row in zip(GRADES, matrix)
            ],
        )
        self._write_json(
            "v3_rater_agreement.json",
            {
                "rows_both": len(pairs),
                "children": sum(1 for p in by_child.values() if p),
                "exact": exact,
                "kappa": kappas,
            },
        )
        self._write_csv(
            "v3_confusion.csv",
            [
                {"researcher": g, **{f"nurse_{h}": n for h, n in zip(GRADES, row)}}
                for g, row in zip(GRADES, matrix)
            ],
        )

    def _rater_comparison_section(self):
        self._heading(f"5. Test: {self.full} against {SBERT}, on each rater's grades")
        rows = []
        for who, _ in RATERS:
            r = self.compare(self.split["test"], self.full, SBERT, who)
            rows.append([who, *self._paired_cells(r)] if r else [who, *([UNKNOWN] * 7)])
        self._table(
            [
                "Rater",
                "n",
                self.full,
                SBERT,
                "Difference [95% CI]",
                "Better/tied/worse",
                "W",
                "p",
            ],
            rows,
        )

    def _beyond_section(self):
        self._heading("6. Beyond accuracy (all 20 profiles, researcher's grades)")
        everyone = [c.child_id for c in self.children]
        rows, raw = [], []
        for setting in (self.full, SBERT):
            grade0 = other_band = ungraded = test0 = 0
            areas, freq = [], Counter()
            for c in everyone:
                top = self.rankings[c][setting][:K]
                freq.update(top)
                areas.append(len({self.activity[a].developmental_domain for a in top}))
                for a in top:
                    g = self.grades["researcher"].get(c, {}).get(a)
                    if g is None:
                        ungraded += 1
                    elif g == 0:
                        grade0 += 1
                        test0 += c in self.split["test"]
                        bracket = ranking.child_bracket(self.age[c])
                        act = ranking.BRACKET_INDEX.get(self.activity[a].age_range)
                        other_band += bracket is not None and act != bracket
            top_id, top_n = freq.most_common(1)[0]
            row = {
                "setting": setting,
                "grade0_slots_of_100": grade0,
                "grade0_from_another_age_band": other_band,
                "ungraded_slots_of_100": ungraded,
                "grade0_slots_test": test0,
                "mean_areas_per_top5": sum(areas) / len(areas),
                "distinct_activities": len(freq),
                "most_frequent_activity": f"{top_id} {self.activity[top_id].activity_name}",
                "most_frequent_count": top_n,
            }
            raw.append(row)
            rows.append(
                [
                    setting,
                    str(grade0) + ("" if not ungraded else f" (+{ungraded} ungraded)"),
                    str(other_band),
                    str(test0),
                    f"{row['mean_areas_per_top5']:.2f}",
                    str(len(freq)),
                    f"{top_n} ({row['most_frequent_activity']})",
                ]
            )
        self._table(
            [
                "Setting",
                "Grade-0 slots (of 100)",
                "From another age band",
                "Grade-0 slots, test",
                "Areas per top 5",
                "Distinct activities",
                "Most frequent",
            ],
            rows,
        )
        self._write_csv("v3_beyond_accuracy.csv", raw)

        matrix = []
        for scope, kids in (("all 20", everyone), ("test", self.split["test"])):
            for setting in (self.full, SBERT):
                for rank in range(1, K + 1):
                    g = Counter(
                        self.grades["researcher"]
                        .get(c, {})
                        .get(self.rankings[c][setting][rank - 1], "ungraded")
                        for c in kids
                        if len(self.rankings[c][setting]) >= rank
                    )
                    matrix.append(
                        {
                            "children": scope,
                            "setting": setting,
                            "rank": rank,
                            "grade_0": g.get(0, 0),
                            "grade_1": g.get(1, 0),
                            "grade_2": g.get(2, 0),
                            "ungraded": g.get("ungraded", 0),
                        }
                    )
        self._line("")
        self._line("Grade by rank position, all 20 profiles:")
        self._line("")
        self._table(
            ["Setting", "Rank", "Grade 0", "Grade 1", "Grade 2", "Ungraded"],
            [
                [
                    m["setting"],
                    str(m["rank"]),
                    str(m["grade_0"]),
                    str(m["grade_1"]),
                    str(m["grade_2"]),
                    str(m["ungraded"]),
                ]
                for m in matrix
                if m["children"] == "all 20"
            ],
        )
        self._write_csv("v3_rank_grade_matrix.csv", matrix)

    def _ablation_section(self):
        self._heading("7. Ablation on the test set (nDCG@5, researcher's grades)")
        settings_ = (
            ("Full system", self.full),
            ("No age weight", NO_AGE),
            ("No rule priority (age weight + similarity)", self.no_priority),
            ("Similarity only (hybrid retrieval)", HYBRID),
        )
        rows, raw = [], []
        for label, setting in settings_:
            value = self.mean_of(self.split["test"], setting)
            missing = self.ungraded(self.split["test"], setting, "researcher")
            r = (
                None
                if setting == self.full
                else self.compare(self.split["test"], self.full, setting)
            )
            cells = (
                ["-"] * 4
                if setting == self.full
                else (
                    [
                        f"{r.mean_diff:+.3f} [{r.ci_low:+.3f}, {r.ci_high:+.3f}]",
                        f"{r.improved}/{r.tied}/{r.worse}",
                        "n/a" if r.wilcoxon_w is None else f"{r.wilcoxon_w:g}",
                        fmt_p(r.p_value),
                    ]
                    if r
                    else [UNKNOWN] * 4
                )
            )
            rows.append([label, fmt(value), str(missing), *cells])
            raw.append(
                {
                    "setting": label,
                    "test_ndcg5": "" if value is None else value,
                    "test_ungraded": missing,
                    "full_minus_this": "" if not r else r.mean_diff,
                    "ci_low": "" if not r else r.ci_low,
                    "ci_high": "" if not r else r.ci_high,
                    "better_tied_worse": (
                        "" if not r else f"{r.improved}/{r.tied}/{r.worse}"
                    ),
                    "wilcoxon_w": "" if not r or r.wilcoxon_w is None else r.wilcoxon_w,
                    "p": "" if not r or r.p_value is None else r.p_value,
                }
            )
        self._table(
            [
                "Setting",
                "Test nDCG@5",
                "Ungraded (test)",
                "Full minus this [95% CI]",
                "Full better/tied/worse",
                "W",
                "p",
            ],
            rows,
        )
        self._write_csv("v3_ablation.csv", raw)

    def _explanation_section(self):
        self._heading("8. Explanation check (stored batches, 20 profiles)")
        totals = Counter()
        max_sentences, examples = 0, []
        for c, r in self.explanations.items():
            for key in ("explanations", "named", "not_in_profile", "showing_a_score"):
                totals[key] += r[key]
            max_sentences = max(max_sentences, r["max_sentences"])
            examples += [f"{c}: {m}" for m in r["examples_not_in_profile"]]
        summary = {
            "profiles": len(self.explanations),
            "explanations": totals["explanations"],
            "max_sentences_per_explanation": max_sentences,
            "items_named": totals["named"],
            "items_not_in_stored_profile": totals["not_in_profile"],
            "explanations_showing_a_score": totals["showing_a_score"],
            "examples_not_in_profile": examples,
        }
        self._table(
            ["Measure", "Value"],
            [
                ["Profiles", str(summary["profiles"])],
                ["Explanations", str(summary["explanations"])],
                ["Most sentences in one explanation", str(max_sentences)],
                ["Milestones, concerns and interests named", str(totals["named"])],
                ["Named but not in the stored profile", str(totals["not_in_profile"])],
                ["Explanations showing a score", str(totals["showing_a_score"])],
            ],
        )
        self._write_json("v3_explanation_check.json", summary)

    # ---------------------------------------------------------------- output

    def _paired_cells(self, r):
        return [
            str(r.n),
            f"{r.mean_a:.3f}",
            f"{r.mean_b:.3f}",
            f"{r.mean_diff:+.3f} [{r.ci_low:+.3f}, {r.ci_high:+.3f}]",
            f"{r.improved}/{r.tied}/{r.worse}",
            "n/a" if r.wilcoxon_w is None else f"{r.wilcoxon_w:g}",
            fmt_p(r.p_value),
        ]

    def _write_csv(self, name, rows, fields=None):
        if not self.raw_dir:
            return
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        fields = fields or (list(rows[0]) if rows else [])
        with open(self.raw_dir / name, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def _write_json(self, name, data):
        if not self.raw_dir:
            return
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        with open(self.raw_dir / name, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def _line(self, text):
        self.stdout.write(text)

    def _heading(self, text):
        self._line(f"\n## {text}\n" if self.markdown else f"\n== {text}")

    def _table(self, header, rows):
        self._line("| " + " | ".join(header) + " |")
        self._line("|" + "---|" * len(header))
        for row in rows:
            self._line("| " + " | ".join(row) + " |")
