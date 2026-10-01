from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from .models import (
    ChildProfile,
    DevelopmentalMilestone,
    DevelopmentalProfile,
    ReferenceMilestone,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """Self-registration always creates a Caregiver (FR-01).

    Administrator accounts are created by existing administrators or with
    createsuperuser, never through the public API.
    """

    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value

    def validate(self, attrs):
        # Run Django's password validators (NFR-02), comparing against the
        # other fields so the password can't just be the username.
        user = User(**{k: v for k, v in attrs.items() if k != "password"})
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(role=User.Role.CAREGIVER, **validated_data)


class ChildProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildProfile
        fields = [
            "id",
            "name",
            "date_of_birth",
            "gender",
            "interests",
            "preferences",
            "concerns",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ReferenceMilestoneSerializer(serializers.ModelSerializer):
    expected_age_months = serializers.FloatField()

    class Meta:
        model = ReferenceMilestone
        fields = [
            "id",
            "milestone_key",
            "domain",
            "description",
            "expected_age_months",
            "source",
        ]


class DevelopmentalMilestoneSerializer(serializers.ModelSerializer):
    reference_key = serializers.CharField(
        source="reference.milestone_key", read_only=True, default=None
    )

    class Meta:
        model = DevelopmentalMilestone
        fields = [
            "id",
            "reference",
            "reference_key",
            "domain",
            "description",
            "status",
            "observation_date",
            "created_at",
        ]
        read_only_fields = fields


class RecordMilestoneSerializer(serializers.Serializer):
    """A milestone observation, chosen from the guideline catalogue.

    The API only accepts catalogue milestones: free-text milestones have no
    expected age, so the rule engine couldn't use them.
    """

    reference = serializers.PrimaryKeyRelatedField(
        queryset=ReferenceMilestone.objects.all()
    )
    status = serializers.ChoiceField(choices=DevelopmentalMilestone.Status.choices)
    observation_date = serializers.DateField(required=False)

    def validate_observation_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Can't be in the future.")
        return value

    def validate(self, attrs):
        child = self.context["child"]
        if child.date_of_birth > timezone.localdate():
            raise serializers.ValidationError(
                "Milestones can be recorded once your baby is born."
            )
        observed = attrs.get("observation_date")
        if observed and observed < child.date_of_birth:
            raise serializers.ValidationError(
                {"observation_date": "Can't be before the date of birth."}
            )
        return attrs


class DevelopmentalProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevelopmentalProfile
        fields = ["age_months", "scores", "ranked_domains", "reasons", "generated_at"]
