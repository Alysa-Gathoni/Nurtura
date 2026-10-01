"""Tests for the rule engine core (#17), using sample rules.

The guideline rule set and its scenario tests come in #18 and #19.
"""

import datetime
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from activities.choices import Domain

from .models import ChildProfile, DevelopmentalMilestone
from .rules import (
    DOMAINS,
    Rule,
    RuleEngine,
    age_in_months,
    build_profile,
    milestone_facts,
)


@dataclass(frozen=True)
class SampleFact:
    domain: str
    flagged: bool = True


def boost_rule(name="sample-boost", amount=3.0):
    """Sample rule: IF a fact is flagged THEN raise its domain by amount."""
    return Rule(
        name=name,
        source="Test fixture",
        condition=lambda fact: fact.flagged,
        effect=lambda fact: {fact.domain: amount},
        reason=lambda fact: f"{fact.domain} flagged",
    )


class RuleEngineTests(SimpleTestCase):
    def test_no_evidence_gives_equal_priority(self):
        profile = RuleEngine([boost_rule()]).evaluate([])
        self.assertEqual(profile.scores, {d: 1.0 for d in DOMAINS})
        self.assertEqual(profile.ranked_domains(), list(DOMAINS))
        self.assertEqual(profile.firings, ())

    def test_fired_rule_raises_its_domain_to_top(self):
        profile = RuleEngine([boost_rule()]).evaluate([SampleFact(Domain.LANGUAGE)])
        self.assertEqual(profile.top_domain, "Language")
        self.assertEqual(profile.scores["Language"], 1.0)
        # baseline 1 / (1 + 3) for the domains with no evidence
        self.assertAlmostEqual(profile.scores["Motor"], 0.25)

    def test_scores_cover_all_domains_and_stay_in_range(self):
        facts = [
            SampleFact(d) for d in (Domain.LANGUAGE, Domain.LANGUAGE, Domain.MOTOR)
        ]
        profile = RuleEngine([boost_rule()]).evaluate(facts)
        self.assertEqual(set(profile.scores), set(DOMAINS))
        for score in profile.scores.values():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
        self.assertEqual(profile.ranked_domains()[:2], ["Language", "Motor"])
        self.assertAlmostEqual(profile.scores["Motor"], 4 / 7)

    def test_non_matching_facts_do_not_fire(self):
        profile = RuleEngine([boost_rule()]).evaluate(
            [SampleFact(Domain.LANGUAGE, flagged=False)]
        )
        self.assertEqual(profile.firings, ())
        self.assertEqual(profile.scores, {d: 1.0 for d in DOMAINS})

    def test_negative_adjustments_floor_at_zero(self):
        profile = RuleEngine([boost_rule(amount=-5.0)]).evaluate(
            [SampleFact(Domain.SENSORY)]
        )
        self.assertEqual(profile.raw_scores["Sensory"], 0.0)
        self.assertEqual(profile.scores["Sensory"], 0.0)
        self.assertEqual(profile.scores["Motor"], 1.0)

    def test_firings_record_rule_source_and_reason(self):
        profile = RuleEngine([boost_rule()]).evaluate([SampleFact(Domain.COGNITIVE)])
        (firing,) = profile.firings
        self.assertEqual(firing.rule.source, "Test fixture")
        self.assertEqual(firing.adjustments, {"Cognitive": 3.0})
        self.assertEqual(profile.reasons_for(Domain.COGNITIVE), ["Cognitive flagged"])
        self.assertEqual(profile.reasons_for(Domain.MOTOR), [])

    def test_rules_can_adjust_several_domains(self):
        rule = Rule(
            name="sample-multi",
            source="Test fixture",
            condition=lambda fact: True,
            effect=lambda fact: {Domain.LANGUAGE: 2, Domain.SOCIO_EMOTIONAL: 1},
            reason=lambda fact: "multi",
        )
        profile = RuleEngine([rule]).evaluate([SampleFact(Domain.LANGUAGE)])
        self.assertEqual(profile.raw_scores["Language"], 3.0)
        self.assertEqual(profile.raw_scores["Socio-Emotional"], 2.0)

    def test_invalid_configuration_rejected(self):
        with self.assertRaises(ValueError):
            RuleEngine([boost_rule(), boost_rule()])
        with self.assertRaises(ValueError):
            RuleEngine([boost_rule()], baseline=0)
        with self.assertRaises(ValueError):
            RuleEngine([boost_rule()]).evaluate([SampleFact("Visual")])

    def test_to_dict(self):
        profile = RuleEngine([boost_rule()]).evaluate(
            [SampleFact(Domain.LANGUAGE)], age_months=14.26
        )
        data = profile.to_dict()
        self.assertEqual(data["age_months"], 14.3)
        self.assertEqual(data["scores"]["Motor"], 0.25)
        self.assertEqual(data["ranked_domains"][0], "Language")
        self.assertEqual(data["reasons"][0]["rule"], "sample-boost")


