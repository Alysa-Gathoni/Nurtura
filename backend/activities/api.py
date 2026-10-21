"""Activity management for administrators in the app (#122, FR-13, DR-12).

Administrators list, add and edit activities and move them through the
review workflow. New activities start as Draft. Editing an activity that is
Under Review or Published sends it back to Draft for re-review, the same
rule seed_activities follows, so nothing reaches caregivers unreviewed.
Every change is written to the admin log, like the Django admin.
"""

import re

from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Avg, Count, Q
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from profiles.permissions import IsAdministrator
from recommendations import embeddings

from .choices import AgeRange, ContentStatus, Difficulty, Domain, Source
from .models import DevelopmentalActivity

# Fields an administrator writes; everything else is read-only.
EDITABLE = [
    "activity_name",
    "developmental_domain",
    "age_range",
    "developmental_goal",
    "materials",
    "difficulty_level",
    "description",
    "cultural_relevance",
    "plain_aim",
    "source",
    "source_url",
]


def next_activity_id():
    """ACT-0001-style ID one past the highest existing number."""
    numbers = [
        int(m.group(1))
        for value in DevelopmentalActivity.objects.values_list("activity_id", flat=True)
        if (m := re.fullmatch(r"ACT-(\d+)", value))
    ]
    return f"ACT-{max(numbers, default=0) + 1:04d}"


def log(user, activity, flag, message):
    LogEntry.objects.log_actions(
        user_id=user.pk,
        queryset=DevelopmentalActivity.objects.filter(pk=activity.pk),
        action_flag=flag,
        change_message=message,
        single_object=True,
    )


class AdminActivitySerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(
        source="get_content_status_display", read_only=True
    )
    times_recommended = serializers.IntegerField(read_only=True, default=0)
    feedback_count = serializers.IntegerField(read_only=True, default=0)
    average_rating = serializers.SerializerMethodField()
    searchable = serializers.SerializerMethodField()

    class Meta:
        model = DevelopmentalActivity
        fields = [
            "id",
            "activity_id",
            *EDITABLE,
            "content_status",
            "status_label",
            "times_recommended",
            "feedback_count",
            "average_rating",
            "searchable",
            "updated_at",
        ]
        read_only_fields = ["id", "activity_id", "content_status", "updated_at"]

    def get_average_rating(self, obj):
        value = getattr(obj, "average_rating", None)
        return round(value, 1) if value is not None else None

    def get_searchable(self, obj):
        """Published, with an embedding of its current text."""
        if obj.content_status != ContentStatus.PUBLISHED:
            return False
        current = getattr(obj, "embedding", None)
        return bool(
            current
            and current.text_hash
            == embeddings.text_hash(
                embeddings.MODEL_NAME, embeddings.activity_text(obj)
            )
        )

    def _full_clean(self, instance):
        # Model rules the serializer can't see (e.g. one name per area).
        try:
            instance.full_clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)

    def create(self, validated_data):
        activity = DevelopmentalActivity(
            **validated_data,
            activity_id=next_activity_id(),
            content_status=ContentStatus.DRAFT,
        )
        self._full_clean(activity)
        activity.save()
        return activity

    def update(self, instance, validated_data):
        changed = [
            field
            for field, value in validated_data.items()
            if getattr(instance, field) != value
        ]
        for field, value in validated_data.items():
            setattr(instance, field, value)
        self.returned_to_draft = bool(
            changed and instance.content_status != ContentStatus.DRAFT
        )
        if self.returned_to_draft:
            instance.content_status = ContentStatus.DRAFT
        self.changed_fields = changed
        self._full_clean(instance)
        instance.save()
        return instance


def annotated():
    return (
        DevelopmentalActivity.objects.select_related("embedding")
        .annotate(
            times_recommended=Count("recommendations", distinct=True),
            feedback_count=Count("recommendations__feedback", distinct=True),
            average_rating=Avg("recommendations__feedback__rating"),
        )
        .order_by("activity_id")
    )


class AdminActivityListView(generics.ListCreateAPIView):
    """GET lists activities (?status=, ?domain=, ?search=); POST adds one."""

    permission_classes = [IsAdministrator]
    serializer_class = AdminActivitySerializer
    pagination_class = None

    def get_queryset(self):
        queryset = annotated()
        params = self.request.query_params
        if value := params.get("status"):
            queryset = queryset.filter(content_status=value)
        if value := params.get("domain"):
            queryset = queryset.filter(developmental_domain=value)
        for term in params.get("search", "").split():
            queryset = queryset.filter(
                Q(activity_name__icontains=term)
                | Q(activity_id__icontains=term)
                | Q(description__icontains=term)
            )
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        activity = serializer.save()
        log(self.request.user, activity, ADDITION, "Added in the app.")


class AdminActivityDetailView(generics.RetrieveUpdateAPIView):
    """GET one activity; PATCH or PUT edits it (back to Draft if it was
    Under Review or Published)."""

    permission_classes = [IsAdministrator]
    serializer_class = AdminActivitySerializer

    def get_queryset(self):
        return annotated()

    @transaction.atomic
    def perform_update(self, serializer):
        activity = serializer.save()
        changed = getattr(serializer, "changed_fields", [])
        if changed:
            message = "Changed " + ", ".join(changed) + " in the app."
            if serializer.returned_to_draft:
                message += " Returned to Draft for review."
            log(self.request.user, activity, CHANGE, message)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        # Re-read so the counts and labels reflect the saved state.
        activity = annotated().get(pk=self.get_object().pk)
        return Response(
            AdminActivitySerializer(activity).data, status=response.status_code
        )


class StatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ContentStatus.choices)


class AdminActivityStatusView(APIView):
    """POST {"status": ...} moves an activity through the review workflow."""

    permission_classes = [IsAdministrator]

    def post(self, request, pk):
        activity = generics.get_object_or_404(DevelopmentalActivity, pk=pk)
        serializer = StatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = serializer.validated_data["status"]
        try:
            with transaction.atomic():
                activity.transition_to(target)
                log(
                    request.user,
                    activity,
                    CHANGE,
                    f"Status changed to {ContentStatus(target).label}.",
                )
        except DjangoValidationError as e:
            return Response({"status": e.messages}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AdminActivitySerializer(annotated().get(pk=pk)).data)


class AdminChoicesView(APIView):
    """The allowed values for the activity form's pickers."""

    permission_classes = [IsAdministrator]

    def get(self, request):
        def pairs(choices):
            return [{"value": v, "label": label} for v, label in choices.choices]

        return Response(
            {
                "domains": pairs(Domain),
                "age_ranges": pairs(AgeRange),
                "difficulty_levels": pairs(Difficulty),
                "sources": pairs(Source),
                "statuses": pairs(ContentStatus),
                "transitions": {
                    current: sorted(targets)
                    for current, targets in DevelopmentalActivity.ALLOWED_TRANSITIONS.items()
                },
            }
        )
