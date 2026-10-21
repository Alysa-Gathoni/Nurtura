"""Operations overview for the app's admin dashboard (#120, #122).

Builds on metrics.dashboard() with what an administrator needs to keep
Nurtura running: use over time, system health, work waiting, library
coverage, recent events and the most recommended activities. Aggregates
only: no child names or caregiver emails (#96). Read-only.
"""

from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from activities.choices import AgeRange, ContentStatus, Domain
from activities.models import DevelopmentalActivity
from feedback.models import CompletedActivity, Feedback
from profiles.models import (
    DevelopmentalMilestone,
    LoginChallenge,
    ReferenceMilestone,
)
from profiles.two_factor import MAX_ATTEMPTS
from recommendations import embeddings
from recommendations.models import ActivityEmbedding, Recommendation

from .metrics import dashboard

# Period tabs on the trend chart, in days.
RANGES = (7, 30, 90)
DEFAULT_RANGE = 30
SPARK_DAYS = 14
EVENTS_N = 8
TABLE_N = 8


def parse_range(value):
    try:
        days = int(value)
    except (TypeError, ValueError):
        return DEFAULT_RANGE
    return days if days in RANGES else DEFAULT_RANGE


def _days(now, count):
    """The `count` local dates ending today, oldest first."""
    today = timezone.localdate(now)
    return [today - timedelta(days=count - 1 - i) for i in range(count)]


def _per_day(queryset, field, since, distinct=None):
    """{date: count} of rows whose `field` falls on each day since `since`."""
    rows = (
        queryset.filter(**{f"{field}__gte": since})
        .annotate(day=TruncDate(field))
        .values("day")
        .annotate(n=Count(distinct or "id", distinct=bool(distinct)))
    )
    return {row["day"]: row["n"] for row in rows}


def daily_series(now, days):
    """Per-day counts for the trend chart and the sparklines."""
    dates = _days(now, days)
    since = timezone.make_aware(
        timezone.datetime.combine(dates[0], timezone.datetime.min.time())
    )
    User = get_user_model()
    raw = {
        "ideas": _per_day(Recommendation.objects, "date_generated", since, "batch"),
        "milestones": _per_day(DevelopmentalMilestone.objects, "created_at", since),
        "feedback": _per_day(Feedback.objects, "date_submitted", since),
        "signups": _per_day(
            User.objects.filter(role=User.Role.CAREGIVER), "date_joined", since
        ),
    }
    return dates, {
        key: [counts.get(d, 0) for d in dates] for key, counts in raw.items()
    }


def stale_embeddings():
    """Published activities without an embedding of their current text."""
    stale = 0
    for activity in DevelopmentalActivity.objects.published().select_related(
        "embedding"
    ):
        current = getattr(activity, "embedding", None)
        digest = embeddings.text_hash(
            embeddings.MODEL_NAME, embeddings.activity_text(activity)
        )
        if current is None or current.text_hash != digest:
            stale += 1
    return stale


def health_checks(now):
    """Each check: status (good, warning or alert), title and detail."""
    checks = []
    model_path = Path(settings.SBERT_MODEL_PATH)
    if model_path.exists():
        checks.append(
            ("good", "AI model ready", f"{embeddings.MODEL_NAME} is installed")
        )
    else:
        checks.append(
            ("alert", "AI model missing", "Run python setup_sbert.py on the server")
        )

    stale = stale_embeddings()
    orphans = ActivityEmbedding.objects.exclude(
        activity__content_status=ContentStatus.PUBLISHED
    ).count()
    if stale or orphans:
        checks.append(
            (
                "warning",
                "Search index out of date",
                f"{stale} Published activit{'y' if stale == 1 else 'ies'} not "
                "searchable yet; run python manage.py embed_activities",
            )
        )
    else:
        checks.append(
            (
                "good",
                "Search index up to date",
                "Every Published activity is searchable",
            )
        )

    backend = settings.MAILERS["default"]["BACKEND"]
    if "smtp" in backend:
        checks.append(("good", "Sign-in emails", "Codes are sent by email"))
    else:
        checks.append(
            (
                "warning",
                "Sign-in emails not sent",
                "Codes are printed in the server console (development)",
            )
        )

    since = now - timedelta(days=7)
    locked = LoginChallenge.objects.filter(
        created_at__gte=since, attempts__gte=MAX_ATTEMPTS, used_at__isnull=True
    ).count()
    if locked:
        checks.append(
            (
                "warning",
                "Sign-in codes locked",
                f"{locked} code{'s' if locked != 1 else ''} locked after "
                f"{MAX_ATTEMPTS} wrong tries in the last 7 days",
            )
        )
    else:
        checks.append(
            ("good", "Sign-in", "No codes locked by wrong tries in the last 7 days")
        )

    if settings.DEBUG:
        checks.append(
            ("warning", "Debug mode on", "Fine for development; turn off when hosted")
        )
    return [{"status": s, "title": t, "detail": d} for s, t, d in checks]


