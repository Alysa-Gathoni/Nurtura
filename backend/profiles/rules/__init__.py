"""Developmental profiling: a custom IF-THEN rule engine (FR-05).

build_profile(child) turns a child's recorded milestones, caregiver concerns
and interests into normalized 0-1 priority scores for the five developmental
domains, using the guideline rules in guidelines.py.
"""

from django.utils import timezone

from .engine import DOMAINS, DevelopmentalProfile, Firing, Rule, RuleEngine
from .facts import (
    ConcernFact,
    InterestFact,
    MilestoneFact,
    age_in_months,
    child_facts,
    milestone_facts,
)
from .guidelines import GUIDELINE_RULES

__all__ = [
    "DOMAINS",
    "GUIDELINE_RULES",
    "ConcernFact",
    "DevelopmentalProfile",
    "Firing",
    "InterestFact",
    "MilestoneFact",
    "Rule",
    "RuleEngine",
    "age_in_months",
    "build_profile",
    "child_facts",
    "milestone_facts",
]


def build_profile(child, rules=GUIDELINE_RULES, on_date=None):
    """Evaluate rules (the guideline rules by default) over the child's facts."""
    on_date = on_date or timezone.localdate()
    return RuleEngine(rules).evaluate(
        child_facts(child, on_date),
        age_months=age_in_months(child.date_of_birth, on_date),
    )
