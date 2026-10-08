from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from profiles.permissions import IsCaregiver

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