class FactTests(TestCase):
    def setUp(self):
        caregiver = get_user_model().objects.create_user(
            username="caregiver", password="x-test-pass"
        )
        self.child = ChildProfile.objects.create(
            caregiver=caregiver, name="Amani", date_of_birth=datetime.date(2025, 6, 1)
        )

    def record(self, description, status, day, domain=Domain.LANGUAGE):
        return self.child.record_milestone(
            domain=domain,
            description=description,
            status=status,
            observation_date=day,
        )

    def test_age_in_months(self):
        dob = datetime.date(2025, 6, 1)
        self.assertAlmostEqual(age_in_months(dob, datetime.date(2026, 6, 1)), 12, 1)
        self.assertLess(age_in_months(dob, datetime.date(2025, 3, 1)), 0)

    def test_latest_observation_per_milestone_is_used(self):
        self.record("Says first words", "not_yet", datetime.date(2026, 3, 1))
        self.record("  says FIRST words ", "emerging", datetime.date(2026, 5, 1))
        self.record("Waves bye-bye", "achieved", datetime.date(2026, 4, 1))
        facts = milestone_facts(self.child, on_date=datetime.date(2026, 6, 1))
        by_description = {f.description.strip().lower(): f for f in facts}
        self.assertEqual(len(facts), 2)
        self.assertEqual(by_description["says first words"].status, "emerging")
        self.assertIsNone(by_description["says first words"].expected_age_months)

    def test_future_observations_ignored(self):
        self.record("Says first words", "not_yet", datetime.date(2026, 3, 1))
        self.record("Says first words", "achieved", datetime.date(2026, 9, 1))
        (fact,) = milestone_facts(self.child, on_date=datetime.date(2026, 6, 1))
        self.assertEqual(fact.status, "not_yet")

    def test_fact_ages(self):
        self.record("Says first words", "not_yet", datetime.date(2026, 3, 1))
        (fact,) = milestone_facts(self.child, on_date=datetime.date(2026, 6, 1))
        self.assertAlmostEqual(fact.age_months, 12, 0)
        self.assertAlmostEqual(fact.age_at_observation_months, 9, 0)

    def test_build_profile_end_to_end(self):
        self.record("Says first words", "not_yet", datetime.date(2026, 5, 1))
        self.record("Rolls over", "achieved", datetime.date(2026, 5, 1), Domain.MOTOR)
        not_yet_rule = Rule(
            name="sample-not-yet",
            source="Test fixture",
            condition=lambda f: f.status == DevelopmentalMilestone.Status.NOT_YET,
            effect=lambda f: {f.domain: 2.0},
            reason=lambda f: f"Not yet: {f.description}",
        )
        profile = build_profile(
            self.child, rules=[not_yet_rule], on_date=datetime.date(2026, 6, 1)
        )
        self.assertEqual(profile.top_domain, "Language")
        self.assertEqual(profile.reasons_for("Language"), ["Not yet: Says first words"])
        self.assertAlmostEqual(profile.age_months, 12, 0)

    def test_build_profile_without_rules_or_milestones(self):
        prenatal = ChildProfile.objects.create(
            caregiver=self.child.caregiver,
            name="Baby",
            date_of_birth=datetime.date(2027, 3, 1),
        )
        profile = build_profile(prenatal, on_date=datetime.date(2026, 10, 1))
        self.assertEqual(profile.scores, {d: 1.0 for d in DOMAINS})
        self.assertLess(profile.age_months, 0)
