from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from profiles.models import ChildProfile
from profiles.permissions import IsCaregiver

from . import generation
from .generation import short_description
from .retrieval import DEFAULT_LIMIT, MAX_LIMIT, retrieve


class ChildCandidatesView(APIView):
    """Activities semantically closest to a child's developmental profile.

    These are retrieval candidates (FR-06), not final recommendations: the
    weighted ranking and explanations come in Sprints 5-6.
    """

    permission_classes = [IsCaregiver]

    def get(self, request, child_id):
        child = get_object_or_404(request.user.children, pk=child_id)
        try:
            limit = int(request.query_params.get("limit", DEFAULT_LIMIT))
        except ValueError:
            raise ValidationError({"limit": "Must be a whole number."})
        if not 1 <= limit <= MAX_LIMIT:
            raise ValidationError({"limit": f"Must be between 1 and {MAX_LIMIT}."})

        result = retrieve(child, limit=limit)
        evaluation = result.evaluation.to_dict()
        return Response(
            {
                "query": result.query,
                "profile": {
                    "scores": evaluation["scores"],
                    "ranked_domains": evaluation["ranked_domains"],
                },
                "candidates": [
                    {
                        "activity_id": c.activity.activity_id,
                        "activity_name": c.activity.activity_name,
                        "developmental_domain": c.activity.developmental_domain,
                        "age_range": c.activity.age_range,
                        "similarity": round(c.similarity, 4),
                    }
                    for c in result.candidates
                ],
            }
        )


def _card(recommendation):
    activity = recommendation.activity
    return {
        "id": recommendation.pk,
        "batch": str(recommendation.batch),
        "position": recommendation.position,
        "generated_at": recommendation.date_generated.isoformat(),
        "activity_id": activity.activity_id,
        "activity_name": activity.activity_name,
        "developmental_domain": activity.developmental_domain,
        "age_range": activity.age_range,
        "short_description": short_description(activity.description),
        "explanation": recommendation.explanation,
    }


def _payload(recommendations):
    first = recommendations[0] if recommendations else None
    return {
        "batch": str(first.batch) if first else None,
        "generated_at": first.date_generated.isoformat() if first else None,
        "recommendations": [_card(r) for r in recommendations],
    }


class ChildRecommendationsView(APIView):
    """The child's ranked recommendations (#52).

    GET returns the newest stored batch and never generates. POST ranks the
    child's eligible activities (the ranking evaluated at sprint5-eval-v1)
    and stores the top 5 as a new batch: 201 when a batch is stored, 200 when
    the newest batch already matches. Only the child's own caregiver may use
    either; other caregivers' children are 404 and administrators 403.
    """

    permission_classes = [IsCaregiver]

    def get(self, request, child_id):
        child = get_object_or_404(request.user.children, pk=child_id)
        return Response(_payload(generation.latest_batch(child)))

    def post(self, request, child_id):
        try:
            result = generation.generate(child_id, request.user)
        except ChildProfile.DoesNotExist:
            raise Http404
        return Response(
            _payload(result.recommendations),
            status=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK,
        )
