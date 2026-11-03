"""Learn from a child's feedback when generating their ideas (#179).

The evaluated ranking (rank(), tag sprint9-eval-v2) knows nothing about
how earlier ideas went. This step, applied by generation.generate() after
ranking, adjusts each score using the child's feedback (#175):

- an activity that went well raises activities similar to it;
- an activity that didn't work lowers activities similar to it, and is not
  suggested again.

"Similar" is the cosine similarity of the stored activity embeddings, above
SIMILARITY_FLOOR, scaled to 0-1. Activities for babies share a lot of words,
so with all-MiniLM-L6-v2 most pairs in an area score about 0.6; the floor
keeps that shared background from counting, and BOOST and PENALTY are equal
so that "went well" and "didn't work" signals balance rather than drag every
score one way. An activity that went well is never penalised itself. Scores
stay within 0-1. A child with no feedback gets the
evaluated ranking unchanged, so the held-out evaluation (whose children
have no feedback, and which calls rank_candidates directly) is unaffected.
"""

from dataclasses import dataclass, replace

import numpy as np

from feedback.models import Feedback

from . import embeddings
from .models import ActivityEmbedding

SIMILARITY_FLOOR = 0.5
BOOST = 0.25
PENALTY = 0.25
# Only a boost at least this big is mentioned in the explanation, and only
# for the MAX_NOTES strongest in a batch, so the same sentence isn't repeated
# on every idea.
MENTION_BOOST = 0.03
MAX_NOTES = 2

LIKED, DISLIKED = "liked", "disliked"


@dataclass(frozen=True)
class Personalised:
    ranked: list  # RankedActivity, re-sorted, scores adjusted
    excluded: set  # activity pks not to suggest again
    notes: dict  # {activity pk: (boost, sentence for the explanation)}

    def notes_for(self, pks):
        """{pk: sentence} for the MAX_NOTES strongest boosts among pks."""
        strongest = sorted(
            (pk for pk in pks if pk in self.notes),
            key=lambda pk: -self.notes[pk][0],
        )[:MAX_NOTES]
        return {pk: self.notes[pk][1] for pk in strongest}


def signals(child):
    """{activity pk: (LIKED or DISLIKED, activity name)} from the child's
    latest feedback on each activity.

    An outcome decides (went well / didn't work; "partly" is neither).
    Feedback from before outcomes were asked falls back to the rating:
    4-5 liked, 1-2 disliked.
    """
    latest = {}
    rows = (
        Feedback.objects.filter(recommendation__child=child)
        .select_related("recommendation__activity")
        .order_by("date_submitted", "pk")
    )
    for f in rows:
        latest[f.recommendation.activity_id] = f
    found = {}
    for pk, f in latest.items():
        if f.outcome == Feedback.Outcome.WENT_WELL or (not f.outcome and f.rating >= 4):
            kind = LIKED
        elif f.outcome == Feedback.Outcome.DIDNT_WORK or (
            not f.outcome and f.rating <= 2
        ):
            kind = DISLIKED
        else:
            continue
        found[pk] = (kind, f.recommendation.activity.activity_name)
    return found


def _vectors(pks):
    return {
        row.activity_id: embeddings.from_bytes(row.vector)
        for row in ActivityEmbedding.objects.filter(activity_id__in=pks)
    }


def _strength(similarity):
    """Similarity above the floor, scaled to 0-1."""
    return max(0.0, (similarity - SIMILARITY_FLOOR) / (1.0 - SIMILARITY_FLOOR))


def personalise(child, ranked):
    """The ranked list adjusted by the child's feedback (see module doc)."""
    found = signals(child)
    if not found:
        return Personalised(ranked=list(ranked), excluded=set(), notes={})
    liked = {pk for pk, (kind, _) in found.items() if kind == LIKED}
    disliked = {pk for pk, (kind, _) in found.items() if kind == DISLIKED}
    vectors = _vectors({r.activity.pk for r in ranked} | set(found))

    adjusted, notes = [], {}
    for r in ranked:
        pk = r.activity.pk
        vector = vectors.get(pk)
        if vector is None:
            adjusted.append(r)
            continue
        boost, because = 0.0, None
        for other in liked:
            if other == pk or other not in vectors:
                continue
            gain = BOOST * _strength(float(np.dot(vector, vectors[other])))
            if gain > boost:
                boost, because = gain, found[other][1]
        penalty = 0.0
        if pk not in liked:
            penalty = max(
                (
                    PENALTY * _strength(float(np.dot(vector, vectors[other])))
                    for other in disliked
                    if other != pk and other in vectors
                ),
                default=0.0,
            )
        score = min(1.0, max(0.0, r.score + boost - penalty))
        adjusted.append(replace(r, score=score))
        if because and boost >= MENTION_BOOST and boost > penalty:
            notes[pk] = (
                boost,
                f"It's similar to “{because}”, which went well for {child.name}.",
            )
    adjusted.sort(key=lambda r: (-r.score, -r.similarity, r.activity.activity_id))
    return Personalised(ranked=adjusted, excluded=disliked, notes=notes)
