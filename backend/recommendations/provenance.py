"""Record what the held-out pools were built from, and detect drift (#44).

export_heldout_labels writes a sidecar JSON next to the labelling sheet with
a snapshot of everything that shapes the pools:

- activities: every Published activity ID with a hash of its content;
- rule_weights: the rule engine's weights, thresholds and rule names;
- ranking: the age weights and the retrieval query settings;
- catalogue: a version hash of the reference milestones (key, source,
  expected age, domain, description). The `verified` flag is left out because
  the rules don't read it, so verifying milestones doesn't count as a change;
  correcting an age or a description does;
- embedding: the model name and dimensions, a hash of the stored activity
  vectors, and a hash of the model files used to encode the query;
- sheet_rows: a hash of the sheet's (child_id, activity_id) rows.

evaluate_alpha_grid takes the same snapshot and warns about any difference.
The `info` section (generation time, git commit, verified count) is recorded
for the record only and never compared.
"""

import hashlib
import json
import subprocess
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from activities.models import DevelopmentalActivity
from profiles.models import ReferenceMilestone
from profiles.rules import GUIDELINE_RULES, RuleEngine, guidelines

from . import embeddings, ranking, retrieval
from .models import ActivityEmbedding

FORMAT = 1
ACTIVITY_FIELDS = (
    "activity_name",
    "developmental_domain",
    "age_range",
    "developmental_goal",
    "materials",
    "difficulty_level",
    "description",
    "cultural_relevance",
    "source",
    "source_url",
    "content_status",
)
CATALOGUE_FIELDS = (
    "milestone_key",
    "source",
    "expected_age_months",
    "domain",
    "description",
)
COMPARED = ("activities", "rule_weights", "ranking", "catalogue", "embedding")


def sidecar_path(sheet_path):
    """heldout_labels.csv -> heldout_labels.provenance.json, alongside it."""
    sheet_path = Path(sheet_path)
    return sheet_path.with_name(f"{sheet_path.stem}.provenance.json")


def _sha256(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def activity_hash(activity):
    return _sha256({f: getattr(activity, f) for f in ACTIVITY_FIELDS})


def rule_weights():
    return {
        "baseline": RuleEngine(GUIDELINE_RULES).baseline,
        "rules": [rule.name for rule in GUIDELINE_RULES],
        "not_yet_deficit": guidelines.NOT_YET_DEFICIT,
        "emerging_deficit": guidelines.EMERGING_DEFICIT,
        "upcoming_window_months": guidelines.UPCOMING_WINDOW_MONTHS,
        "upcoming_weight": guidelines.UPCOMING_WEIGHT,
        "concern_weight": guidelines.CONCERN_WEIGHT,
        "sensory_interest_weight": guidelines.SENSORY_INTEREST_WEIGHT,
        "sensory_interest_keywords": list(guidelines.SENSORY_INTEREST_KEYWORDS),
        "not_a_delay_signal": sorted(guidelines.NOT_A_DELAY_SIGNAL),
    }


def ranking_settings():
    return {
        "age_weights": {
            "same_bracket": ranking.SAME_BRACKET,
            "one_younger": ranking.ONE_YOUNGER,
            "one_older": ranking.ONE_OLDER,
            "two_away": ranking.TWO_AWAY,
            "further": ranking.FURTHER,
        },
        "focus_threshold": retrieval.FOCUS_THRESHOLD,
        "domain_descriptions_sha256": _sha256(retrieval.DOMAIN_DESCRIPTIONS),
    }


def catalogue_version():
    rows = [
        [str(v) for v in row]
        for row in ReferenceMilestone.objects.order_by("milestone_key").values_list(
            *CATALOGUE_FIELDS
        )
    ]
    return {"milestones": len(rows), "sha256": _sha256(rows)}


def model_files_sha256(path):
    """Hash of every file in the model directory (names and contents)."""
    path = Path(path)
    if not path.exists():
        return None
    digest = hashlib.sha256()
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(file.relative_to(path).as_posix().encode("utf-8"))
        with open(file, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                digest.update(chunk)
    return digest.hexdigest()


def embedding_state(encoder):
    """The model and the stored vectors of Published activities."""
    vectors = hashlib.sha256()
    rows = (
        ActivityEmbedding.objects.filter(model_name=encoder.name)
        .filter(activity__in=DevelopmentalActivity.objects.published())
        .order_by("activity__activity_id")
        .values_list("activity__activity_id", "vector")
    )
    count = 0
    for activity_id, vector in rows:
        vectors.update(activity_id.encode("utf-8"))
        vectors.update(bytes(vector))
        count += 1
    files = None
    if isinstance(encoder, embeddings.SentenceTransformerEncoder):
        files = model_files_sha256(settings.SBERT_MODEL_PATH)
    return {
        "model_name": encoder.name,
        "dimensions": encoder.dimensions,
        "embedded_activities": count,
        "vectors_sha256": vectors.hexdigest(),
        "model_files_sha256": files,
    }


def _git_commit():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=settings.BASE_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def sheet_rows_sha256(rows):
    """Hash of the sheet's (child_id, activity_id) pairs, order ignored."""
    return _sha256(sorted([c, a] for c, ids in rows.items() for a in ids))


def snapshot(rows=None):
    """The current state; `rows` is {child_id: [activity_id, ...]} if known."""
    activities = DevelopmentalActivity.objects.published().order_by("activity_id")
    state = {
        "format": FORMAT,
        "activities": {a.activity_id: activity_hash(a) for a in activities},
        "rule_weights": rule_weights(),
        "ranking": ranking_settings(),
        "catalogue": catalogue_version(),
        "embedding": embedding_state(embeddings.get_encoder()),
        "info": {
            "generated_at": timezone.now().isoformat(timespec="seconds"),
            "git_commit": _git_commit(),
            "verified_milestones": ReferenceMilestone.objects.filter(
                verified=True
            ).count(),
        },
    }
    if rows is not None:
        state["sheet_rows_sha256"] = sheet_rows_sha256(rows)
    return state


def write(path, state):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _changed_keys(old, new):
    return sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))


def differences(recorded, current):
    """Plain-English list of what differs between two snapshots."""
    found = []
    if recorded.get("format") != current.get("format"):
        found.append(
            f"sidecar format {recorded.get('format')} (expected {current['format']})"
        )
    old, new = recorded.get("activities", {}), current["activities"]
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    edited = sorted(a for a in set(old) & set(new) if old[a] != new[a])
    if added:
        found.append("Published activities added: " + ", ".join(added))
    if removed:
        found.append(
            "activities no longer Published (or deleted): " + ", ".join(removed)
        )
    if edited:
        found.append("activity content changed: " + ", ".join(edited))
    for section, label in (
        ("rule_weights", "rule weights"),
        ("ranking", "ranking settings"),
        ("catalogue", "reference milestone catalogue"),
        ("embedding", "embeddings"),
    ):
        keys = _changed_keys(recorded.get(section, {}), current[section])
        if keys:
            found.append(f"{label} changed: " + ", ".join(keys))
    if "sheet_rows_sha256" in current and recorded.get(
        "sheet_rows_sha256"
    ) != current.get("sheet_rows_sha256"):
        found.append("the sheet's (child_id, activity_id) rows were added or removed")
    return found
