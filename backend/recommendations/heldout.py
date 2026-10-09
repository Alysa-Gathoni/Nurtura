"""Held-out evaluation children for choosing alpha (#37).

Twenty sample children, separate from the seven spot-check development
children in samples.py, built from real catalogue milestones and caregiver
concerns. Each has a fixed split, assigned before any labelling:

- tune (11): alpha is selected on these only.
- test (8): final precision@k and nDCG@k at the chosen alpha.
- gap (1): H17, a Sensory child aged 18-24 months, where there is no
  Published content; labelled, but reported separately and excluded from
  tune and test.

The split came from stratified_split(): stratified by domain stratum,
largest-remainder allocation of 60% to tune, seed 2026. H17 was then moved
to "gap". Stored explicitly so the split never changes after labelling.
"""

import datetime
import math
import random
from dataclasses import dataclass

from django.utils import timezone

from profiles.models import ChildProfile, ReferenceMilestone

from .ranking import rank_candidates
from .retrieval import retrieve

SPLIT_SEED = 2026
TUNE_SHARE = 0.6
SPLITS = ("tune", "test", "gap")
AVERAGE_DAYS_PER_MONTH = 365.25 / 12

# The grid searched for alpha, and the cut-offs reported (#37).
ALPHAS = tuple(i / 10 for i in range(11))
KS = (3, 5)
POOL_DEPTH = max(KS)
BASELINE = "sbert-only"  # similarity order: no rule priority, no age weighting
SHUFFLE_SEED = 2026


@dataclass(frozen=True)
class HeldOutChild:
    child_id: str
    split: str
    stratum: str  # domain used for stratifying the split
    age_months: float  # negative = months until the due date
    profile: str  # plain-English description shown to the labeller
    not_yet: tuple = ()  # catalogue milestones observed as Not yet
    achieved: tuple = ()  # catalogue milestones observed as Achieved
    concerns: tuple = ()
    interests: tuple = ()
    content_gap: bool = False


HELDOUT_CHILDREN = (
    HeldOutChild(
        "H01",
        "tune",
        "Language",
        -2,
        "Expecting parent, due in about 2 months, would like support with the "
        "baby's language (talking and singing to the bump).",
        concerns=("Language",),
    ),
    HeldOutChild(
        "H02",
        "test",
        "Socio-Emotional",
        -4,
        "Expecting parent, due in about 4 months, would like support with "
        "bonding and emotional wellbeing.",
        concerns=("Socio-Emotional",),
    ),
    HeldOutChild(
        "H03",
        "test",
        "Motor",
        2.5,
        "2½ months old, not yet holding head up when on tummy (most babies do "
        "by 2 months).",
        not_yet=("CDC-02M-MO-01",),
    ),
    HeldOutChild(
        "H04",
        "test",
        "Socio-Emotional",
        2.5,
        "2½ months old, not yet smiling when talked to or smiled at (most "
        "babies do by 2 months).",
        not_yet=("CDC-02M-SE-04",),
    ),
    HeldOutChild(
        "H05",
        "tune",
        "Language",
        5,
        "5 months old, not yet making sounds back when talked to (most babies "
        "do by 4 months).",
        not_yet=("CDC-04M-LA-02",),
    ),
    HeldOutChild(
        "H06",
        "tune",
        "Cognitive",
        5,
        "5 months old, not yet looking at their hands with interest (most "
        "babies do by 4 months).",
        not_yet=("CDC-04M-CO-02",),
    ),
    HeldOutChild(
        "H07",
        "test",
        "Sensory",
        4.5,
        "4½ months old; the caregiver would like support with sensory "
        "development; the baby enjoys music and rattles.",
        concerns=("Sensory",),
        interests=("music", "rattles"),
    ),
    HeldOutChild(
        "H08",
        "tune",
        "Motor",
        8,
        "8 months old, not yet rolling from tummy to back (most babies do by "
        "6 months).",
        not_yet=("CDC-06M-MO-01",),
    ),
    HeldOutChild(
        "H09",
        "tune",
        "Socio-Emotional",
        11,
        "11 months old, not yet smiling or laughing at peek-a-boo (most babies "
        "do by 9 months).",
        not_yet=("CDC-09M-SE-05",),
    ),
    HeldOutChild(
        "H10",
        "test",
        "None",
        7,
        "7 months old and on track: laughs and rolls from tummy to back; no "
        "concerns.",
        achieved=("CDC-06M-SE-03", "CDC-06M-MO-01"),
    ),
    HeldOutChild(
        "H11",
        "tune",
        "Language",
        14,
        "14 months old, not yet waving bye-bye or calling a parent mama or dada "
        "(most children do by 12 months).",
        not_yet=("CDC-12M-LA-01", "CDC-12M-LA-02"),
    ),
    HeldOutChild(
        "H12",
        "tune",
        "Cognitive",
        16,
        "16 months old, not yet stacking two small objects like blocks (most "
        "children do by 15 months).",
        not_yet=("CDC-15M-CO-02",),
    ),
    HeldOutChild(
        "H13",
        "tune",
        "Sensory",
        13,
        "13 months old; the caregiver would like support with sensory "
        "development; the child enjoys water play and sand.",
        concerns=("Sensory",),
        interests=("water play", "sand"),
    ),
    HeldOutChild(
        "H14",
        "test",
        "Mixed",
        15.5,
        "15½ months old, not yet taking a few steps alone or showing affection "
        "with hugs (most children do both by 15 months).",
        not_yet=("CDC-15M-MO-01", "CDC-15M-SE-05"),
    ),
    HeldOutChild(
        "H15",
        "test",
        "Cognitive",
        20,
        "20 months old, not yet playing with toys in a simple way, like pushing "
        "a toy car (most children do by 18 months).",
        not_yet=("CDC-18M-CO-02",),
    ),
    HeldOutChild(
        "H16",
        "tune",
        "Socio-Emotional",
        22,
        "22 months old, not yet pointing to show you something interesting "
        "(most children do by 18 months).",
        not_yet=("CDC-18M-SE-02",),
    ),
    HeldOutChild(
        "H17",
        "gap",
        "Sensory",
        20,
        "20 months old; the caregiver would like support with sensory "
        "development; the child enjoys textures.",
        concerns=("Sensory",),
        interests=("textures",),
        content_gap=True,
    ),
    HeldOutChild(
        "H18",
        "test",
        "Language",
        27,
        "27 months old, not yet putting two words together or pointing to two "
        "body parts (most children do by 24 months).",
        not_yet=("CDC-24M-LA-02", "CDC-24M-LA-03"),
    ),
    HeldOutChild(
        "H19",
        "tune",
        "Mixed",
        31,
        "31 months old, not yet showing simple problem-solving (like using a "
        "stool to reach something) or jumping with both feet (most children do "
        "both by 30 months).",
        not_yet=("CDC-30M-CO-02", "CDC-30M-MO-03"),
    ),
    HeldOutChild(
        "H20",
        "tune",
        "None",
        34,
        "34 months old and on track: says about 50 words and jumps with both "
        "feet; no concerns.",
        achieved=("CDC-30M-LA-01", "CDC-30M-MO-03"),
    ),
)

