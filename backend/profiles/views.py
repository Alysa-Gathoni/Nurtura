from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from activities.choices import Domain

from .models import ReferenceMilestone
from .permissions import IsCaregiver
from .serializers import (
    ChildProfileSerializer,
    DevelopmentalMilestoneSerializer,
    DevelopmentalProfileSerializer,
    RecordMilestoneSerializer,
    ReferenceMilestoneSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    """Create a caregiver account and return its API token."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = Token.objects.create(user=user)
        return Response(
            {"token": token.key, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(ObtainAuthToken):
    """Exchange username and password for an API token.

    Throttled per client to slow down password guessing (rate in settings).
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class LogoutView(APIView):
    """Invalidate the current API token."""

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ChildProfileViewSet(viewsets.ModelViewSet):
    """Caregivers manage only their own children's profiles."""

    serializer_class = ChildProfileSerializer
    permission_classes = [IsCaregiver]

    def get_queryset(self):
        return self.request.user.children.all()

    def perform_create(self, serializer):
        child = serializer.save(caregiver=self.request.user)
        child.refresh_developmental_profile()

    def perform_update(self, serializer):
        # Concerns and interests feed the rule engine.
        serializer.save().refresh_developmental_profile()

    @action(detail=True, methods=["get", "post"])
    def milestones(self, request, pk=None):
        """List the child's milestone observations, or record one.

        Recording a milestone regenerates the child's DevelopmentalProfile.
        """
        child = self.get_object()
        if request.method == "GET":
            observations = child.milestones.select_related("reference")
            return Response(
                DevelopmentalMilestoneSerializer(observations, many=True).data
            )

        serializer = RecordMilestoneSerializer(
            data=request.data, context={"child": child}
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            try:
                milestone = child.record_milestone(**serializer.validated_data)
            except DjangoValidationError as exc:
                raise ValidationError(exc.message_dict) from exc
            profile = child.refresh_developmental_profile()
        return Response(
            {
                "milestone": DevelopmentalMilestoneSerializer(milestone).data,
                "profile": DevelopmentalProfileSerializer(profile).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def profile(self, request, pk=None):
        """The child's DevelopmentalProfile, regenerated for today's age."""
        profile = self.get_object().refresh_developmental_profile()
        return Response(DevelopmentalProfileSerializer(profile).data)


class ReferenceMilestoneViewSet(viewsets.ReadOnlyModelViewSet):
    """The guideline milestone catalogue, for the milestone picker.

    ?search= matches every word against the description or key;
    ?domain= limits results to one developmental domain.
    """

    serializer_class = ReferenceMilestoneSerializer

    def get_queryset(self):
        queryset = ReferenceMilestone.objects.all()
        for term in self.request.query_params.get("search", "").split():
            queryset = queryset.filter(
                Q(description__icontains=term) | Q(milestone_key__icontains=term)
            )
        domain = self.request.query_params.get("domain", "").strip()
        if domain:
            if domain not in Domain.values:
                raise ValidationError(
                    {"domain": f"Must be one of: {', '.join(Domain.values)}."}
                )
            queryset = queryset.filter(domain=domain)
        return queryset
