from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from recommendations.models import Recommendation


class CompletedActivity(models.Model):
    """Records that a recommended activity was carried out.

    A recommendation has at most one completion; a missing row means the
    activity has not been done, so status only describes the degree.
    """

    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        PARTIALLY_COMPLETED = "partially_completed", "Partially Completed"

    recommendation = models.OneToOneField(
        Recommendation, on_delete=models.CASCADE, related_name="completion"
    )
    completion_date = models.DateField(default=timezone.localdate)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.COMPLETED
    )

    class Meta:
        ordering = ["-completion_date"]
        verbose_name_plural = "completed activities"

    def __str__(self):
        # Names the activity, not the child: the admin review shows this
        # label and keeps families out of it (FR-16).
        activity = self.recommendation.activity
        return f"{activity.activity_name} ({self.get_status_display()})"


class Feedback(models.Model):
    """A caregiver's view of a recommendation: how it went, what got in the
    way, the child's interest, an optional 1-5 rating and a comment."""

    class Outcome(models.TextChoices):
        WENT_WELL = "went_well", "Went well"
        PARTLY = "partly", "Partly"
        DIDNT_WORK = "didnt_work", "Didn't work"

    class Issue(models.TextChoices):
        TOO_HARD = "too_hard", "Too hard"
        TOO_EASY = "too_easy", "Too easy"
        NOT_INTERESTED = "not_interested", "My child wasn't interested"
        NO_MATERIALS = "no_materials", "I didn't have the materials"
        NO_TIME = "no_time", "Not enough time"
        CHILD_UPSET = "child_upset", "My child got upset"

    class Interest(models.TextChoices):
        BORED = "bored", "Bored"
        OKAY = "okay", "Okay"
        HAPPY = "happy", "Happy"
        LOVED_IT = "loved_it", "Loved it"

    recommendation = models.ForeignKey(
        Recommendation, on_delete=models.CASCADE, related_name="feedback"
    )
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 (not helpful) to 5 (very helpful); optional since #185.",
    )
    comment = models.TextField(blank=True)
    # How it went and what got in the way (#175). Blank on feedback given
    # before these were asked.
    outcome = models.CharField(max_length=20, choices=Outcome.choices, blank=True)
    issues = models.JSONField(
        default=list, blank=True, help_text='Issue values, e.g. ["too_hard"].'
    )
    # The child's interest, from the "Well done!" sheet (#185).
    interest = models.CharField(max_length=20, choices=Interest.choices, blank=True)
    date_submitted = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date_submitted"]
        verbose_name_plural = "feedback"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__isnull=True)
                | (models.Q(rating__gte=1) & models.Q(rating__lte=5)),
                name="rating_between_1_and_5",
            ),
        ]

    def __str__(self):
        # The activity, not the child (see CompletedActivity.__str__).
        rating = f"{self.rating}/5" if self.rating else "Feedback"
        return f"{rating} on {self.recommendation.activity.activity_name}"
