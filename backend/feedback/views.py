from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from profiles.permissions import IsCaregiver
from recommendations.models import Recommendation

from .models import CompletedActivity


def own_recommendation(user, recommendation_id):
    """The caregiver's own recommendation; anyone else's is a 404."""
    return get_object_or_404(
        Recommendation.objects.select_related("activity"),
        pk=recommendation_id,
        child__caregiver=user,
    )


def completion_json(completion):
    if completion is None:
        return None
    return {
        "status": completion.status,
        "completion_date": completion.completion_date.isoformat(),
    }


class CompletionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=CompletedActivity.Status.choices,
        default=CompletedActivity.Status.COMPLETED,
    )


class RecommendationCompletionView(APIView):
    """Mark a recommended activity as done, fully or partly (FR-14).

    PUT records or changes it (201 the first time, then 200) and DELETE
    undoes it. Completed activities are left out of the child's next batch
    (generation.py); partly completed ones stay eligible.
    """

    permission_classes = [IsCaregiver]

    def put(self, request, recommendation_id):
        recommendation = own_recommendation(request.user, recommendation_id)
        serializer = CompletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        completion, created = CompletedActivity.objects.update_or_create(
            recommendation=recommendation,
            defaults={
                "status": serializer.validated_data["status"],
                "completion_date": timezone.localdate(),
            },
        )
        return Response(
            completion_json(completion),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, recommendation_id):
        recommendation = own_recommendation(request.user, recommendation_id)
        CompletedActivity.objects.filter(recommendation=recommendation).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
