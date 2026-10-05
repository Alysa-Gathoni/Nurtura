"""Semantic retrieval: match a child's developmental profile to activities (FR-06).

At request time the child's profile (from the rule engine) is turned into a
plain-language query, encoded with SBERT, and compared by cosine similarity
with the precomputed embeddings of Published activities. The result is a list
of candidates; combining similarity with rule priority, age and preferences
into the final ranking is Sprint 5.

One age rule is applied here because it isn't a matter of degree: pregnancy
activities are only for expecting parents, and are never suggested once the
baby is born. Finer age-appropriateness weighting is part of Sprint 5.
"""

from dataclasses import dataclass

import numpy as np
from django.utils import timezone

from activities.choices import AgeRange, ContentStatus
from profiles.models import DevelopmentalMilestone
from profiles.rules import build_profile
from profiles.rules.facts import MilestoneFact

from . import embeddings
from .models import ActivityEmbedding

# Domains scoring at least this much (top domain = 1.0) shape the query.
FOCUS_THRESHOLD = 0.5
DEFAULT_LIMIT = 10
MAX_LIMIT = 50

# What each domain means in everyday words, so the query matches activity text.
DOMAIN_DESCRIPTIONS = {
    "Language": "language and communication: talking, babbling, first words, "
    "listening, singing and reading together",
    "Motor": "movement and physical skills: tummy time, rolling, crawling, "
    "walking, balance, and using hands and fingers",
    "Cognitive": "thinking and problem-solving: exploring objects, cause and "
    "effect, hiding and finding, sorting and puzzles",
    "Sensory": "the senses: touch and textures, sounds and music, sights, and "
    "calming sensory play",
    "Socio-Emotional": "social and emotional development: bonding, feelings, "
    "smiling, copying and playing with others",
}


@dataclass(frozen=True)
class Candidate:
    activity: object
    similarity: float


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    evaluation: object
    candidates: list


def _age_phrase(age_months):
    if age_months is None:
        return "a young child"
    if age_months < 0:
        return "an expecting parent during pregnancy"
    months = int(age_months)
    if months < 1:
        return "a newborn baby"
    if months < 12:
        return f"a {months}-month-old baby"
    return f"a {months}-month-old toddler"


def profile_query(evaluation, child):
    """Plain-language description of what the child needs right now."""
    focus = [
        domain
        for domain in evaluation.ranked_domains()
        if evaluation.scores[domain] >= FOCUS_THRESHOLD
    ]
    sentences = [
        f"Activities for {_age_phrase(evaluation.age_months)} to support "
        + "; and ".join(DOMAIN_DESCRIPTIONS[d] for d in focus)
        + "."
    ]

    not_yet = []
    for firing in evaluation.firings:
        fact = firing.fact
        if (
            isinstance(fact, MilestoneFact)
            and fact.status != DevelopmentalMilestone.Status.ACHIEVED
            and fact.description not in not_yet
        ):
            not_yet.append(fact.description)
    if not_yet:
        sentences.append("Still working on: " + "; ".join(not_yet) + ".")

    interests = [str(i).strip() for i in child.interests if str(i).strip()]
    if interests:
        sentences.append("Enjoys " + ", ".join(interests) + ".")
    return " ".join(sentences)


def retrieve(child, limit=DEFAULT_LIMIT, on_date=None):
    """Top Published activities by cosine similarity to the child's profile."""
    on_date = on_date or timezone.localdate()
    evaluation = build_profile(child, on_date=on_date)
    query = profile_query(evaluation, child)

    encoder = embeddings.get_encoder()
    eligible = ActivityEmbedding.objects.filter(
        activity__content_status=ContentStatus.PUBLISHED,
        model_name=encoder.name,
    )
    if evaluation.age_months is not None and evaluation.age_months < 0:
        eligible = eligible.filter(activity__age_range=AgeRange.PRENATAL)
    else:
        eligible = eligible.exclude(activity__age_range=AgeRange.PRENATAL)
    rows = list(eligible.select_related("activity"))
    if not rows:
        return RetrievalResult(query=query, evaluation=evaluation, candidates=[])

    matrix = np.stack([embeddings.from_bytes(row.vector) for row in rows])
    query_vector = encoder.encode([query])[0]
    # Vectors are L2-normalised, so the dot product is the cosine similarity.
    # Clipped because float rounding can land a hair outside [-1, 1].
    similarities = np.clip(matrix @ query_vector, -1.0, 1.0)
    order = np.argsort(-similarities, kind="stable")[:limit]
    candidates = [
        Candidate(activity=rows[i].activity, similarity=float(similarities[i]))
        for i in order
    ]
    return RetrievalResult(query=query, evaluation=evaluation, candidates=candidates)
