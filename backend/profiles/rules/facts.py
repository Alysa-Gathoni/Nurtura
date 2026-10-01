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

    When the observation is linked to a guideline ReferenceMilestone,
    expected_age_months is the age by which the guideline expects it and
    source/reference_key/verified describe that entry. Unlinked observations
    leave them empty.
    """

    domain: str
    description: str
    status: str
    observation_date: date
    age_months: float
    age_at_observation_months: float
    expected_age_months: float | None = None
    source: str = ""
    reference_key: str = ""
    verified: bool = False


@dataclass(frozen=True)
class ConcernFact:
    """A caregiver-reported concern about one developmental domain."""

    domain: str


@dataclass(frozen=True)
class InterestFact:
    """One of the child's interests, as recorded by the caregiver."""

    interest: str


def milestone_facts(child, on_date=None):
    """One fact per milestone, using its most recent observation up to on_date.

    Observations of the same milestone are matched on their reference
    milestone when linked, otherwise on domain and description (ignoring case
    and surrounding whitespace).
    """
    on_date = on_date or timezone.localdate()
    age_now = age_in_months(child.date_of_birth, on_date)
    latest = {}
    observations = (
        child.milestones.filter(observation_date__lte=on_date)
        .select_related("reference")
        .order_by("observation_date", "created_at")
    )
    for milestone in observations:
        if milestone.reference_id:
            key = ("reference", milestone.reference_id)
        else:
            key = (milestone.domain, " ".join(milestone.description.lower().split()))
        latest[key] = milestone

    facts = []
    for m in latest.values():
        reference = m.reference
        facts.append(
            MilestoneFact(
                domain=m.domain,
                description=m.description,
                status=m.status,
                observation_date=m.observation_date,
                age_months=age_now,
                age_at_observation_months=age_in_months(
                    child.date_of_birth, m.observation_date
                ),
                expected_age_months=(
                    float(reference.expected_age_months) if reference else None
                ),
                source=reference.source if reference else "",
                reference_key=reference.milestone_key if reference else "",
                verified=reference.verified if reference else False,
            )
        )
    return facts


def concern_facts(child):
    return [ConcernFact(domain=domain) for domain in child.concerns]


def interest_facts(child):
    return [
        InterestFact(interest=" ".join(str(i).lower().split()))
        for i in child.interests
        if str(i).strip()
    ]


def child_facts(child, on_date=None):
    """All facts the guideline rules use for a child."""
    return (
        milestone_facts(child, on_date) + concern_facts(child) + interest_facts(child)
    )
