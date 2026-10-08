"""Weighted ranking: combine rule priority and semantic similarity (FR-07).

For each eligible activity a, for child c:

    score(a) = age_weight(c, a) * ((1 - alpha) * sim_norm(a)
                                   + alpha * priority(c, domain(a)))

- sim_norm: SBERT cosine similarity, min-max normalised to 0-1 across the
  child's candidate pool, so both signals are on the same scale and alpha
  means what it says.
- priority: the rule engine's 0-1 score for the activity's domain (top
  domain = 1.0).
- alpha: the only tuned parameter (grid search, #37). alpha = 0 ranks by
  similarity only, alpha = 1 by rule priority only.
- age_weight: a fixed, documented design choice, applied as a multiplier so
  it scales a score rather than competing with the two signals.

Ties are broken by raw similarity, then activity ID, so the order is stable.
"""

from dataclasses import dataclass

from django.conf import settings

from activities.choices import AgeRange

from .retrieval import retrieve

# Post-natal age brackets in order, with their [start, end) in months.
AGE_BRACKETS = (
    (AgeRange.MONTHS_0_3, 0, 3),
    (AgeRange.MONTHS_3_6, 3, 6),
    (AgeRange.MONTHS_6_12, 6, 12),
    (AgeRange.MONTHS_12_18, 12, 18),
    (AgeRange.MONTHS_18_24, 18, 24),
    (AgeRange.MONTHS_24_36, 24, 36),
)
BRACKET_INDEX = {age_range: i for i, (age_range, _, _) in enumerate(AGE_BRACKETS)}

# Age-appropriateness weights by bracket distance (activity - child), agreed
# for Sprint 5. Asymmetric: a delayed child usually needs the previous
# bracket's skills, while the next bracket up is more likely to be too
# advanced. Never zero, so a highly relevant activity can still surface.
SAME_BRACKET = 1.0
ONE_YOUNGER = 0.7
ONE_OLDER = 0.5
TWO_AWAY = 0.25
FURTHER = 0.1


def child_bracket(age_months):
    """Index of the bracket containing the child's age (start inclusive).

    None for prenatal profiles; ages of 36 months or more map to the last
    bracket.
    """
    if age_months is None or age_months < 0:
        return None
    for i, (_, start, end) in enumerate(AGE_BRACKETS):
        if start <= age_months < end:
            return i
    return len(AGE_BRACKETS) - 1


def age_weight(age_months, activity_age_range):
    """How well an activity's age range suits a child of age_months."""
    child = child_bracket(age_months)
    if child is None or activity_age_range == AgeRange.PRENATAL:
        # Prenatal and post-natal activities never mix (hard filter in
        # retrieval), so within the prenatal pool every activity fits.
        return SAME_BRACKET
    distance = BRACKET_INDEX[activity_age_range] - child
    if distance == 0:
        return SAME_BRACKET
    if distance == -1:
        return ONE_YOUNGER
    if distance == 1:
        return ONE_OLDER
    if abs(distance) == 2:
        return TWO_AWAY
    return FURTHER


@dataclass(frozen=True)
class RankedActivity:
    activity: object
    score: float
    similarity: float
    similarity_norm: float
    priority: float
    age_weight: float


@dataclass(frozen=True)
class RankingResult:
    query: str
    evaluation: object
    alpha: float
    ranked: list


def validate_alpha(alpha):
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be between 0 and 1, got {alpha}")
    return float(alpha)


def rank_candidates(candidates, evaluation, alpha, use_age=True):
    """Score and sort retrieval candidates; pure, so it is easy to test."""
    alpha = validate_alpha(alpha)
    if not candidates:
        return []
    sims = [c.similarity for c in candidates]
    low, high = min(sims), max(sims)
    ranked = []
    for candidate in candidates:
        activity = candidate.activity
        sim_norm = (candidate.similarity - low) / (high - low) if high > low else 1.0
        priority = evaluation.scores[activity.developmental_domain]
        weight = (
            age_weight(evaluation.age_months, activity.age_range) if use_age else 1.0
        )
        score = weight * ((1 - alpha) * sim_norm + alpha * priority)
        ranked.append(
            RankedActivity(
                activity=activity,
                score=score,
                similarity=candidate.similarity,
                similarity_norm=sim_norm,
                priority=priority,
                age_weight=weight,
            )
        )
    ranked.sort(key=lambda r: (-r.score, -r.similarity, r.activity.activity_id))
    return ranked


def rank(child, alpha=None, limit=None, on_date=None, use_age=True):
    """Rank every eligible Published, embedded activity for the child."""
    alpha = settings.RANKING_ALPHA if alpha is None else alpha
    retrieval = retrieve(child, limit=None, on_date=on_date)
    ranked = rank_candidates(retrieval.candidates, retrieval.evaluation, alpha, use_age)
    return RankingResult(
        query=retrieval.query,
        evaluation=retrieval.evaluation,
        alpha=validate_alpha(alpha),
        ranked=ranked[:limit],
    )
