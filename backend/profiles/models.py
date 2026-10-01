from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from activities.choices import Domain, Source


def validate_domain_list(value):
    """A list of distinct developmental domain names, e.g. ["Sensory"]."""
    if not isinstance(value, list):
        raise ValidationError("Must be a list of domains.")
    invalid = [item for item in value if item not in Domain.values]
    if invalid:
        raise ValidationError(
            f"Unknown domain(s): {invalid}. Allowed: {', '.join(Domain.values)}."
        )
    if len(set(value)) != len(value):
        raise ValidationError("Each domain may only be listed once.")


class NurturaUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMINISTRATOR)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Project user with a Caregiver/Administrator role (FR-01, FR-02).

    Caregivers use the mobile app via the API; Administrators manage the
    activity repository via the Django admin. is_staff (admin site access) is
    derived from the role so the two can't drift apart.
    """

    class Role(models.TextChoices):
        CAREGIVER = "caregiver", "Caregiver"
        ADMINISTRATOR = "administrator", "Administrator"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CAREGIVER)

    objects = NurturaUserManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            # One account per email, ignoring case; blank emails (e.g. from
            # createsuperuser) are allowed more than once.
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="unique_user_email_case_insensitive",
                violation_error_message="A user with this email already exists.",
            ),
        ]

    @property
    def is_caregiver(self):
        return self.role == self.Role.CAREGIVER

    @property
    def is_administrator(self):
        return self.role == self.Role.ADMINISTRATOR

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMINISTRATOR
        self.is_staff = self.is_administrator
        super().save(*args, **kwargs)


class ChildProfile(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        UNSPECIFIED = "unspecified", "Prefer not to say"

    caregiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="children",
    )
    name = models.CharField(max_length=100)
    date_of_birth = models.DateField(
        help_text="For expecting parents, the expected due date."
    )
    gender = models.CharField(
        max_length=20, choices=Gender.choices, default=Gender.UNSPECIFIED
    )
    interests = models.JSONField(
        default=list,
        blank=True,
        help_text='List of keywords, e.g. ["music", "animals"].',
    )
    preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Caregiver preferences used for ranking, e.g. preferred difficulty.",
    )
    concerns = models.JSONField(
        default=list,
        blank=True,
        validators=[validate_domain_list],
        help_text='Domains the caregiver is concerned about, e.g. ["Sensory"].',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def refresh_developmental_profile(self, on_date=None):
        """Run the rule engine and store the result as this child's profile."""
        from .rules import build_profile  # rules import these models

        evaluation = build_profile(self, on_date=on_date).to_dict()
        profile, _ = DevelopmentalProfile.objects.update_or_create(
            child=self,
            defaults={
                "age_months": evaluation["age_months"],
                "scores": evaluation["scores"],
                "ranked_domains": evaluation["ranked_domains"],
                "reasons": evaluation["reasons"],
            },
        )
        return profile

    def record_milestone(
        self,
        domain=None,
        description=None,
        status=None,
        observation_date=None,
        reference=None,
    ):
        """Validate and save a milestone observation for this child.

        With a reference milestone, domain and description default to the
        reference's, so callers only need the status.
        """
        if reference is not None:
            domain = domain or reference.domain
            description = description or reference.description
        milestone = DevelopmentalMilestone(
            child=self,
            reference=reference,
            domain=domain,
            description=description,
            status=status,
            observation_date=observation_date or timezone.localdate(),
        )
        milestone.full_clean()
        milestone.save()
        return milestone


class ReferenceMilestone(models.Model):
    """A guideline milestone (CDC/WHO) with the age by which it is expected.

    Entries are written from the cited guideline and marked verified once
    checked against the source document. They are reference data for the rule
    engine, not caregiver-facing content, so they use a verified flag rather
    than the activity review workflow.
    """

    milestone_key = models.CharField(
        max_length=30, unique=True, help_text="e.g. CDC-12M-LA-01 or WHO-MO-06."
    )
    source = models.CharField(max_length=20, choices=Source.choices)
    expected_age_months = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        help_text="Age by which the guideline expects the milestone.",
    )
    domain = models.CharField(max_length=20, choices=Domain.choices)
    description = models.CharField(max_length=255)
    source_reference = models.CharField(max_length=300)
    notes = models.TextField(blank=True)
    verified = models.BooleanField(
        default=False, help_text="Checked against the source document."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expected_age_months", "milestone_key"]

    def __str__(self):
        return f"{self.milestone_key}: {self.description}"


class DevelopmentalMilestone(models.Model):
    class Status(models.TextChoices):
        ACHIEVED = "achieved", "Achieved"
        EMERGING = "emerging", "Emerging"
        NOT_YET = "not_yet", "Not yet"

    child = models.ForeignKey(
        ChildProfile, on_delete=models.CASCADE, related_name="milestones"
    )
    reference = models.ForeignKey(
        ReferenceMilestone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="observations",
        help_text="Guideline milestone this observation is for, if any.",
    )
    domain = models.CharField(max_length=20, choices=Domain.choices)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices)
    observation_date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observation_date", "-created_at"]

    def __str__(self):
        return f"{self.child}: {self.description} ({self.get_status_display()})"

    def clean(self):
        if self.reference and self.domain and self.domain != self.reference.domain:
            raise ValidationError(
                {
                    "domain": f"Must match the reference milestone's domain "
                    f"({self.reference.domain})."
                }
            )


class DevelopmentalProfile(models.Model):
    """A child's latest developmental profile from the rule engine (FR-05).

    Regenerated whenever its inputs change (a milestone is recorded, or the
    child's details, concerns or interests are saved through the API) and
    when it is requested, since priorities also change as the child ages.
    """

    child = models.OneToOneField(
        ChildProfile, on_delete=models.CASCADE, related_name="developmental_profile"
    )
    age_months = models.FloatField(
        null=True, help_text="Age when generated; negative for prenatal profiles."
    )
    scores = models.JSONField(
        default=dict, help_text="Priority per domain, 0-1 (top domain = 1)."
    )
    ranked_domains = models.JSONField(default=list)
    reasons = models.JSONField(
        default=list, help_text="Rules that fired, with sources and reasons."
    )
    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.child}"

    @property
    def top_domain(self):
        return self.ranked_domains[0] if self.ranked_domains else None
