"""1c catalogue, 1d storage and engine, 1e alpha = 1.0 pool, 2a dataset, 2b configuration.

Read-only: SELECTs, plus one fictional held-out child whose recommendation
row is generated inside a transaction that is rolled back.
"""

import csv
import re
from collections import Counter, defaultdict

from _common import (
    ROOT,
    django_setup,
    grep,
    line_of,
    redact,
    rolled_back,
    run,
    table,
    write_csv,
    write_json,
    write_md,
)

COMMAND = "backend\\venv\\Scripts\\python.exe scripts\\report_evidence\\catalogue_and_config.py"

CONFIG_FILES = [
    "backend/profiles/rules/engine.py",
    "backend/profiles/rules/guidelines.py",
    "backend/profiles/rules/referral.py",
    "backend/recommendations/retrieval.py",
    "backend/recommendations/ranking.py",
    "backend/recommendations/generation.py",
    "backend/recommendations/explanations.py",
    "backend/recommendations/embeddings.py",
    "backend/recommendations/personalisation.py",
    "backend/recommendations/options.py",
    "backend/recommendations/browse.py",
    "backend/recommendations/warmup.py",
]
CONSTANT = re.compile(r"^([A-Z][A-Z0-9_]+) = (.+)$")


def constants():
    rows = []
    for path in CONFIG_FILES:
        for i, line in enumerate(
            (ROOT / path).read_text(encoding="utf-8").splitlines(), 1
        ):
            m = CONSTANT.match(line)
            if m and not m.group(2).rstrip().endswith(("(", "{", "[")):
                rows.append(
                    {
                        "setting": m.group(1),
                        "value": m.group(2).split("  #")[0].strip(),
                        "where": f"{path}:{i}",
                    }
                )
    return rows


