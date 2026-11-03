"""Skills a caregiver may have observed during an activity (#185).

The "Well done!" sheet asks "Did you observe any of these?". The skills
offered are guideline milestones (the CDC/WHO catalogue) in the activity's
area that are due or coming up for the child: expected between
WINDOW_BEFORE months before and WINDOW_AFTER months after the child's age,
and not already Achieved. Only catalogue milestones have an expected age
the rule engine can use, so free text is never offered.

Ticking one records it as Emerging, the ASQ-3 "sometimes": seeing a skill
once during play shows it is starting rather than secure. A milestone
already Emerging or Achieved is left as it is. Pregnancy activities have no
milestones to observe, and the catalogue has no Sensory milestones.
"""

from django.utils import timezone

from profiles.models import DevelopmentalMilestone, ReferenceMilestone
from profiles.rules.facts import age_in_months

WINDOW_BEFORE = 6
WINDOW_AFTER = 3
MAX_SKILLS = 6

Status = DevelopmentalMilestone.Status


def _latest_statuses(child):
    """{reference pk: status of the latest observation}."""
    latest = {}
    for m in child.milestones.filter(reference__isnull=False).order_by(
        "observation_date", "created_at"
    ):
        latest[m.reference_id] = m.status
    return latest


def observable(recommendation, on_date=None):
    """[(ReferenceMilestone, current status or None)], earliest expected first."""
    child = recommendation.child
    on_date = on_date or timezone.localdate()
    age = age_in_months(child.date_of_birth, on_date)
    if age < 0:
        return []
    latest = _latest_statuses(child)
    found = []
    candidates = ReferenceMilestone.objects.filter(
        domain=recommendation.activity.developmental_domain,
        expected_age_months__gte=max(0, age - WINDOW_BEFORE),
        expected_age_months__lte=age + WINDOW_AFTER,
    ).order_by("expected_age_months", "milestone_key")
    for ref in candidates:
        status = latest.get(ref.pk)
        if status == Status.ACHIEVED:
            continue
        found.append((ref, status))
        if len(found) == MAX_SKILLS:
            break
    return found


def record(recommendation, keys):
    """Record the observed skills (milestone keys) as Emerging.

    Returns the descriptions recorded. Raises ValueError for a key that
    wasn't offered for this recommendation.
    """
    offered = {
        ref.milestone_key: (ref, status) for ref, status in observable(recommendation)
    }
    unknown = [k for k in keys if k not in offered]
    if unknown:
        raise ValueError(", ".join(unknown))
    child = recommendation.child
    recorded = []
    for key in dict.fromkeys(keys):
        ref, status = offered[key]
        if status in (Status.EMERGING, Status.ACHIEVED):
            continue
        child.record_milestone(reference=ref, status=Status.EMERGING)
        recorded.append(ref.description)
    if recorded:
        child.refresh_developmental_profile()
    return recorded
