"""Facts the rule engine reasons over, built from a child's recorded data."""

from dataclasses import dataclass
from datetime import date

from django.utils import timezone

AVERAGE_DAYS_PER_MONTH = 365.25 / 12


def age_in_months(date_of_birth, on_date):
    """Age in months on on_date; negative before birth (prenatal profiles)."""
    return (on_date - date_of_birth).days / AVERAGE_DAYS_PER_MONTH


@dataclass(frozen=True)
class MilestoneFact:
    """The latest observation of one milestone for a child.

    expected_age_months is the age by which guidelines expect the milestone;
    it is filled in from the guideline milestone catalogue (#18) and is None
    until a recorded milestone is linked to it.
    """

    domain: str
    description: str
    status: str
    observation_date: date
    age_months: float
    age_at_observation_months: float
    expected_age_months: float | None = None


def milestone_facts(child, on_date=None):
    """One fact per milestone, using its most recent observation up to on_date.

    Observations of the same milestone are matched on domain and description,
    ignoring case and surrounding whitespace.
    """
    on_date = on_date or timezone.localdate()
    age_now = age_in_months(child.date_of_birth, on_date)
    latest = {}
    observations = child.milestones.filter(observation_date__lte=on_date).order_by(
        "observation_date", "created_at"
    )
    for milestone in observations:
        key = (milestone.domain, " ".join(milestone.description.lower().split()))
        latest[key] = milestone
    return [
        MilestoneFact(
            domain=m.domain,
            description=m.description,
            status=m.status,
            observation_date=m.observation_date,
            age_months=age_now,
            age_at_observation_months=age_in_months(
                child.date_of_birth, m.observation_date
            ),
        )
        for m in latest.values()
    ]
