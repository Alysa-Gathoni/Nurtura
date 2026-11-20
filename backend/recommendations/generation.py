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
- Pinned activities (#177), chosen by the caregiver from the options after
  feedback, come first and are carried into later batches until they are
  completed, at most MAX_PINNED of them. Their explanation starts with why
  they were chosen. The rest of the batch is the evaluated order.
- The child's feedback adjusts the order after ranking (personalisation.py,
  #179): activities similar to ones that went well move up, ones similar to
  ones that didn't work move down, and an activity that didn't work isn't
  suggested again. A child with no feedback gets the evaluated order.
- Ideas come as a weekly plan (#244), Monday to Sunday (#253), the same
  weeks as the app's week streak. A new plan starts on the Monday of the
  current week; one made on a Sunday runs to the following Sunday, so it
  isn't a one-day plan. Batches stored during a plan (a new milestone, an
  edited profile, a pinned option) keep its start date; the first request
  after it ends starts a new plan. Plans started mid-week before #253 keep
  their PLAN_DAYS days.
- Ideas rotate between weeks (#246). Of last week's ideas that weren't tried
  (done or partly done), only the KEEP_UNTRIED best-ranked come back; the
  rest of the week is ideas that weren't in last week's plan, in ranked
  order, topped up with more of last week's if there aren't enough. Pinned
  ideas are kept regardless. The ranking itself is unchanged, so the first
  week is the evaluated top 5.
"""

import datetime
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
from .personalisation import personalise
from .ranking import child_bracket, rank

RECOMMENDATIONS_PER_BATCH = 5
MAX_PINNED = 2
SHORT_DESCRIPTION_LENGTH = 160
PLAN_DAYS = 7
# Rotation (#246): how many of last week's untried ideas a new week keeps.
KEEP_UNTRIED = 2

# ranking_version() at tag sprint5-eval-v1: the rule weights, ranking
# settings, alpha (0.7), embedding model and batch size that were evaluated.
# A test fails if the current settings drift from it, so any change to the
# evaluated configuration has to be made (and re-evaluated) deliberately.
SPRINT5_EVAL_V1_RANKING_VERSION = (
    "da4d8bcfc4b96aa8275ddf6d450433ff66df8c6786952221e19cad800840de31"
)

# ranking_version() since #250: the same configuration with retrieval mixing
# SBERT and TF-IDF at beta = 0.25 (docs/tfidf_comparison.md). With
# RETRIEVAL_BETA = 1 the version is SPRINT5_EVAL_V1_RANKING_VERSION again.
TFIDF_MIX_RANKING_VERSION = (
    "1bebb5441fd039526e63ec57f62d5d513a017a4bd839773fdfe00ff8b5d928c4"
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


def _plan_start_of(row):
    """A stored row's plan start (older rows: the day it was generated)."""
    return row.plan_start or timezone.localtime(row.date_generated).date()


def plan_for(recommendations, today=None):
    """The weekly plan of a batch: its first and last day, and whether it
    has ended. None for an empty batch."""
    if not recommendations:
        return None
    today = today or timezone.localdate()
    start = _plan_start_of(recommendations[0])
    ends = plan_end(start)
    return {"starts": start, "ends": ends, "ended": today > ends}


SUNDAY = 6  # date.weekday()


def new_plan_start(today):
    """Where a plan made today starts: the Monday of this week, or today
    if it's a Sunday (that plan then runs to the following Sunday)."""
    if today.weekday() == SUNDAY:
        return today
    return today - datetime.timedelta(days=today.weekday())


def plan_end(start):
    """A plan's last day: the following Sunday for a plan that starts on a
    Sunday, else PLAN_DAYS days on (Monday to Sunday; plans started mid-week
    before #253 keep their seven days)."""
    if start.weekday() == SUNDAY:
        return start + datetime.timedelta(days=PLAN_DAYS)
    return start + datetime.timedelta(days=PLAN_DAYS - 1)


def current_plan_start(newest, today):
    """The newest batch's plan start while that plan runs, else where a new
    plan made today starts."""
    plan = plan_for(newest, today)
    if plan is None or plan["ended"]:
        return new_plan_start(today)
    return plan["starts"]


@dataclass(frozen=True)
class GenerationResult:
    recommendations: list
    created: bool


def _pins(newest, completed, pin):
    """[(activity pk, note)] to pin: the new one first, then carried ones."""
    pins = [
        (r.activity_id, r.pin_note)
        for r in newest
        if r.pinned and r.activity_id not in completed
    ]
    if pin is not None:
        pins = [pin] + [p for p in pins if p[0] != pin[0]]
    return pins[:MAX_PINNED]


def tried_activity_ids(child):
    """Activities the child has done or partly done, on any batch."""
    return set(
        CompletedActivity.objects.filter(recommendation__child=child).values_list(
            "recommendation__activity_id", flat=True
        )
    )


def previous_plan_ids(child, plan_start):
    """Activities in the newest batch of the plan before plan_start."""
    newest = (
        Recommendation.objects.filter(child=child, plan_start__lt=plan_start)
        .order_by("-date_generated", "-id")
        .values_list("batch", flat=True)
        .first()
    )
    if newest is None:
        return set()
    return set(
        Recommendation.objects.filter(child=child, batch=newest).values_list(
            "activity_id", flat=True
        )
    )


def rotate(candidates, rested, count, keep=KEEP_UNTRIED):
    """Choose `count` of the ranked `candidates` for a new week (#246).

    `rested` are last week's ideas that weren't tried: the `keep` best of
    them stay, and the rest of the week is ideas that weren't in last week's
    plan. If there aren't enough of those, more rested ideas fill the gap.
    The chosen ideas keep their ranked order.
    """
    rested_ranked = [c for c in candidates if c.activity.pk in rested]
    fresh = [c for c in candidates if c.activity.pk not in rested]
    held = rested_ranked[:keep]
    chosen = held + fresh[: count - len(held)]
    if len(chosen) < count:
        chosen += rested_ranked[keep:][: count - len(chosen)]
    order = {c.activity.pk: i for i, c in enumerate(candidates)}
    return sorted(chosen, key=lambda c: order[c.activity.pk])


def generate(child_id, caregiver, pin=None):
    """Rank, then store a new batch or return the identical newest one.

    pin=(activity pk, note) pins that activity first (#177). Raises
    ChildProfile.DoesNotExist if the child isn't the caregiver's.
    """
    with transaction.atomic():
        child = ChildProfile.objects.select_for_update().get(
            pk=child_id, caregiver=caregiver
        )
        result = rank(child)
        personal = personalise(child, result.ranked)
        completed = completed_activity_ids(child)
        newest = latest_batch(child)
        ranked = {r.activity.pk: r for r in personal.ranked}
        notes = {
            pk: note
            for pk, note in _pins(newest, completed, pin)
            # still eligible, and not since marked as not working
            if pk in ranked and pk not in personal.excluded
        }
        skip = completed | personal.excluded | set(notes)
        candidates = [r for r in personal.ranked if r.activity.pk not in skip]
        # Rotation (#246): from the second week on, last week's untried
        # ideas mostly rest. Decided by the previous plan, so a mid-week
        # refresh keeps the week's mix.
        plan_start = current_plan_start(newest, timezone.localdate())
        rested = previous_plan_ids(child, plan_start) - tried_activity_ids(child)
        top = [ranked[pk] for pk in notes] + rotate(
            candidates, rested - set(notes), RECOMMENDATIONS_PER_BATCH - len(notes)
        )
        alpha = result.alpha
        fingerprint = profile_fingerprint(result.evaluation, result.query)
        version = ranking_version()
        liked_notes = personal.notes_for(
            [r.activity.pk for r in top if r.activity.pk not in notes]
        )
        texts = [
            " ".join(
                filter(
                    None,
                    [
                        notes.get(r.activity.pk),
                        explain(child, result.evaluation, r).text,
                        liked_notes.get(r.activity.pk),
                    ],
                )
            )
            for r in top
        ]

        if newest and (
            # the same week: a new week stores a new plan, even if identical
            _plan_start_of(newest[0]) == plan_start
            and [r.activity_id for r in newest] == [r.activity.pk for r in top]
            and [r.pinned for r in newest] == [r.activity.pk in notes for r in top]
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
                    pinned=r.activity.pk in notes,
                    pin_note=notes.get(r.activity.pk, ""),
                    date_generated=now,
                    plan_start=plan_start,
                )
                for position, (r, text) in enumerate(zip(top, texts), start=1)
            ]
        )
        return GenerationResult(recommendations=rows, created=True)
