"""Options offered after a caregiver's feedback (#177).

When a caregiver says how an activity went (#175), they are offered up to
MAX_OPTIONS other activities, each answering one thing that went wrong:
an easier one when it was too hard, one that needs nothing special when the
materials were missing, and so on. Each option says why it is offered.

The options come from the same pool as recommendations (Published, embedded
activities on the right side of birth), leaving out the activity itself,
anything the child has done and anything already in the newest batch.
"Similar" means cosine similarity between the stored activity embeddings
(one per activity, from embed_activities), so no model is loaded here.
"""

from dataclasses import dataclass

import numpy as np

from activities.choices import AgeRange, Difficulty, Domain
from feedback.models import Feedback
from profiles.rules.facts import age_in_months

from . import embeddings
from .models import ActivityEmbedding
from .ranking import BRACKET_INDEX, child_bracket

MAX_OPTIONS = 3
DIFFICULTY_ORDER = [Difficulty.BEGINNER, Difficulty.INTERMEDIATE, Difficulty.ADVANCED]
CALM_WORDS = ("calm", "sooth", "gentle", "cuddle", "relax", "quiet", "settle")
NO_MATERIALS = ("", "none")

UPSET_TIP = (
    "Try again another day, when your child is rested and calm, and stop if "
    "they get upset."
)


@dataclass(frozen=True)
class Option:
    reason: str  # stable key, e.g. "too_hard"
    title: str
    why: str
    activity: object
    tip: str = ""


def _difficulty(activity):
    try:
        return DIFFICULTY_ORDER.index(activity.difficulty_level)
    except ValueError:
        return 0


def _band(activity):
    return BRACKET_INDEX.get(activity.age_range)


def _is_calm(activity):
    text = f"{activity.activity_name} {activity.description}".lower()
    return any(word in text for word in CALM_WORDS)


class _Pool:
    """Eligible activities for a child, with their stored vectors."""

    def __init__(self, recommendation, exclude_ids):
        child = recommendation.child
        self.age = age_in_months(child.date_of_birth, _today())
        self.band = child_bracket(self.age)  # None before birth
        self.original = recommendation.activity
        rows = ActivityEmbedding.objects.filter(
            activity__content_status="published"
        ).select_related("activity")
        self.items = []
        for row in rows:
            activity = row.activity
            if activity.pk in exclude_ids or activity.pk == self.original.pk:
                continue
            prenatal = activity.age_range == AgeRange.PRENATAL
            if prenatal != (self.band is None):
                continue  # pregnancy and baby activities never mix
            self.items.append((activity, embeddings.from_bytes(row.vector)))
        original = ActivityEmbedding.objects.filter(activity=self.original).first()
        self.origin_vector = (
            embeddings.from_bytes(original.vector) if original else None
        )

    def similarity(self, vector):
        if self.origin_vector is None:
            return 0.0
        return float(np.dot(vector, self.origin_vector))

    def same_area(self, band_offset=0):
        """Same domain, in the child's band (+ offset); prenatal ignores bands."""
        domain = self.original.developmental_domain
        for activity, vector in self.items:
            if activity.developmental_domain != domain:
                continue
            if self.band is not None and _band(activity) != self.band + band_offset:
                continue
            yield activity, vector

    def in_band(self):
        for activity, vector in self.items:
            if self.band is None or _band(activity) == self.band:
                yield activity, vector


def _today():
    from django.utils import timezone

    return timezone.localdate()


def _most_similar(pool, candidates, taken):
    ranked = sorted(
        ((a, pool.similarity(v)) for a, v in candidates if a.pk not in taken),
        key=lambda x: (-x[1], x[0].activity_id),
    )
    return ranked[0][0] if ranked else None


