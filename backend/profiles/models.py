from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from activities.choices import Domain


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def record_milestone(self, domain, description, status, observation_date=None):
        """Validate and save a milestone observation for this child."""
        milestone = DevelopmentalMilestone(
            child=self,
            domain=domain,
            description=description,
            status=status,
            observation_date=observation_date or timezone.localdate(),
        )
        milestone.full_clean()
        milestone.save()
        return milestone


class DevelopmentalMilestone(models.Model):
    class Status(models.TextChoices):
        ACHIEVED = "achieved", "Achieved"
        EMERGING = "emerging", "Emerging"
        NOT_YET = "not_yet", "Not yet"

    child = models.ForeignKey(
        ChildProfile, on_delete=models.CASCADE, related_name="milestones"
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
