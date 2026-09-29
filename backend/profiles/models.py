from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from activities.choices import Domain


class User(AbstractUser):
    """Project user model.

    Defined up front because Django does not support swapping AUTH_USER_MODEL
    after the first migration. The Caregiver/Administrator role is added in #4.
    """


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
