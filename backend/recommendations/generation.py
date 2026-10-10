"""Generate and store a child's ranked recommendations (#52, Sprint 6 entry).

The ranking is the one evaluated at tag sprint5-eval-v1: rank() over every
eligible Published, embedded activity at settings.RANKING_ALPHA. The top N
are stored as one batch of Recommendation rows.

- Completed activities (a CompletedActivity with status Completed on any of
  the child's earlier recommendations) are removed *after* ranking, so the
  remaining order is exactly the evaluated order. This filter is outside the
  evaluated pipeline: the Sprint 5 evaluation never excluded anything.
  Partially completed activities stay eligible.
- Each row stores its caregiver-readable explanation (explanations.py) and
  the EXPLANATION_VERSION that produced it.
- Existing recommendations are never edited or deleted. A new request whose
  activities, order, alpha, profile fingerprint and ranking version all
  match the newest batch, and whose explanations (version and text) match
  too, returns that batch instead of storing a copy. The
  fingerprint covers the rule engine output, the retrieval query (and so
  the child's interests), the age bracket and the milestone catalogue.
- The child row is locked for the whole generation, so simultaneous
  requests for the same child can't both store a batch.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from feedback.models import CompletedActivity
from profiles.models import ChildProfile

from . import embeddings, provenance
from .explanations import EXPLANATION_VERSION, explain
from .models import Recommendation
from .ranking import child_bracket, rank

RECOMMENDATIONS_PER_BATCH = 5
SHORT_DESCRIPTION_LENGTH = 160

# ranking_version() at tag sprint5-eval-v1: the rule weights, ranking
# settings, alpha (0.7), embedding model and batch size that were evaluated.
# A test fails if the current settings drift from it, so any change to the
# evaluated configuration has to be made (and re-evaluated) deliberately.
SPRINT5_EVAL_V1_RANKING_VERSION = (
    "da4d8bcfc4b96aa8275ddf6d450433ff66df8c6786952221e19cad800840de31"
)


def _sha256(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def ranking_version():
    """Hash of everything besides the child that decides the ranking."""
    return _sha256(
        {
            "rule_weights": provenance.rule_weights(),
            "ranking": provenance.ranking_settings(),
            "alpha": float(settings.RANKING_ALPHA),
            "embedding_model": embeddings.MODEL_NAME,
            "per_batch": RECOMMENDATIONS_PER_BATCH,
        }
    )


def profile_fingerprint(evaluation, query):
    """Hash of the rule engine output, the retrieval query, the age bracket
    and the milestone catalogue.

    The query carries what the rules don't, such as non-sensory interests, so
    a change there can't leave a stale batch (or, later, a stale explanation).
    """
    bracket = child_bracket(evaluation.age_months)
    return _sha256(
        {
            "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "scores": evaluation.scores,
            "firings": [
                [f.rule.name, f.adjustments, f.reason] for f in evaluation.firings
            ],
            "age_bracket": "prenatal" if bracket is None else bracket,
            "catalogue": provenance.catalogue_version()["sha256"],
        }
    )


def short_description(text, limit=SHORT_DESCRIPTION_LENGTH):
    """The description cut at a word boundary to at most `limit` characters."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:.")
    return cut + "…"


def completed_activity_ids(child):
    return set(
        CompletedActivity.objects.filter(
            recommendation__child=child,
            status=CompletedActivity.Status.COMPLETED,
        ).values_list("recommendation__activity_id", flat=True)
    )


def latest_batch(child):
    """The newest batch's rows in position order (empty if none)."""
    newest = (
        Recommendation.objects.filter(child=child)
        .order_by("-date_generated", "-id")
        .values_list("batch", flat=True)
        .first()
    )
    if newest is None:
        return []
    return list(
        Recommendation.objects.filter(child=child, batch=newest)
        .select_related("activity")
        .order_by("position")
    )


@dataclass(frozen=True)
class GenerationResult:
    recommendations: list
    created: bool


def generate(child_id, caregiver):
    """Rank, then store a new batch or return the identical newest one.

    Raises ChildProfile.DoesNotExist if the child isn't the caregiver's.
    """
    with transaction.atomic():
        child = ChildProfile.objects.select_for_update().get(
            pk=child_id, caregiver=caregiver
        )
        result = rank(child)
        completed = completed_activity_ids(child)
        top = [r for r in result.ranked if r.activity.pk not in completed][
            :RECOMMENDATIONS_PER_BATCH
        ]
        alpha = result.alpha
        fingerprint = profile_fingerprint(result.evaluation, result.query)
        version = ranking_version()
        texts = [explain(child, result.evaluation, r).text for r in top]

        newest = latest_batch(child)
        if newest and (
            [r.activity_id for r in newest] == [r.activity.pk for r in top]
            and all(
                r.alpha == alpha
                and r.profile_fingerprint == fingerprint
                and r.ranking_version == version
                and r.explanation_version == EXPLANATION_VERSION
                for r in newest
            )
            # The text too: a newly approved plain_aim changes it without
            # changing the version.
            and [r.explanation for r in newest] == texts
        ):
            return GenerationResult(recommendations=newest, created=False)
        if not top:
            return GenerationResult(recommendations=[], created=False)

        batch, now = uuid.uuid4(), timezone.now()
        rows = Recommendation.objects.bulk_create(
            [
                Recommendation(
                    child=child,
                    activity=r.activity,
                    batch=batch,
                    position=position,
                    similarity_score=r.similarity,
                    ranking_score=r.score,
                    rule_priority=r.priority,
                    age_weight=r.age_weight,
                    alpha=alpha,
                    profile_fingerprint=fingerprint,
                    ranking_version=version,
                    explanation=text,
                    explanation_version=EXPLANATION_VERSION,
                    date_generated=now,
                )
                for position, (r, text) in enumerate(zip(top, texts), start=1)
            ]
        )
        return GenerationResult(recommendations=rows, created=True)
