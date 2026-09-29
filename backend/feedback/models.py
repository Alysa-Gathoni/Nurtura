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
        return f"{self.recommendation} ({self.get_status_display()})"


class Feedback(models.Model):
    """A caregiver's rating and comment on a specific recommendation."""

    recommendation = models.ForeignKey(
        Recommendation, on_delete=models.CASCADE, related_name="feedback"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 (not helpful) to 5 (very helpful).",
    )
    comment = models.TextField(blank=True)
    date_submitted = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-date_submitted"]
        verbose_name_plural = "feedback"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="rating_between_1_and_5",
            ),
        ]

    def __str__(self):
        return f"{self.rating}/5 on {self.recommendation}"
