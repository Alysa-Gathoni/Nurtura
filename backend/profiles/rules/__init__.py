"""Developmental profiling: a custom IF-THEN rule engine (FR-05).

build_profile(child) turns a child's recorded milestones into normalized 0-1
priority scores for the five developmental domains.
"""

from django.utils import timezone

from .engine import DOMAINS, DevelopmentalProfile, Firing, Rule, RuleEngine
from .facts import MilestoneFact, age_in_months, milestone_facts

__all__ = [
    "DOMAINS",
    "DevelopmentalProfile",
    "Firing",
    "MilestoneFact",
    "Rule",
    "RuleEngine",
    "age_in_months",
    "build_profile",
    "milestone_facts",
]


def build_profile(child, rules=(), on_date=None):
    """Evaluate rules over the child's milestone facts.

    The guideline rule set (#18) becomes the default once it is encoded; until
    then callers pass the rules to apply.
    """
    on_date = on_date or timezone.localdate()
    facts = milestone_facts(child, on_date)
    return RuleEngine(rules).evaluate(
        facts, age_months=age_in_months(child.date_of_birth, on_date)
    )