def _pick(pool, reason, taken):
    original = pool.original
    level = _difficulty(original)
    if reason == Feedback.Issue.TOO_HARD:
        easier = [
            (a, v) for a, v in pool.same_area() if _difficulty(a) < level
        ] or list(pool.same_area(-1))
        return _most_similar(pool, easier, taken)
    if reason == Feedback.Issue.TOO_EASY:
        harder = [
            (a, v) for a, v in pool.same_area() if _difficulty(a) > level
        ] or list(pool.same_area(+1))
        return _most_similar(pool, harder, taken)
    if reason == Feedback.Issue.NOT_INTERESTED:
        # Something genuinely different in the same area: least similar.
        ranked = sorted(
            ((a, pool.similarity(v)) for a, v in pool.same_area() if a.pk not in taken),
            key=lambda x: (x[1], x[0].activity_id),
        )
        return ranked[0][0] if ranked else None
    if reason == Feedback.Issue.NO_MATERIALS:
        bare = [
            (a, v)
            for a, v in pool.same_area()
            if a.materials.strip().lower() in NO_MATERIALS
        ]
        return _most_similar(pool, bare, taken)
    if reason == Feedback.Issue.NO_TIME:
        quick = sorted(
            (
                (a, v)
                for a, v in pool.same_area()
                if a.difficulty_level == Difficulty.BEGINNER and a.pk not in taken
            ),
            key=lambda x: (len(x[0].description), x[0].activity_id),
        )
        return quick[0][0] if quick else None
    if reason == Feedback.Issue.CHILD_UPSET:
        calm = [
            (a, v)
            for a, v in pool.in_band()
            if a.developmental_domain in (Domain.SOCIO_EMOTIONAL, Domain.SENSORY)
            and _is_calm(a)
        ]
        return _most_similar(pool, calm, taken)
    # "more_like_this" and "same_area"
    return _most_similar(pool, pool.same_area(), taken)


TITLES = {
    Feedback.Issue.TOO_HARD: "An easier one",
    Feedback.Issue.TOO_EASY: "A bigger challenge",
    Feedback.Issue.NOT_INTERESTED: "Something different",
    Feedback.Issue.NO_MATERIALS: "Needs nothing special",
    Feedback.Issue.NO_TIME: "A quicker idea",
    Feedback.Issue.CHILD_UPSET: "A calmer idea",
    "more_like_this": "More like this",
    "same_area": "Another idea for the same skills",
}


def _why(reason, name):
    return {
        Feedback.Issue.TOO_HARD: f"You said “{name}” was too hard, so this one "
        "is simpler.",
        Feedback.Issue.TOO_EASY: f"You said “{name}” was too easy, so this one "
        "is a step up.",
        Feedback.Issue.NOT_INTERESTED: f"Your child wasn't interested in “{name}”, "
        "so this one works on the same skills in a different way.",
        Feedback.Issue.NO_MATERIALS: f"You didn't have the materials for “{name}”; "
        "this one needs nothing special.",
        Feedback.Issue.NO_TIME: f"“{name}” took too long, so this one is quick.",
        Feedback.Issue.CHILD_UPSET: f"Your child got upset during “{name}”, so this "
        "one is calm and gentle.",
        "more_like_this": f"“{name}” went well, and this one is similar.",
        "same_area": f"Another way to work on the same skills as “{name}”.",
    }[reason]


def reasons_for(feedback):
    """The reasons to answer, in order, from the latest feedback."""
    if feedback is None or not feedback.outcome:
        return []
    if feedback.outcome == Feedback.Outcome.WENT_WELL:
        return ["more_like_this", "same_area"]
    return [*feedback.issues, "same_area"]


def options_for(recommendation, feedback, exclude_ids=()):
    """Up to MAX_OPTIONS Options for the caregiver's latest feedback."""
    reasons = reasons_for(feedback)
    if not reasons:
        return []
    pool = _Pool(recommendation, set(exclude_ids))
    options, taken = [], set()
    for reason in reasons:
        if len(options) == MAX_OPTIONS:
            break
        activity = _pick(pool, reason, taken)
        if activity is None:
            continue
        taken.add(activity.pk)
        options.append(
            Option(
                reason=str(reason),
                title=TITLES[reason],
                why=_why(reason, recommendation.activity.activity_name),
                activity=activity,
                tip=UPSET_TIP if reason == Feedback.Issue.CHILD_UPSET else "",
            )
        )
    return options
