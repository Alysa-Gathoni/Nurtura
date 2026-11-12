"""The milestone tracker: a child's milestones by area (#192).

For each area with guideline milestones (Motor, Socio-Emotional, Language,
Cognitive; the catalogue has no Sensory milestones), the tracker lists:

- every catalogue milestone with an observation, whatever its age; and
- unrecorded milestones expected from RECENT_MONTHS before the child's age
  to UPCOMING_MONTHS after it, so the caregiver sees what is due and what
  is coming without the whole catalogue.

Each entry has its latest status and the child's age when it was observed
("Achieved at 22 months"). Before birth there is nothing to track.
"""

from django.utils import timezone

from activities.choices import Domain

from .models import ReferenceMilestone
from .rules.facts import age_in_months
from .rules.guidelines import UPCOMING_WINDOW_MONTHS


def whole_months(date_of_birth, on_date):
    """Completed calendar months, as the app counts them (#214).

    For display only: the rule engine keeps age_in_months (days divided by
    the average month), so the ranking is unchanged.
    """
    months = (on_date.year - date_of_birth.year) * 12 + (
        on_date.month - date_of_birth.month
    )
    if on_date.day < date_of_birth.day:
        months -= 1
    return months


RECENT_MONTHS = 6
UPCOMING_MONTHS = UPCOMING_WINDOW_MONTHS
AREAS = (Domain.MOTOR, Domain.SOCIO_EMOTIONAL, Domain.LANGUAGE, Domain.COGNITIVE)


def _latest_observations(child, on_date):
    latest = {}
    for m in child.milestones.filter(
        reference__isnull=False, observation_date__lte=on_date
    ).order_by("observation_date", "created_at"):
        latest[m.reference_id] = m
    return latest


def tracker(child, on_date=None):
    on_date = on_date or timezone.localdate()
    age = age_in_months(child.date_of_birth, on_date)
    if age < 0:
        return {"age_months": round(age, 1), "prenatal": True, "areas": []}

    latest = _latest_observations(child, on_date)
    areas = []
    for domain in AREAS:
        entries = []
        for ref in ReferenceMilestone.objects.filter(domain=domain).order_by(
            "expected_age_months", "milestone_key"
        ):
            expected = float(ref.expected_age_months)
            observation = latest.get(ref.pk)
            in_window = age - RECENT_MONTHS <= expected <= age + UPCOMING_MONTHS
            if observation is None and not in_window:
                continue
            entries.append(
                {
                    "id": ref.pk,
                    "key": ref.milestone_key,
                    "description": ref.description,
                    "source": ref.source,
                    "expected_age_months": expected,
                    "due": expected <= age,
                    "status": observation.status if observation else "",
                    "observed_on": (
                        observation.observation_date.isoformat()
                        if observation
                        else None
                    ),
                    "observed_at_months": (
                        whole_months(child.date_of_birth, observation.observation_date)
                        if observation
                        else None
                    ),
                }
            )
        areas.append({"domain": domain, "milestones": entries})
    return {"age_months": round(age, 1), "prenatal": False, "areas": areas}
