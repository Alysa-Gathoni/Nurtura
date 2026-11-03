from django.db.models import prefetch_related_objects
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from feedback.manager import latest as latest_feedback
from feedback.views import completion_json, feedback_json, own_recommendation
from profiles.models import ChildProfile
from profiles.permissions import IsCaregiver
from profiles.rules.referral import referral_for

from . import generation
from .generation import short_description
from .options import options_for
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
        # The full activity for the app's activity screen (#138). Display
        # only: none of these feeds the ranking or the explanation.
        "description": activity.description,
        "materials": activity.materials,
        "cultural_relevance": activity.cultural_relevance,
        "source": activity.source,
        "source_url": activity.source_url,
        "explanation": recommendation.explanation,
        # Chosen by the caregiver after feedback, and kept until done (#177).
        "pinned": recommendation.pinned,
        # Read-only state recorded by the caregiver (FR-14).
        "completion": completion_json(getattr(recommendation, "completion", None)),
        # Read-only, from FeedbackManager (FR-15).
        "feedback": feedback_json(latest_feedback(recommendation.feedback.all())),
    }


def _payload(child, recommendations):
    prefetch_related_objects(recommendations, "completion", "feedback")
    first = recommendations[0] if recommendations else None
    referral = referral_for(child)
    return {
        "batch": str(first.batch) if first else None,
        "generated_at": first.date_generated.isoformat() if first else None,
        "recommendations": [_card(r) for r in recommendations],
        # Worked out on each request and never stored or ranked (#161).
        "referral": referral.to_dict() if referral else None,
    }


class ChildRecommendationsView(APIView):
    """The child's ranked recommendations (#52).

    GET returns the newest stored batch and never generates. POST ranks the
    child's eligible activities (the ranking evaluated at sprint5-eval-v1)
    and stores the top 5 as a new batch: 201 when a batch is stored, 200 when
    the newest batch already matches. Both include the clinic-visit referral
    (#161), or null. Only the child's own caregiver may use either; other
    caregivers' children are 404 and administrators 403.
    """

    permission_classes = [IsCaregiver]

    def get(self, request, child_id):
        child = get_object_or_404(request.user.children, pk=child_id)
        return Response(_payload(child, generation.latest_batch(child)))

    def post(self, request, child_id):
        try:
            result = generation.generate(child_id, request.user)
        except ChildProfile.DoesNotExist:
            raise Http404
        child = request.user.children.get(pk=child_id)
        return Response(
            _payload(child, result.recommendations),
            status=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK,
        )


def _activity_json(activity):
    return {
        "activity_id": activity.activity_id,
        "activity_name": activity.activity_name,
        "developmental_domain": activity.developmental_domain,
        "age_range": activity.age_range,
        "short_description": short_description(activity.description),
        "description": activity.description,
        "materials": activity.materials,
        "cultural_relevance": activity.cultural_relevance,
        "source": activity.source,
        "source_url": activity.source_url,
    }


def _options(recommendation):
    """The options for the caregiver's latest feedback on recommendation."""
    child = recommendation.child
    exclude = generation.completed_activity_ids(child) | {
        r.activity_id for r in generation.latest_batch(child)
    }
    feedback = latest_feedback(recommendation.feedback.all())
    return options_for(recommendation, feedback, exclude)


class RecommendationOptionsView(APIView):
    """Options offered after feedback (#177).

    GET lists up to three activities answering what went wrong, each with
    why it is offered (an empty list until there is feedback with an
    outcome). POST {"activity_id"} pins one of them: a new batch is stored
    with it first, and it stays in later batches until it is done. The
    response is the new batch, as from the recommendations endpoint.
    """

    permission_classes = [IsCaregiver]

    def get(self, request, recommendation_id):
        recommendation = own_recommendation(request.user, recommendation_id)
        return Response(
            {
                "options": [
                    {
                        "reason": o.reason,
                        "title": o.title,
                        "why": o.why,
                        "tip": o.tip,
                        "activity": _activity_json(o.activity),
                    }
                    for o in _options(recommendation)
                ]
            }
        )

    def post(self, request, recommendation_id):
        recommendation = own_recommendation(request.user, recommendation_id)
        chosen = str(request.data.get("activity_id", "")).strip()
        option = next(
            (o for o in _options(recommendation) if o.activity.activity_id == chosen),
            None,
        )
        if option is None:
            raise ValidationError(
                {"activity_id": ["Choose one of the options offered."]}
            )
        child = recommendation.child
        result = generation.generate(
            child.pk, request.user, pin=(option.activity.pk, option.why)
        )
        return Response(
            _payload(child, result.recommendations), status=status.HTTP_201_CREATED
        )
