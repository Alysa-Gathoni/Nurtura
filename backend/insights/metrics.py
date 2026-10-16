"""Figures for the admin dashboard (#116).

Aggregates only: nothing here returns a child's name or a caregiver's email,
the same rule as the feedback review (#96). Read-only; nothing that affects
recommendations is touched.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q
from django.utils import timezone
from django.utils.text import Truncator

from activities.choices import ContentStatus, Domain
from activities.models import DevelopmentalActivity
from feedback.models import CompletedActivity, Feedback
from profiles.models import ChildProfile, DevelopmentalMilestone
from recommendations.models import Recommendation

ACTIVE_DAYS = 7

# An activity whose average rating is at or below this needs a look.
NEEDS_ATTENTION_AT = 2.5

TOP_N = 5


def _share(part, whole):
    """Whole-number percentage, 0 when there's nothing to divide by."""
    return round(100 * part / whole) if whole else 0


def _bars(rows, value="count"):
    """Add each row's width as a share of the largest value (for bar marks)."""
    top = max((row[value] for row in rows), default=0)
    for row in rows:
        row["width"] = _share(row[value], top)
    return rows


def active_caregivers(since):
    """Caregivers who generated ideas, recorded a milestone, or marked an
    activity done or rated it since `since`."""
    ids = set(
        Recommendation.objects.filter(date_generated__gte=since).values_list(
            "child__caregiver", flat=True
        )
    )
    ids |= set(
        DevelopmentalMilestone.objects.filter(created_at__gte=since).values_list(
            "child__caregiver", flat=True
        )
    )
    ids |= set(
        CompletedActivity.objects.filter(
            completion_date__gte=timezone.localdate(since)
        ).values_list("recommendation__child__caregiver", flat=True)
    )
    ids |= set(
        Feedback.objects.filter(date_submitted__gte=since).values_list(
            "recommendation__child__caregiver", flat=True
        )
    )
    return len(ids)


def _rated_activities():
    return DevelopmentalActivity.objects.annotate(
        ratings=Count("recommendations__feedback"),
        average=Avg("recommendations__feedback__rating"),
    ).filter(ratings__gt=0)


def _activity_row(activity):
    return {
        "pk": activity.pk,
        "activity_id": activity.activity_id,
        "name": activity.activity_name,
        "average": round(activity.average, 1),
        "ratings": activity.ratings,
    }


def dashboard(now=None):
    now = now or timezone.now()
    since = now - timedelta(days=ACTIVE_DAYS)
    today = timezone.localdate(now)
    User = get_user_model()

    children = ChildProfile.objects.all()
    child_count = children.count()
    expecting = children.filter(date_of_birth__gt=today).count()

    recommended = Recommendation.objects.count()
    completions = CompletedActivity.objects.aggregate(
        done=Count("id", filter=Q(status=CompletedActivity.Status.COMPLETED)),
        partly=Count(
            "id", filter=Q(status=CompletedActivity.Status.PARTIALLY_COMPLETED)
        ),
    )
    tried = completions["done"] + completions["partly"]

    ratings = Feedback.objects.aggregate(count=Count("id"), average=Avg("rating"))
    by_rating = dict(Feedback.objects.values_list("rating").annotate(n=Count("id")))

    published = dict(
        DevelopmentalActivity.objects.filter(content_status=ContentStatus.PUBLISHED)
        .values_list("developmental_domain")
        .annotate(n=Count("id"))
    )
    pipeline = dict(
        DevelopmentalActivity.objects.values_list("content_status").annotate(
            n=Count("id")
        )
    )

    milestone_counts = dict(
        DevelopmentalMilestone.objects.values_list("status").annotate(n=Count("id"))
    )
    milestone_total = sum(milestone_counts.values())

    rated = _rated_activities()
    recent = Feedback.objects.select_related("recommendation__activity").order_by(
        "-date_submitted", "-id"
    )[:TOP_N]

    return {
        "active_days": ACTIVE_DAYS,
        "caregivers": User.objects.filter(role=User.Role.CAREGIVER).count(),
        "active_caregivers": active_caregivers(since),
        "children": child_count,
        "children_born": child_count - expecting,
        "children_expecting": expecting,
        "batches": Recommendation.objects.values("batch").distinct().count(),
        "batches_recent": Recommendation.objects.filter(date_generated__gte=since)
        .values("batch")
        .distinct()
        .count(),
        "recommended": recommended,
        "done": completions["done"],
        "partly": completions["partly"],
        "tried_share": _share(tried, recommended),
        "ratings_count": ratings["count"],
        "ratings_average": (
            round(ratings["average"], 1) if ratings["average"] is not None else None
        ),
        "rating_bars": _bars(
            [{"rating": r, "count": by_rating.get(r, 0)} for r in range(1, 6)]
        ),
        "library_bars": _bars(
            [
                {"label": label, "count": published.get(value, 0)}
                for value, label in Domain.choices
            ]
        ),
        "library_total": sum(published.values()),
        "pipeline": [
            {"label": label, "count": pipeline.get(value, 0)}
            for value, label in ContentStatus.choices
        ],
        "milestones_total": milestone_total,
        "milestone_parts": [
            {
                "key": value,
                "label": label,
                "count": milestone_counts.get(value, 0),
                "share": _share(milestone_counts.get(value, 0), milestone_total),
            }
            for value, label in DevelopmentalMilestone.Status.choices
        ],
        "top_rated": [
            _activity_row(a)
            for a in rated.order_by("-average", "-ratings", "activity_id")[:TOP_N]
        ],
        "needs_attention": [
            _activity_row(a)
            for a in rated.filter(average__lte=NEEDS_ATTENTION_AT).order_by(
                "average", "-ratings", "activity_id"
            )[:TOP_N]
        ],
        "needs_attention_at": NEEDS_ATTENTION_AT,
        "recent_feedback": [
            {
                "activity_pk": f.recommendation.activity.pk,
                "activity_id": f.recommendation.activity.activity_id,
                "name": f.recommendation.activity.activity_name,
                "rating": f.rating,
                "comment": Truncator(f.comment).chars(90),
                "date": f.date_submitted,
            }
            for f in recent
        ],
    }