def work_waiting():
    review = dict(
        DevelopmentalActivity.objects.exclude(content_status=ContentStatus.PUBLISHED)
        .values_list("content_status")
        .annotate(n=Count("id"))
    )
    total = ReferenceMilestone.objects.count()
    unverified = ReferenceMilestone.objects.filter(verified=False).count()
    return {
        "drafts": review.get(ContentStatus.DRAFT, 0),
        "under_review": review.get(ContentStatus.UNDER_REVIEW, 0),
        "unverified": unverified,
        "milestones_total": total,
        "verified_share": round(100 * (total - unverified) / total) if total else 0,
    }


POSTNATAL_AGES = [value for value, _ in AgeRange.choices if value != AgeRange.PRENATAL]


def coverage_grid():
    """Published activities by area (rows) and age (columns)."""
    counts = {
        (row["developmental_domain"], row["age_range"]): row["n"]
        for row in DevelopmentalActivity.objects.published()
        .values("developmental_domain", "age_range")
        .annotate(n=Count("id"))
    }
    top = max(counts.values(), default=0)
    rows, gaps = [], 0
    for domain, label in Domain.choices:
        cells = []
        for age in POSTNATAL_AGES:
            n = counts.get((domain, age), 0)
            gaps += n == 0
            level = 0 if n == 0 else min(4, 1 + (3 * n) // max(top, 1))
            cells.append({"age": age, "count": n, "level": level})
        rows.append({"label": label, "cells": cells})
    return {
        # Column headers in months ("0–3"), stated once under the grid.
        "ages": [
            label.replace(" months", "").replace("-", "–")
            for value, label in AgeRange.choices
            if value != AgeRange.PRENATAL
        ],
        "rows": rows,
        "gaps": gaps,
        "prenatal": DevelopmentalActivity.objects.published()
        .filter(age_range=AgeRange.PRENATAL)
        .count(),
    }


def recent_events(limit=EVENTS_N):
    """The newest things that happened, without naming any family."""
    User = get_user_model()
    events = []
    for user in User.objects.filter(role=User.Role.CAREGIVER).order_by("-date_joined")[
        :limit
    ]:
        events.append((user.date_joined, "signup", "A caregiver joined", ""))
    for row in (
        Recommendation.objects.values("batch", "date_generated")
        .order_by("-date_generated")
        .distinct()[: limit * 5]
    ):
        events.append((row["date_generated"], "ideas", "Ideas generated", ""))
    for m in DevelopmentalMilestone.objects.order_by("-created_at")[:limit]:
        events.append(
            (
                m.created_at,
                "milestone",
                "Milestone recorded",
                f"{m.domain} · {m.get_status_display()}",
            )
        )
    for c in CompletedActivity.objects.select_related(
        "recommendation__activity"
    ).order_by("-id")[:limit]:
        when = timezone.make_aware(
            timezone.datetime.combine(c.completion_date, timezone.datetime.min.time())
        )
        events.append(
            (
                when,
                "done",
                "Marked " + c.get_status_display().lower(),
                c.recommendation.activity.activity_name,
            )
        )
    for f in Feedback.objects.select_related("recommendation__activity").order_by(
        "-date_submitted"
    )[:limit]:
        events.append(
            (
                f.date_submitted,
                "feedback",
                f"Rated {f.rating}★",
                f.recommendation.activity.activity_name,
            )
        )
    # Admin changes to content only: other models' labels can name a child.
    content_types = ContentType.objects.get_for_models(
        DevelopmentalActivity, ReferenceMilestone
    ).values()
    # One row per admin, action and minute, so a bulk edit is one event.
    groups = {}
    for entry in LogEntry.objects.filter(content_type__in=content_types).order_by(
        "-action_time"
    )[: limit * 10]:
        key = (
            entry.user_id,
            entry.action_flag,
            entry.action_time.replace(second=0, microsecond=0),
        )
        groups.setdefault(key, []).append(entry)
    for entries in groups.values():
        first = entries[0]
        action = {1: "Added", 2: "Changed", 3: "Deleted"}.get(first.action_flag, "")
        detail = (
            first.object_repr
            if len(entries) == 1
            else f"{len(entries)} items, including {first.object_repr}"
        )
        events.append((first.action_time, "admin", f"{action} by {first.user}", detail))
    events.sort(key=lambda e: e[0], reverse=True)
    seen, unique = set(), []
    for when, kind, title, detail in events:
        key = (kind, when.replace(microsecond=0), title, detail)
        if key in seen:
            continue
        seen.add(key)
        unique.append({"when": when, "kind": kind, "title": title, "detail": detail})
    return unique[:limit]


def most_recommended(limit=TABLE_N):
    rows = (
        DevelopmentalActivity.objects.annotate(
            times=Count("recommendations", distinct=True),
            done=Count(
                "recommendations__completion",
                filter=Q(
                    recommendations__completion__status=CompletedActivity.Status.COMPLETED
                ),
                distinct=True,
            ),
            ratings=Count("recommendations__feedback", distinct=True),
            average=Avg("recommendations__feedback__rating"),
        )
        .filter(times__gt=0)
        .order_by("-times", "activity_id")[:limit]
    )
    return [
        {
            "pk": a.pk,
            "activity_id": a.activity_id,
            "name": a.activity_name,
            "domain": a.developmental_domain,
            "times": a.times,
            "done_share": round(100 * a.done / a.times) if a.times else 0,
            "average": round(a.average, 1) if a.average is not None else None,
            "status": a.get_content_status_display(),
            "status_key": a.content_status,
        }
        for a in rows
    ]


def api_overview(now=None, days=DEFAULT_RANGE):
    """Everything the app's admin dashboard shows, as plain JSON data.

    The app draws its own charts, so series are raw daily counts.
    """
    now = now or timezone.now()
    d = dashboard(now)
    dates, series = daily_series(now, days)
    spark_dates, spark = daily_series(now, SPARK_DAYS)
    not_marked = max(d["recommended"] - d["done"] - d["partly"], 0)
    return {
        "range": days,
        "ranges": list(RANGES),
        "people": {
            "caregivers": d["caregivers"],
            "active_caregivers": d["active_caregivers"],
            "active_days": d["active_days"],
            "children": d["children"],
            "children_born": d["children_born"],
            "children_expecting": d["children_expecting"],
        },
        "trend": {
            "dates": [day.isoformat() for day in dates],
            "series": {key: series[key] for key in ("ideas", "milestones", "feedback")},
            "totals": {key: sum(values) for key, values in series.items()},
        },
        "spark": {
            "days": SPARK_DAYS,
            "series": spark,
            "totals": {key: sum(values) for key, values in spark.items()},
        },
        "outcomes": {
            "recommended": d["recommended"],
            "done": d["done"],
            "partly": d["partly"],
            "not_marked": not_marked,
            "tried_share": d["tried_share"],
        },
        "ratings": {
            "count": d["ratings_count"],
            "average": d["ratings_average"],
            "by_star": [b["count"] for b in d["rating_bars"]],
        },
        "milestones": {
            "total": d["milestones_total"],
            "by_status": [
                {"status": m["key"], "label": m["label"], "count": m["count"]}
                for m in d["milestone_parts"]
            ],
        },
        "needs_attention": d["needs_attention"],
        "needs_attention_at": d["needs_attention_at"],
        "health": health_checks(now),
        "waiting": work_waiting(),
        "coverage": coverage_grid(),
        "events": [{**e, "when": e["when"].isoformat()} for e in recent_events()],
        "most_recommended": most_recommended(),
    }
