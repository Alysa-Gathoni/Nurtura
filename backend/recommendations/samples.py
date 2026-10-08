"""Sample child profiles for spot-checking retrieval relevance (#31).

Each sample is a clear-cut case built from real catalogue milestones (or
caregiver concerns), with the domain(s) its retrievals should come from. The
spot_check_retrieval command and the tests both use them.
"""

import datetime
from dataclasses import dataclass, field

from django.utils import timezone
from django.utils.text import slugify

from profiles.models import ChildProfile, ReferenceMilestone

AVERAGE_DAYS_PER_MONTH = 365.25 / 12


@dataclass(frozen=True)
class SampleProfile:
    name: str
    age_months: float  # negative = weeks/months until the due date
    expected_domains: tuple
    not_yet: tuple = ()  # catalogue milestone keys observed as Not yet
    concerns: tuple = ()
    interests: tuple = ()
    note: str = ""

    @property
    def key(self):
        """Stable ID used in relevance labels, e.g. "language-delay".

        Derived from the name, so renaming a sample changes its key and its
        existing labels would need updating.
        """
        return slugify(self.name)


SAMPLE_PROFILES = (
    SampleProfile(
        name="Language delay",
        age_months=6,
        expected_domains=("Language",),
        not_yet=("CDC-04M-LA-01",),
        note="6 months, not cooing yet (expected by 4 months)",
    ),
    SampleProfile(
        name="Motor delay",
        age_months=13,
        expected_domains=("Motor",),
        not_yet=("CDC-12M-MO-01",),
        note="13 months, not pulling up to stand (expected by 12 months)",
    ),
    SampleProfile(
        name="Cognitive delay",
        age_months=10,
        expected_domains=("Cognitive",),
        not_yet=("CDC-09M-CO-01",),
        note="10 months, not looking for dropped objects (expected by 9 months)",
    ),
    SampleProfile(
        name="Socio-emotional delay",
        age_months=10,
        expected_domains=("Socio-Emotional",),
        not_yet=("CDC-09M-SE-03",),
        note="10 months, not looking when name is called (expected by 9 months)",
    ),
    SampleProfile(
        name="Sensory concern",
        age_months=8,
        expected_domains=("Sensory",),
        concerns=("Sensory",),
        interests=("water play", "textures"),
        note="8 months, caregiver concerned about sensory development",
    ),
    SampleProfile(
        name="Language and motor delay",
        age_months=19,
        expected_domains=("Language", "Motor"),
        not_yet=("CDC-18M-LA-01", "CDC-18M-MO-01"),
        note="19 months, not yet saying 3+ words or walking alone",
    ),
    SampleProfile(
        name="Expecting parent",
        age_months=-3,
        expected_domains=("Sensory",),
        concerns=("Sensory",),
        note="Due in about 3 months, Sensory concern (prenatal activities only)",
    ),
)


def create_child(sample, caregiver, today=None):
    """Create the sample's child and milestone observations (caller rolls back)."""
    today = today or timezone.localdate()
    # One extra day so the child has just passed age_months rather than
    # falling a fraction short of it (10 months, not 9.99).
    date_of_birth = today - datetime.timedelta(
        days=round(sample.age_months * AVERAGE_DAYS_PER_MONTH) + 1
    )
    child = ChildProfile.objects.create(
        caregiver=caregiver,
        name=sample.name,
        date_of_birth=date_of_birth,
        concerns=list(sample.concerns),
        interests=list(sample.interests),
    )
    for key in sample.not_yet:
        child.record_milestone(
            reference=ReferenceMilestone.objects.get(milestone_key=key),
            status="not_yet",
            observation_date=today,
        )
    return child


SAMPLES_BY_KEY = {sample.key: sample for sample in SAMPLE_PROFILES}
