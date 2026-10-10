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

from . import two_factor
from .models import LoginChallenge, ReferenceMilestone
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


def _signed_in(user, device_trusted_until=None):
    token, _ = Token.objects.get_or_create(user=user)
    return {
        "token": token.key,
        "user": UserSerializer(user).data,
        "device_trusted_until": (
            device_trusted_until.isoformat() if device_trusted_until else None
        ),
    }


class RegisterView(generics.CreateAPIView):
    """Create a caregiver account, then confirm the email with a code (#86).

    No token yet: the app gets it from /auth/login/verify/ once the emailed
    code is entered, which also proves the address belongs to the caregiver.
    """

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
            challenge = two_factor.start(user, LoginChallenge.Purpose.REGISTER)
        return Response(
            {
                **two_factor.challenge_payload(challenge),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(ObtainAuthToken):
    """Password first, then (on an untrusted device) an emailed code (#86).

    A device trusted in the last 30 days gets the token straight away (200).
    Otherwise a code is emailed and the response (202) names the challenge
    to send to /auth/login/verify/. Throttled per client (rate in settings).
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        if two_factor.is_trusted(user, request.data.get("device_id")):
            return Response(_signed_in(user))
        if not user.email:
            raise ValidationError(
                {
                    "non_field_errors": [
                        "This account has no email address for the login code. "
                        "Please contact the Nurtura team."
                    ]
                }
            )
        challenge = two_factor.start(user)
        return Response(
            two_factor.challenge_payload(challenge), status=status.HTTP_202_ACCEPTED
        )


class VerifyLoginView(APIView):
    """Exchange the emailed code for an API token (#86)."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "two_factor"

    def post(self, request):
        challenge_id = request.data.get("challenge")
        if not challenge_id:
            raise ValidationError({"challenge": ["This field is required."]})
        try:
            verified = two_factor.verify(challenge_id, request.data.get("code"))
        except (two_factor.ChallengeError, DjangoValidationError) as exc:
            message = (
                str(exc)
                if isinstance(exc, two_factor.ChallengeError)
                else "This code has already been used. Please log in again."
            )
            raise ValidationError({"code": [message]})
        device_id = request.data.get("device_id")
        remember = request.data.get("remember_device", True) is not False
        until = None
        if remember and two_factor.valid_device_id(device_id):
            until = two_factor.trust(verified.user, device_id)
        return Response(_signed_in(verified.user, until))


class ResendCodeView(APIView):
    """Email a fresh code for an open challenge (#86)."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "two_factor"

    def post(self, request):
        try:
            challenge = two_factor.resend(request.data.get("challenge"))
        except (two_factor.ChallengeError, DjangoValidationError) as exc:
            message = (
                str(exc)
                if isinstance(exc, two_factor.ChallengeError)
                else "This code has already been used. Please log in again."
            )
            raise ValidationError({"code": [message]})
        return Response(two_factor.challenge_payload(challenge))


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
