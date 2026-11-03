"""The single way caregiver feedback enters the system (FR-15).

Feedback is about one recommendation, and a caregiver keeps one entry per
recommendation: submitting again replaces the whole entry, so a
change of mind doesn't count twice in the evaluation. Feedback doesn't need
the activity to be completed ("not suitable for us" is useful feedback).
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from recommendations.models import Recommendation

from . import observations
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
    def submit(
        caregiver,
        recommendation_id,
        rating=None,
        comment="",
        outcome="",
        issues=None,
        interest="",
        observed=None,
    ):
        """Record or replace the caregiver's feedback on a recommendation.

        Returns (feedback, created); feedback.recorded lists the observed
        skills recorded as milestones (#185). Raises
        Recommendation.DoesNotExist when the recommendation isn't the
        caregiver's, and ValidationError for a rating outside 1-5 (it is
        optional), a comment over MAX_COMMENT_LENGTH characters, an unknown
        outcome, issue (#175) or interest, or an observed skill that wasn't
        offered. Recording skills needs the privacy notice agreed, like any
        milestone. Issues are stored once each, in the order of
        Feedback.Issue.
        """
        from profiles import privacy

        comment = (comment or "").strip()
        outcome = (outcome or "").strip()
        interest = (interest or "").strip()
        issues = list(issues or [])
        observed = list(observed or [])
        errors = {}
        if interest and interest not in Feedback.Interest.values:
            errors["interest"] = ["Choose how interested your child was."]
        if observed and privacy.consent_required(caregiver):
            errors["observed"] = ["Please read and agree to the privacy notice first."]
        if outcome and outcome not in Feedback.Outcome.values:
            errors["outcome"] = ["Choose how it went."]
        unknown = [i for i in issues if i not in Feedback.Issue.values]
        if unknown:
            errors["issues"] = [f"Unknown option: {', '.join(map(str, unknown))}."]
        issues = [i for i in Feedback.Issue.values if i in issues]
        if rating is not None and (
            isinstance(rating, bool)
            or not isinstance(rating, int)
            or not 1 <= rating <= 5
        ):
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
            feedback.outcome = outcome
            feedback.issues = issues
            feedback.interest = interest
            feedback.date_submitted = timezone.now()
            feedback.full_clean()
            feedback.save()
            try:
                feedback.recorded = observations.record(recommendation, observed)
            except ValueError as exc:
                raise ValidationError(
                    {"observed": [f"Not offered for this activity: {exc}."]}
                ) from exc
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
