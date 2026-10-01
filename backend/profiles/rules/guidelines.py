"""Guideline rules for developmental profiling (#18).

Expected ages come from the ReferenceMilestone catalogue
(data/reference/developmental_milestones.csv):
- CDC "Learn the Signs. Act Early." checklists, 2022 revision: milestones most
  children (75% or more) reach by each age from 2 to 36 months.
- WHO Motor Development Study (2006): windows of achievement for six gross
  motor milestones; the expected age is the window end (99th percentile).

Weights follow the ASQ-3 scoring convention, which the milestone statuses
mirror: Yes / Sometimes / Not yet score 10 / 5 / 0 points, so the deficit for a
due milestone is 0 (Achieved), 5 (Emerging) or 10 (Not yet). ASQ-3 items are
copyrighted and are not reproduced; only the scoring convention is used.

None of these frameworks has a Sensory domain, so Sensory priority comes from
caregiver-reported concerns and sensory interests instead of milestone due
dates.
"""

from activities.choices import Domain

from ..models import DevelopmentalMilestone
from .engine import Rule
from .facts import ConcernFact, InterestFact, MilestoneFact

Status = DevelopmentalMilestone.Status

# ASQ-3 deficits (10 points per item, minus the item score).
NOT_YET_DEFICIT = 10.0
EMERGING_DEFICIT = 5.0

# Milestones expected within this many months get a smaller boost, so
# activities can support skills that are about to emerge.
UPCOMING_WINDOW_MONTHS = 3.0
UPCOMING_WEIGHT = 2.0

# A caregiver concern counts like an Emerging (half-achieved) milestone.
CONCERN_WEIGHT = EMERGING_DEFICIT

# Interests that point to sensory play raise Sensory a little.
SENSORY_INTEREST_WEIGHT = 2.0
SENSORY_INTEREST_KEYWORDS = (
    "sensory",
    "texture",
    "touch",
    "water",
    "sand",
    "messy play",
    "music",
    "sound",
    "light",
)

# WHO found that some healthy children never crawl on hands and knees, so not
# crawling on its own is not treated as a delay.
NOT_A_DELAY_SIGNAL = {"WHO-MO-03"}

SOURCE_WORDING = {
    "CDC": "most children do this by {age} months (CDC)",
    "WHO": "almost all children do this by {age} months (WHO)",
}


def _format_age(months):
    return f"{months:g}"


def _expected_by(fact):
    template = SOURCE_WORDING.get(fact.source, "expected by {age} months")
    return template.format(age=_format_age(fact.expected_age_months))


def _is_milestone_with_due_age(fact):
    return (
        isinstance(fact, MilestoneFact)
        and fact.expected_age_months is not None
        and fact.reference_key not in NOT_A_DELAY_SIGNAL
    )


def _is_due(fact):
    return (
        _is_milestone_with_due_age(fact) and fact.age_months >= fact.expected_age_months
    )


def _is_upcoming(fact):
    return (
        _is_milestone_with_due_age(fact)
        and fact.expected_age_months - UPCOMING_WINDOW_MONTHS
        <= fact.age_months
        < fact.expected_age_months
    )


DUE_NOT_YET = Rule(
    name="due-milestone-not-yet",
    source="CDC 2022 checklist / WHO 2006 motor windows (expected age); "
    "ASQ-3 scoring convention (Not yet = 0 of 10 points)",
    condition=lambda f: _is_due(f) and f.status == Status.NOT_YET,
    effect=lambda f: {f.domain: NOT_YET_DEFICIT},
    reason=lambda f: f"Not yet: “{f.description}” — {_expected_by(f)}.",
)

DUE_EMERGING = Rule(
    name="due-milestone-emerging",
    source="CDC 2022 checklist / WHO 2006 motor windows (expected age); "
    "ASQ-3 scoring convention (Sometimes = 5 of 10 points)",
    condition=lambda f: _is_due(f) and f.status == Status.EMERGING,
    effect=lambda f: {f.domain: EMERGING_DEFICIT},
    reason=lambda f: f"Still emerging: “{f.description}” — {_expected_by(f)}.",
)

UPCOMING = Rule(
    name="upcoming-milestone",
    source="CDC 2022 checklist / WHO 2006 motor windows (expected age)",
    condition=lambda f: _is_upcoming(f) and f.status != Status.ACHIEVED,
    effect=lambda f: {f.domain: UPCOMING_WEIGHT},
    reason=lambda f: f"Coming up: “{f.description}” — {_expected_by(f)}.",
)

CAREGIVER_CONCERN = Rule(
    name="caregiver-concern",
    source="Caregiver-reported concern",
    condition=lambda f: isinstance(f, ConcernFact),
    effect=lambda f: {f.domain: CONCERN_WEIGHT},
    reason=lambda f: f"You told us you'd like support with {f.domain} development.",
)

SENSORY_INTEREST = Rule(
    name="sensory-interest",
    source="Caregiver-reported interest",
    condition=lambda f: isinstance(f, InterestFact)
    and any(keyword in f.interest for keyword in SENSORY_INTEREST_KEYWORDS),
    effect=lambda f: {Domain.SENSORY: SENSORY_INTEREST_WEIGHT},
    reason=lambda f: f"Enjoys “{f.interest}”, which sensory activities build on.",
)

GUIDELINE_RULES = (
    DUE_NOT_YET,
    DUE_EMERGING,
    UPCOMING,
    CAREGIVER_CONCERN,
    SENSORY_INTEREST,
)
