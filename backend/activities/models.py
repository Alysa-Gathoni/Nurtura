from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from .choices import AgeRange, ContentStatus, Difficulty, Domain, Source

PLAIN_AIM_MAX_WORDS = 20


def validate_plain_aim(value):
    """At most PLAIN_AIM_MAX_WORDS words, and it must read after "Its aim is to"."""
    words = value.split()
    if len(words) > PLAIN_AIM_MAX_WORDS:
        raise ValidationError(
            f"Use at most {PLAIN_AIM_MAX_WORDS} words (this has {len(words)})."
        )
    if words and (words[0][0].isupper() or value.rstrip().endswith(".")):
        raise ValidationError(
            'Write it to follow "Its aim is to": start in lower case, no final full stop.'
        )


class DevelopmentalActivityQuerySet(models.QuerySet):
    def published(self):
        """Activities eligible for recommendation."""
        return self.filter(content_status=ContentStatus.PUBLISHED)


class DevelopmentalActivity(models.Model):
    """An evidence-based activity in the activity repository."""

    # Content-validation workflow (FR-13, DR-12): content must be reviewed
    # before it is published; any state can go back to draft for edits.
    ALLOWED_TRANSITIONS = {
        ContentStatus.DRAFT: {ContentStatus.UNDER_REVIEW},
        ContentStatus.UNDER_REVIEW: {ContentStatus.PUBLISHED, ContentStatus.DRAFT},
        ContentStatus.PUBLISHED: {ContentStatus.DRAFT},
    }

    activity_id = models.CharField(
        max_length=20, unique=True, help_text="Dataset ID, e.g. ACT-0001."
    )
    activity_name = models.CharField(max_length=200)
    developmental_domain = models.CharField(max_length=20, choices=Domain.choices)
    age_range = models.CharField(max_length=20, choices=AgeRange.choices)
    developmental_goal = models.TextField()
    materials = models.TextField(help_text='Use "None" if nothing is required.')
    difficulty_level = models.CharField(max_length=20, choices=Difficulty.choices)
    description = models.TextField()
    cultural_relevance = models.TextField()
    # Caregiver-facing wording of the goal, shown in explanations as "Its aim
    # is to ..." (#68). Deliberately outside the embedding text, the ranking
    # and the provenance hash, so it can be written or reworded without
    # changing any recommendation or the Sprint 5 evaluation.
    plain_aim = models.CharField(
        max_length=200,
        blank=True,
        validators=[validate_plain_aim],
        help_text='Completes "Its aim is to ...": second person, at most '
        f"{PLAIN_AIM_MAX_WORDS} words, no technical terms, British spelling. "
        "Leave blank to show no aim sentence.",
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        help_text="Organisation whose guidance this activity is traceable to.",
    )
    source_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Link to the specific guidance document, once verified.",
    )
    content_status = models.CharField(
        max_length=20,
        choices=ContentStatus.choices,
        default=ContentStatus.DRAFT,
        help_text="Only published activities are recommended.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DevelopmentalActivityQuerySet.as_manager()

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

    def transition_to(self, new_status):
        """Move to new_status if the workflow allows it, and save."""
        if new_status not in self.ALLOWED_TRANSITIONS[self.content_status]:
            raise ValidationError(
                f"Cannot move {self.activity_id} from "
                f"{self.get_content_status_display()} to "
                f"{ContentStatus(new_status).label}."
            )
        self.content_status = new_status
        self.save(update_fields=["content_status", "updated_at"])
