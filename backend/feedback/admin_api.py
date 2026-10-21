"""Feedback review for administrators in the app (#122, FR-16).

Each rating and comment is shown against the activity it concerns, with
whether the activity was marked done. No child or caregiver details, the
same rule as the Django feedback review (#96).
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from profiles.permissions import IsAdministrator

from .models import Feedback

DEFAULT_LIMIT, MAX_LIMIT = 50, 200


def _int(value, default, low, high):
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


class AdminFeedbackListView(APIView):
    """GET feedback, newest first (?rating=, ?domain=, ?activity=,
    ?limit=, ?offset=)."""

    permission_classes = [IsAdministrator]

    def get(self, request):
        params = request.query_params
        queryset = Feedback.objects.select_related(
            "recommendation__activity", "recommendation__completion"
        ).order_by("-date_submitted", "-id")
        if rating := params.get("rating"):
            queryset = queryset.filter(rating=_int(rating, 0, 0, 5))
        if domain := params.get("domain"):
            queryset = queryset.filter(
                recommendation__activity__developmental_domain=domain
            )
        if activity := params.get("activity"):
            queryset = queryset.filter(
                recommendation__activity__pk=_int(activity, 0, 0, 10**9)
            )
        limit = _int(params.get("limit"), DEFAULT_LIMIT, 1, MAX_LIMIT)
        offset = _int(params.get("offset"), 0, 0, 10**9)
        total = queryset.count()
        return Response(
            {
                "count": total,
                "results": [_row(f) for f in queryset[offset : offset + limit]],
            }
        )


def _row(feedback):
    activity = feedback.recommendation.activity
    completion = getattr(feedback.recommendation, "completion", None)
    return {
        "id": feedback.pk,
        "rating": feedback.rating,
        "comment": feedback.comment,
        "date_submitted": feedback.date_submitted.isoformat(),
        "completion": completion.status if completion else None,
        "activity": {
            "id": activity.pk,
            "activity_id": activity.activity_id,
            "name": activity.activity_name,
            "domain": activity.developmental_domain,
            "age_range": activity.age_range,
        },
    }
