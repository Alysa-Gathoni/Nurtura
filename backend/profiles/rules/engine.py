"""Custom IF-THEN rule engine for developmental profiling (FR-05).

A rule reads: IF a fact matches the rule's condition THEN adjust the priority
of one or more developmental domains. The engine applies every rule to every
fact, adds the adjustments to a baseline score for each domain, and normalizes
the totals to 0-1 by dividing by the highest one, so the most urgent domain
scores 1.0. With no evidence every domain keeps the baseline and scores 1.0
(equal priority).

Each rule names the guideline it comes from and produces a caregiver-readable
reason when it fires, so every score can be traced and explained (Sprint 6).
"""

from dataclasses import dataclass
from typing import Any, Callable

from activities.choices import Domain

DOMAINS = tuple(Domain.values)


@dataclass(frozen=True)
class Rule:
    """IF condition(fact) THEN apply effect(fact) to the domain scores."""

    name: str
    source: str
    condition: Callable[[Any], bool]
    effect: Callable[[Any], dict]
    reason: Callable[[Any], str]

    def fire(self, fact):
        """Return a Firing if the rule applies to the fact, otherwise None."""
        if not self.condition(fact):
            return None
        adjustments = {str(domain): float(v) for domain, v in self.effect(fact).items()}
        unknown = set(adjustments) - set(DOMAINS)
        if unknown:
            raise ValueError(
                f"Rule {self.name!r} adjusts unknown domain(s): {sorted(unknown)}"
            )
        return Firing(
            rule=self, fact=fact, adjustments=adjustments, reason=self.reason(fact)
        )


@dataclass(frozen=True)
class Firing:
    """A record of one rule applying to one fact."""

    rule: Rule
    fact: Any
    adjustments: dict
    reason: str


@dataclass(frozen=True)
class DevelopmentalProfile:
    """Per-domain priority scores (0-1) and the rule firings behind them."""

    scores: dict
    raw_scores: dict
    firings: tuple
    age_months: float | None = None

    def ranked_domains(self):
        """Domains from highest to lowest priority; ties keep Domain order."""
        return sorted(DOMAINS, key=lambda d: (-self.scores[d], DOMAINS.index(d)))

    @property
    def top_domain(self):
        return self.ranked_domains()[0]

    def reasons_for(self, domain):
        return [f.reason for f in self.firings if str(domain) in f.adjustments]

    def to_dict(self):
        return {
            "age_months": (
                None if self.age_months is None else round(self.age_months, 1)
            ),
            "scores": {d: round(self.scores[d], 3) for d in DOMAINS},
            "ranked_domains": self.ranked_domains(),
            "reasons": [
                {
                    "rule": f.rule.name,
                    "source": f.rule.source,
                    "adjustments": f.adjustments,
                    "reason": f.reason,
                }
                for f in self.firings
            ],
        }


class RuleEngine:
    def __init__(self, rules, baseline=1.0):
        if baseline <= 0:
            raise ValueError("baseline must be positive")
        names = [rule.name for rule in rules]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"Duplicate rule name(s): {duplicates}")
        self.rules = tuple(rules)
        self.baseline = float(baseline)

    def evaluate(self, facts, age_months=None):
        raw = {domain: self.baseline for domain in DOMAINS}
        firings = []
        for fact in facts:
            for rule in self.rules:
                firing = rule.fire(fact)
                if firing is None:
                    continue
                firings.append(firing)
                for domain, delta in firing.adjustments.items():
                    raw[domain] += delta

        raw = {domain: max(0.0, score) for domain, score in raw.items()}
        top = max(raw.values())
        scores = {
            domain: (score / top if top else 0.0) for domain, score in raw.items()
        }
        return DevelopmentalProfile(
            scores=scores,
            raw_scores=raw,
            firings=tuple(firings),
            age_months=age_months,
        )
