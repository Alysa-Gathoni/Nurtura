"""2c explanation figure data for three fictional children.

Each child is created inside a transaction that is rolled back. For each:
the rules that fired and their adjustments (raw boosts), the normalised
area priorities, the top five at settings.RANKING_ALPHA with similarity,
rule priority, age weight and final score, and the explanation text the app
shows.
"""

from _common import django_setup, rolled_back, table, write_csv, write_json, write_md

COMMAND = "backend\\venv\\Scripts\\python.exe scripts\\report_evidence\\explanation_examples.py"


def main():
    django_setup()
    from django.conf import settings
    from django.contrib.auth import get_user_model

    from profiles.rules import build_profile
    from recommendations.explanations import explain
    from recommendations.heldout import HeldOutChild, create_child
    from recommendations.ranking import rank_candidates
    from recommendations.retrieval import profile_query, retrieve

    alpha = float(settings.RANKING_ALPHA)
    profiles = [
        HeldOutChild(
            "E1",
            "example",
            "Language",
            -3.0,
            "Fictional: expecting in about 3 months; caregiver wants support with language.",
            concerns=("Language",),
        ),
        HeldOutChild(
            "E2",
            "example",
            "Language",
            13.0,
            'Fictional: 13 months; "Waves bye-bye" (CDC, by 12 months) recorded as Not yet.',
            not_yet=("CDC-12M-LA-01",),
        ),
        HeldOutChild(
            "E3",
            "example",
            "Sensory",
            8.0,
            "Fictional: 8 months; enjoys water, sand and different textures; no concerns.",
            interests=("water", "sand", "textures"),
        ),
    ]

    rules_rows, top_rows, data = [], [], []
    with rolled_back():
        caregiver = get_user_model().objects.create_user(
            username="explanation-evidence@nurtura.invalid"
        )
        for p in profiles:
            child = create_child(p, caregiver)
            evaluation = build_profile(child)
            retrieval = retrieve(child, limit=None)
            ranked = rank_candidates(retrieval.candidates, retrieval.evaluation, alpha)[
                :5
            ]
            for f in evaluation.firings:
                rules_rows.append(
                    {
                        "profile": p.child_id,
                        "rule": f.rule.name,
                        "adjustments": "; ".join(
                            f"{d} +{v:g}" for d, v in f.adjustments.items()
                        ),
                        "reason": f.reason,
                    }
                )
            for i, r in enumerate(ranked, 1):
                top_rows.append(
                    {
                        "profile": p.child_id,
                        "rank": i,
                        "activity_id": r.activity.activity_id,
                        "activity": r.activity.activity_name,
                        "area": r.activity.developmental_domain,
                        "age_range": r.activity.age_range,
                        "similarity": round(r.similarity, 4),
                        "similarity_norm": round(r.similarity_norm, 4),
                        "rule_priority": round(r.priority, 4),
                        "age_weight": r.age_weight,
                        "score": round(r.score, 4),
                        "explanation": explain(child, evaluation, r).text,
                    }
                )
            data.append(
                {
                    "profile": p.child_id,
                    "description": p.profile,
                    "query": profile_query(evaluation, child),
                    "raw_scores": {
                        k: round(v, 3) for k, v in evaluation.raw_scores.items()
                    },
                    "priorities": {
                        k: round(v, 3) for k, v in evaluation.scores.items()
                    },
                    "eligible_activities": len(retrieval.candidates),
                }
            )
    write_csv("explanation_rules_fired.csv", rules_rows)
    write_csv("explanation_top5.csv", top_rows)
    write_json("explanation_profiles.json", data)

    parts = []
    for d in data:
        pid = d["profile"]
        fired = [r for r in rules_rows if r["profile"] == pid]
        top = [r for r in top_rows if r["profile"] == pid]
        parts.append(f"""## {pid}: {d['description']}

- **Query sent to SBERT:** "{d['query']}"
- **Raw area scores** (baseline 1 + rule adjustments): {d['raw_scores']}
- **Priorities** (normalised, top area = 1): {d['priorities']}
- **Eligible activities scored:** {d['eligible_activities']}

Rules that fired:

{table(['Rule', 'Adjustments', 'Reason'], [[r['rule'], r['adjustments'], r['reason']] for r in fired]) if fired else 'None: every area stays at the baseline.'}

Top five at α = {alpha}:

{table(['#', 'Activity', 'Area', 'Age', 'Similarity', 'Norm. sim.', 'Priority', 'Age weight', 'Score'], [[r['rank'], f"{r['activity']} ({r['activity_id']})", r['area'], r['age_range'], r['similarity'], r['similarity_norm'], r['rule_priority'], r['age_weight'], r['score']] for r in top])}

Explanations shown to the caregiver:

{chr(10).join(f"{r['rank']}. {r['explanation']}" for r in top)}
""")
    body = (
        f"Three fictional children (not in the evaluation), created in a rolled-back transaction. Score = age weight × ((1 − α) × normalised similarity + α × priority), α = {alpha}. Raw: `raw/explanation_rules_fired.csv`, `raw/explanation_top5.csv`, `raw/explanation_profiles.json`.\n\n"
        + "\n".join(parts)
    )
    write_md("06_explanation_examples.md", body, "Explanation examples", COMMAND)
    print("ok")


if __name__ == "__main__":
    main()
