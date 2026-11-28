"""Explore: browse and search activities for a child (#194).

The pool is every Published, embedded activity that suits the child's age:
before birth, pregnancy activities only; after birth, the child's own age
band and its neighbours (age weight at least MIN_AGE_WEIGHT). Activities
the child has completed are left out.

- **Without a search,** activities are ordered by age fit and then by the
  rule engine's priority for their area, so the areas the child needs most
  come first.
- **With a search,** the text is encoded with SBERT and compared by
  meaning with the stored activity embeddings, the same vectors retrieval
  uses, weighted by age fit. "Messy play with water" finds water and
  texture activities without those exact words.
- **For the child's interests** (#288), each interest is compared on its
  own and an activity keeps its best match, so one strong match counts
  ("animals, music" finds animal and music ideas, not ideas vaguely about
  "a child who enjoys" things). The meaning score is mixed with word
  overlap (TF-IDF, weight INTEREST_LEXICAL_WEIGHT), and activities whose
  match is below INTEREST_FLOOR are left out, so the row is short rather
  than padded with unrelated ideas. Explore only: recommendations and the
  evaluation are unchanged.

Browsing never changes the child's ideas; "Try this" pins one (#177).
"""

from dataclasses import dataclass

import numpy as np

from activities.choices import AgeRange, ContentStatus, Difficulty
from profiles.rules import build_profile

from . import embeddings, lexical
from .generation import completed_activity_ids
from .models import ActivityEmbedding, SavedActivity
from .ranking import age_weight, child_bracket

MIN_AGE_WEIGHT = 0.5  # the child's band, one younger (0.7) or one older (0.5)
QUICK_MAX_CHARS = 220  # a Beginner activity this short is "quick"
DEFAULT_LIMIT = 30
# Interests row (#288). Chosen on the 27 Nov catalogue with six interests for
# a 14-month-old, swept over word weights 0-1 and floors 0.14-0.22, keeping
# the setting that showed the most relevant ideas (36 of 41 shown; keyword
# check, not graded labels). A heavier word weight was more precise but cut
# rows to 3-4 ideas. Explore only; retrieval for the weekly ideas keeps
# RETRIEVAL_BETA.
INTEREST_LEXICAL_WEIGHT = 0.25
INTEREST_FLOOR = 0.20
MAX_LIMIT = 100


@dataclass(frozen=True)
class Found:
    activity: object
    score: float
    saved: bool


def _pool(child, on_date):
    evaluation = build_profile(child, on_date=on_date)
    prenatal = child_bracket(evaluation.age_months) is None
    done = completed_activity_ids(child)
    rows = ActivityEmbedding.objects.filter(
        activity__content_status=ContentStatus.PUBLISHED
    ).select_related("activity")
    pool = []
    for row in rows:
        activity = row.activity
        if activity.pk in done:
            continue
        if (activity.age_range == AgeRange.PRENATAL) != prenatal:
            continue
        weight = age_weight(evaluation.age_months, activity.age_range)
        if weight < MIN_AGE_WEIGHT:
            continue
        pool.append((activity, embeddings.from_bytes(row.vector), weight))
    return pool, evaluation


def child_interests(child):
    """The child's interests, tidied (empty ones dropped)."""
    return [str(i).strip() for i in child.interests if str(i).strip()]


def interest_scores(interests, pool):
    """Each pooled activity's best match with any one interest: meaning
    (SBERT) mixed with word overlap (TF-IDF)."""
    vectors = np.stack([v for _, v, _ in pool])
    queries = embeddings.get_encoder().encode(interests)
    meaning = np.max(np.stack([vectors @ q for q in queries]), axis=0)
    pks = [a.pk for a, _, _ in pool]
    words = np.max(np.stack([lexical.similarities(i, pks) for i in interests]), axis=0)
    return (1 - INTEREST_LEXICAL_WEIGHT) * meaning + INTEREST_LEXICAL_WEIGHT * words


def browse(
    child,
    query="",
    area=None,
    no_materials=False,
    quick=False,
    saved_only=False,
    limit=DEFAULT_LIMIT,
    on_date=None,
    interests=None,
):
    """[Found], best first. `interests` (a list) ranks by the child's
    interests instead of `query` (#288)."""
    pool, evaluation = _pool(child, on_date)
    saved = set(
        SavedActivity.objects.filter(child=child).values_list("activity_id", flat=True)
    )

    def keep(activity):
        if area and activity.developmental_domain != area:
            return False
        if no_materials and activity.materials.strip().lower() not in ("", "none"):
            return False
        if quick and not (
            activity.difficulty_level == Difficulty.BEGINNER
            and len(activity.description) <= QUICK_MAX_CHARS
        ):
            return False
        return not saved_only or activity.pk in saved

    pool = [p for p in pool if keep(p[0])]
    query = (query or "").strip()
    if interests:
        matches = interest_scores(interests, pool) if pool else []
        scored = [
            (a, float(match) * w)
            for (a, _, w), match in zip(pool, matches)
            if match >= INTEREST_FLOOR
        ]
    elif query:
        vector = embeddings.get_encoder().encode([query])[0]
        scored = [(a, float(np.dot(v, vector)) * w) for a, v, w in pool]
    else:
        scores = evaluation.scores
        scored = [
            (a, w * (0.5 + 0.5 * scores.get(a.developmental_domain, 0.0)))
            for a, _, w in pool
        ]
    scored.sort(key=lambda x: (-x[1], x[0].activity_name))
    return [Found(a, s, a.pk in saved) for a, s in scored[:limit]]
