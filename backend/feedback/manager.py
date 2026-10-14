"""The single way caregiver feedback enters the system (FR-15).

Feedback is about one recommendation, and a caregiver keeps one entry per
recommendation: submitting again replaces the rating and comment, so a
change of mind doesn't count twice in the evaluation. Feedback doesn't need
the activity to be completed ("not suitable for us" is useful feedback).
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from recommendations.models import Recommendation

from .models import Feedback

MAX_COMMENT_LENGTH = 1000


def latest(feedback_rows):
    """The newest of a recommendation's feedback rows, or None."""
    rows = list(feedback_rows)
    if not rows:
        return None
    return max(rows, key=lambda f: (f.date_submitted, f.pk))


class FeedbackManager:
    @staticmethod
    def submit(caregiver, recommendation_id, rating, comment=""):
        """Record or replace the caregiver's feedback on a recommendation.

        Returns (feedback, created). Raises Recommendation.DoesNotExist when
        the recommendation isn't the caregiver's, and ValidationError for a
        rating outside 1-5 or a comment over MAX_COMMENT_LENGTH characters.
        """
        comment = (comment or "").strip()
        errors = {}
        if isinstance(rating, bool) or not isinstance(rating, int):
            errors["rating"] = ["Choose a rating from 1 to 5."]
        elif not 1 <= rating <= 5:
            errors["rating"] = ["Choose a rating from 1 to 5."]
        if len(comment) > MAX_COMMENT_LENGTH:
            errors["comment"] = [
                f"Keep the comment to {MAX_COMMENT_LENGTH} characters or fewer."
            ]
        if errors:
            raise ValidationError(errors)

        with transaction.atomic():
            # Locking the recommendation stops two submissions at once from
            # both creating an entry.
            recommendation = Recommendation.objects.select_for_update(of=("self",)).get(
                pk=recommendation_id, child__caregiver=caregiver
            )
            feedback = latest(recommendation.feedback.all())
            created = feedback is None
            if created:
                feedback = Feedback(recommendation=recommendation)
            feedback.rating = rating
            feedback.comment = comment
            feedback.date_submitted = timezone.now()
            feedback.full_clean()
            feedback.save()
        return feedback, created

    @staticmethod
    def for_caregiver(caregiver, recommendation_id):
        """The caregiver's feedback on a recommendation, or None.

        Raises Recommendation.DoesNotExist like submit().
        """
        recommendation = Recommendation.objects.get(
            pk=recommendation_id, child__caregiver=caregiver
        )
        return latest(recommendation.feedback.all())