HELDOUT_BY_ID = {child.child_id: child for child in HELDOUT_CHILDREN}


def stratified_split(children, seed=SPLIT_SEED, tune_share=TUNE_SHARE):
    """The procedure that produced the stored splits (kept for the record).

    Stratified by `stratum`; each stratum gets floor(n * tune_share) tune
    children, and the remaining tune places go to the strata with the
    largest remainders (ties broken by the seeded random generator). Within a
    stratum, children are shuffled with the same generator.
    """
    rng = random.Random(seed)
    strata = {}
    for child in children:
        strata.setdefault(child.stratum, []).append(child.child_id)
    target = round(len(children) * tune_share)
    quotas = {s: len(ids) * tune_share for s, ids in strata.items()}
    tune_n = {s: math.floor(q) for s, q in quotas.items()}
    order = sorted(strata, key=lambda s: (-(quotas[s] - tune_n[s]), rng.random()))
    for stratum in order[: target - sum(tune_n.values())]:
        tune_n[stratum] += 1
    assignment = {}
    for stratum in sorted(strata):
        ids = sorted(strata[stratum])
        rng.shuffle(ids)
        for i, child_id in enumerate(ids):
            assignment[child_id] = "tune" if i < tune_n[stratum] else "test"
    return assignment


def milestone_keys():
    """Every catalogue milestone the held-out children use, sorted."""
    return sorted({k for c in HELDOUT_CHILDREN for k in c.not_yet + c.achieved})


def create_child(child, caregiver, today=None):
    """Create the child and its observations (callers roll back)."""
    today = today or timezone.localdate()
    date_of_birth = today - datetime.timedelta(
        days=round(child.age_months * AVERAGE_DAYS_PER_MONTH) + 1
    )
    profile = ChildProfile.objects.create(
        caregiver=caregiver,
        name=child.child_id,
        date_of_birth=date_of_birth,
        concerns=list(child.concerns),
        interests=list(child.interests),
    )
    for keys, status in ((child.not_yet, "not_yet"), (child.achieved, "achieved")):
        for key in keys:
            profile.record_milestone(
                reference=ReferenceMilestone.objects.get(milestone_key=key),
                status=status,
                observation_date=today,
            )
    return profile


def rankings_for(profile, alphas=ALPHAS):
    """Every evaluated ordering of the child's activities, from one retrieval.

    Returns (activities by ID, {BASELINE or alpha: [activity_id, ...]}).
    """
    retrieval = retrieve(profile, limit=None)
    activities = {c.activity.activity_id: c.activity for c in retrieval.candidates}
    rankings = {BASELINE: [c.activity.activity_id for c in retrieval.candidates]}
    for alpha in alphas:
        ranked = rank_candidates(retrieval.candidates, retrieval.evaluation, alpha)
        rankings[alpha] = [r.activity.activity_id for r in ranked]
    return activities, rankings


def pool(rankings, depth=POOL_DEPTH):
    """Union of every ranking's top `depth`, in first-seen order."""
    seen = {}
    for ranked_ids in rankings.values():
        for activity_id in ranked_ids[:depth]:
            seen.setdefault(activity_id, None)
    return list(seen)


def shuffled(activity_ids, child_id, seed=SHUFFLE_SEED):
    """The pool in a fixed random order, so row order reveals no rank."""
    ids = sorted(activity_ids)
    random.Random(f"{seed}-{child_id}").shuffle(ids)
    return ids
