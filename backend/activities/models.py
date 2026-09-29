from django.db import models
from django.db.models.functions import Lower

from .choices import AgeRange, Difficulty, Domain, Source


class DevelopmentalActivity(models.Model):
    """An evidence-based activity in the activity repository.

    content_status (Draft/Under Review/Published) is added separately in #3.
    """

    activity_id = models.CharField(
        max_length=20, unique=True, help_text="Dataset ID, e.g. ACT001."
    )
    activity_name = models.CharField(max_length=200)
    developmental_domain = models.CharField(max_length=20, choices=Domain.choices)
    age_range = models.CharField(max_length=20, choices=AgeRange.choices)
    developmental_goal = models.TextField()
    materials = models.TextField(help_text='Use "None" if nothing is required.')
    difficulty_level = models.CharField(max_length=20, choices=Difficulty.choices)
    description = models.TextField()
    cultural_relevance = models.TextField()
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        help_text="Organisation whose guidance this activity is traceable to.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["activity_id"]
        verbose_name_plural = "developmental activities"
        constraints = [
            models.UniqueConstraint(
                Lower("activity_name"),
                "developmental_domain",
                name="unique_activity_name_per_domain",
            ),
        ]

    def __str__(self):
        return f"{self.activity_id}: {self.activity_name}"