def main():
    django_setup()
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.db import connection
    from django.forms.models import model_to_dict

    from activities.models import DevelopmentalActivity
    from profiles.models import ReferenceMilestone
    from recommendations import generation, heldout
    from recommendations.models import Recommendation

    # ---- 1c / 2a inventories ----
    batches = {}
    with open(
        ROOT / "data" / "raw" / "activities.csv", newline="", encoding="utf-8"
    ) as f:
        for row in csv.DictReader(f):
            batches[row["activity_id"]] = row.get("batch", "")
    activities = [
        {
            "activity_id": a.activity_id,
            "name": a.activity_name,
            "domain": a.developmental_domain,
            "age_range": a.age_range,
            "status": a.content_status,
            "source": a.source,
            "has_source_url": bool(a.source_url),
            "difficulty": a.difficulty_level,
            "batch": batches.get(a.activity_id, "UNKNOWN"),
        }
        for a in DevelopmentalActivity.objects.order_by("activity_id")
    ]
    write_csv("activities_inventory.csv", activities)
    milestones = [
        {
            "milestone_key": m.milestone_key,
            "source": m.source,
            "domain": m.domain,
            "expected_age_months": float(m.expected_age_months),
            "verified": m.verified,
            "description": m.description,
        }
        for m in ReferenceMilestone.objects.order_by("milestone_key")
    ]
    write_csv("milestones_inventory.csv", milestones)

    published = [a for a in activities if a["status"] == "published"]
    ages = [c for c, _ in DevelopmentalActivity._meta.get_field("age_range").choices]
    domains = [
        c
        for c, _ in DevelopmentalActivity._meta.get_field(
            "developmental_domain"
        ).choices
    ]
    grid = Counter((a["domain"], a["age_range"]) for a in published)
    heat = [
        {"domain": d, **{age: grid.get((d, age), 0) for age in ages}} for d in domains
    ]
    write_csv("published_by_domain_age.csv", heat, ["domain", *ages])

    held_keys = heldout.milestone_keys()
    verified = {m["milestone_key"]: m["verified"] for m in milestones}
    held = [[k, verified.get(k, "not in catalogue")] for k in held_keys]
    load_line = line_of(
        "backend/profiles/management/commands/seed_milestones.py", r"^DEFAULT_FILE"
    )
    from profiles.management.commands import seed_milestones

    default_file = seed_milestones.DEFAULT_FILE.resolve().relative_to(ROOT).as_posix()

    # ---- 1d storage and engine ----
    with connection.cursor() as c:
        c.execute(
            "SELECT table_name, column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'recommendations_activityembedding' ORDER BY ordinal_position"
        )
        embedding_cols = c.fetchall()
    searches = {}
    for term in ("faiss", "pgvector", "experta"):
        hits = grep(
            term,
            [
                "backend",
                "mobile/nurtura_app/lib",
                "docs",
                "README.md",
                "backend/requirements.txt",
            ],
            re.I,
        )
        hits = [h for h in hits if not h[0].startswith("backend/models/")]
        searches[term] = hits
    code_use = {
        t: [h for h in hits if h[0].endswith(".py") and ("import" in h[2])]
        for t, hits in searches.items()
    }
    import json as _json

    prs = _json.loads(
        run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "all",
                "--search",
                "experta",
                "--json",
                "number,title",
            ]
        )
        or "[]"
    )
    pr_quotes = []
    for pr in prs:
        body = run(
            ["gh", "pr", "view", str(pr["number"]), "--json", "body", "-q", ".body"]
        )
        for text_line in body.splitlines():
            if "experta" in text_line.lower():
                pr_quotes.append(
                    f'PR #{pr["number"]} ({pr["title"]}): "{text_line.strip()}"'
                )

    # ---- 2a samples ----
    sample_activity = model_to_dict(
        DevelopmentalActivity.objects.filter(content_status="published")
        .order_by("activity_id")
        .first()
    )
    sample_milestone = model_to_dict(
        ReferenceMilestone.objects.order_by("milestone_key").first()
    )
    child_def = heldout.HELDOUT_CHILDREN[0]
    sample_child = {
        "child_id": child_def.child_id,
        "fictional": True,
        "age_months": child_def.age_months,
        "not_yet": list(child_def.not_yet),
        "achieved": list(child_def.achieved),
        "concerns": list(child_def.concerns),
        "interests": list(child_def.interests),
        "defined_in": f"backend/recommendations/heldout.py:{line_of('backend/recommendations/heldout.py', re.escape(child_def.child_id))}",
    }
    sample_rec = None
    with rolled_back():
        caregiver = get_user_model().objects.create_user(
            username="evidence@nurtura.invalid"
        )
        child = heldout.create_child(child_def, caregiver)
        result = generation.generate(child.pk, caregiver)
        first = result.recommendations[0]
        sample_rec = model_to_dict(Recommendation.objects.get(pk=first.pk))
        sample_rec["activity_id"] = first.activity.activity_id
    write_json(
        "dataset_samples.json",
        redact(
            {
                "activity": sample_activity,
                "milestone": sample_milestone,
                "fictional_child": sample_child,
                "recommendation_row (rolled back)": sample_rec,
            }
        ),
    )

    # ---- 2b configuration ----
    config = constants()
    config += [
        {
            "setting": "RANKING_ALPHA",
            "value": settings.RANKING_ALPHA,
            "where": f"backend/nurtura_backend/settings.py:{line_of('backend/nurtura_backend/settings.py', '^RANKING_ALPHA')} (env RANKING_ALPHA)",
        },
        {
            "setting": "SBERT_MODEL_PATH",
            "value": str(settings.SBERT_MODEL_PATH.name),
            "where": f"backend/nurtura_backend/settings.py:{line_of('backend/nurtura_backend/settings.py', '^SBERT_MODEL_PATH')}",
        },
        {
            "setting": "DEFAULT_THROTTLE_RATES",
            "value": settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES"),
            "where": f"backend/nurtura_backend/settings.py:{line_of('backend/nurtura_backend/settings.py', 'DEFAULT_THROTTLE_RATES')}",
        },
        {
            "setting": "TOKEN_LIFETIME",
            "value": str(settings.TOKEN_LIFETIME),
            "where": f"backend/nurtura_backend/settings.py:{line_of('backend/nurtura_backend/settings.py', '^TOKEN_LIFETIME')}",
        },
        {
            "setting": "ranking_version()",
            "value": generation.ranking_version(),
            "where": f"backend/recommendations/generation.py:{line_of('backend/recommendations/generation.py', 'def ranking_version')}",
        },
        {
            "setting": "RuleEngine baseline",
            "value": 1.0,
            "where": f"backend/profiles/rules/engine.py:{line_of('backend/profiles/rules/engine.py', 'def __init__.*baseline')}",
        },
        {
            "setting": "Priority normalisation",
            "value": "max(0, raw) / top raw score (top area = 1.0)",
            "where": f"backend/profiles/rules/engine.py:{line_of('backend/profiles/rules/engine.py', 'top = max')}",
        },
        {
            "setting": "Similarity normalisation",
            "value": "min-max over the child's pool",
            "where": f"backend/recommendations/ranking.py:{line_of('backend/recommendations/ranking.py', 'sim_norm = ')}",
        },
        {
            "setting": "Query template",
            "value": "'Activities for <age phrase> to support <focus areas>. Still working on: ... Enjoys ...'",
            "where": f"backend/recommendations/retrieval.py:{line_of('backend/recommendations/retrieval.py', 'def profile_query')}",
        },
    ]
    from recommendations import embeddings

    model_dir = settings.SBERT_MODEL_PATH
    size_mb = (
        round(
            sum(p.stat().st_size for p in model_dir.rglob("*") if p.is_file()) / 1e6, 1
        )
        if model_dir.exists()
        else "UNKNOWN"
    )
    config.append(
        {
            "setting": "Embedding model size on disk",
            "value": f"{size_mb} MB; {embeddings.get_encoder().dimensions} dimensions",
            "where": (
                str(model_dir.relative_to(ROOT)) if model_dir.exists() else "UNKNOWN"
            ),
        }
    )
    write_csv("configuration.csv", config)

    # ---- 1e ----
    rank_line = line_of(
        "backend/recommendations/ranking.py", r"retrieval = retrieve\(child, limit=None"
    )
    doc_line = line_of(
        "backend/recommendations/retrieval.py", r"limit=None returns every eligible"
    )
    tie_line = line_of("backend/recommendations/ranking.py", r"if alpha == 1.0")
    gen_line = line_of(
        "backend/recommendations/generation.py", r"result = rank\(child\)"
    )

    # ---- Write ----
    status_counts = Counter(a["status"] for a in activities)
    body = f"""## 1c. Milestone catalogue

- **Load command:** `python manage.py seed_milestones` (from `backend/`); default file `{default_file}` (`backend/profiles/management/commands/seed_milestones.py:{load_line}`). It validates every row before writing and matches on `milestone_key`.
- **Verified:** {sum(m['verified'] for m in milestones)} of {len(milestones)} catalogue milestones (`ReferenceMilestone.verified`; `raw/milestones_inventory.csv`).
- **Used by the held-out children:** {len(held_keys)} milestones (`heldout.milestone_keys()`), {sum(1 for _, v in held if v is True)} of them verified:

{table(['Milestone key', 'Verified'], held)}

## Published activities by area and age band

{len(published)} Published activities ({dict(status_counts)} by status). `raw/published_by_domain_age.csv`; heatmap in `figures/published_heatmap.png`.

{table(['Area', *ages, 'Total'], [[h['domain'], *[h[a] for a in ages], sum(h[a] for a in ages)] for h in heat])}

By source: {dict(Counter(a['source'] for a in published))}. With a source URL: {sum(a['has_source_url'] for a in published)} of {len(published)}. By batch (from `data/raw/activities.csv`): {dict(Counter(a['batch'] for a in published))}.

## 1d. Storage and engine

- **Embeddings:** {', '.join(f'`{t}.{c}` {d}' for t, c, d in embedding_cols)} (`information_schema.columns`). Vectors are float32 bytes in a `BinaryField` (`backend/recommendations/models.py:{line_of('backend/recommendations/models.py', 'vector = models.BinaryField')}`), compared with a NumPy dot product (`backend/recommendations/retrieval.py:{line_of('backend/recommendations/retrieval.py', 'matrix @ query_vector')}`).
- **FAISS / pgvector / experta imported by code:** {', '.join(f"{t}: {'yes' if code_use[t] else 'no'}" for t in code_use)}. Mentions in the repository (docs and comments): {', '.join(f"{t}: {len(h)}" for t, h in searches.items())}; listed in `raw/engine_mentions.json`.
- **Reason for the custom rule engine** (pull request text containing "experta", via `gh pr view`):
{chr(10).join('  - ' + q for q in pr_quotes) or '  - UNKNOWN: no pull request text found.'}

## 1e. Does α = 1.0 rank every eligible Published activity?

Yes. `rank()` calls `retrieve(child, limit=None, ...)` (`backend/recommendations/ranking.py:{rank_line}`), and `limit=None` returns every eligible activity in similarity order (`backend/recommendations/retrieval.py:{doc_line}`). Eligible means Published, embedded with the current model, and prenatal-only for pregnancies or postnatal-only otherwise (same function). The app's `generate()` uses `rank(child)` (`backend/recommendations/generation.py:{gen_line}`). At α = 1.0, ties in priority × age weight are broken by age weight, then activity ID (`backend/recommendations/ranking.py:{tie_line}`).

## 2a. Samples and preparation

Samples (`raw/dataset_samples.json`): one Published activity, one catalogue milestone, one fictional held-out child ({sample_child['child_id']}) and the recommendation row generated for it inside a rolled-back transaction.

Preparation and validation steps:

{table(['Step', 'Command / file'], [
    ['Activities loaded from CSV as Draft, all-or-nothing validation', 'backend/activities/management/commands/seed_activities.py'],
    ['Plain-language aims loaded', 'backend/activities/management/commands/load_plain_aims.py'],
    ['Review: Draft → Under Review → Published (only Published are recommended)', 'backend/activities/models.py'],
    ['Embeddings precomputed; re-encoded only when the text hash changes', 'backend/recommendations/management/commands/embed_activities.py'],
    ['Milestone catalogue loaded and validated', 'backend/profiles/management/commands/seed_milestones.py'],
    ['Data files and their provenance', 'data/README.md'],
])}

## 2b. Configuration ("hyperparameters")

Every module constant in the recommendation path, plus the settings that affect results. Values are read from the code at run time. `raw/configuration.csv`.

{table(['Setting', 'Value', 'Where'], [[c['setting'], str(c['value']).replace('|', '/'), c['where']] for c in config])}
"""
    write_json(
        "engine_mentions.json",
        {t: [f"{f}:{n}: {txt[:160]}" for f, n, txt in h] for t, h in searches.items()},
    )
    write_md(
        "03_catalogue_dataset_config.md",
        body,
        "Catalogue, dataset and configuration",
        COMMAND,
    )
    print(
        len(published),
        "published;",
        sum(m["verified"] for m in milestones),
        "verified of",
        len(milestones),
    )


if __name__ == "__main__":
    main()
