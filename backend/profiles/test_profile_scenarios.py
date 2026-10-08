"""Scenario tests for DevelopmentalProfile scoring with the guideline rules (#19).

These run against the real guideline catalogue (loaded with seed_milestones)
and refer to milestones by key, so edits to milestone wording during
verification don't affect them. The first test is the Sprint 3 Definition of
done: a delayed language milestone weights Language highest.
"""

import datetime
import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from .models import ChildProfile, DevelopmentalMilestone, ReferenceMilestone
from .rules import DOMAINS, build_profile

Status = DevelopmentalMilestone.Status
DOB = datetime.date(2025, 1, 1)
OTHER_DOMAINS_12M_ACHIEVED = ("CDC-12M-SE-01", "CDC-12M-CO-01", "CDC-12M-MO-01")


def on_age(months, dob=DOB):
    """Evaluation date when a child born on dob is about this many months old."""
    return dob + datetime.timedelta(days=round(months * 30.4375) + 1)


class ProfileScenarioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_milestones", stdout=StringIO())
        cls.caregiver = get_user_model().objects.create_user(
            username="caregiver", password="x-test-pass"
        )

    def setUp(self):
        self.child = ChildProfile.objects.create(
            caregiver=self.caregiver, name="Amani", date_of_birth=DOB
        )

    def observe(self, key, status, months_old):
        self.child.record_milestone(
            reference=ReferenceMilestone.objects.get(milestone_key=key),
            status=status,
            observation_date=on_age(months_old),
        )

    def profile(self, months_old):
        return build_profile(self.child, on_date=on_age(months_old))

    def assertRanked(self, profile, leading):
        self.assertEqual(profile.ranked_domains()[: len(leading)], leading)

    # Sprint 3 Definition of done
    def test_delayed_language_milestone_weights_language_highest(self):
        for key in OTHER_DOMAINS_12M_ACHIEVED:
            self.observe(key, Status.ACHIEVED, 13)
        self.observe("CDC-12M-LA-01", Status.NOT_YET, 13)

        profile = self.profile(13)

        self.assertEqual(profile.top_domain, "Language")
        self.assertEqual(profile.scores["Language"], 1.0)
        for domain in DOMAINS:
            if domain != "Language":
                self.assertLess(profile.scores[domain], profile.scores["Language"])
                self.assertAlmostEqual(profile.scores[domain], 1 / 11)
        (reason,) = profile.reasons_for("Language")
        self.assertIn("most children do this by 12 months (CDC)", reason)

    def test_on_track_child_has_equal_priority(self):
        for key in OTHER_DOMAINS_12M_ACHIEVED + ("CDC-12M-LA-01",):
            self.observe(key, Status.ACHIEVED, 13)
        profile = self.profile(13)
        self.assertEqual(profile.scores, {d: 1.0 for d in DOMAINS})
        self.assertEqual(profile.firings, ())

    def test_more_delays_in_a_domain_rank_it_higher(self):
        self.observe("CDC-12M-LA-01", Status.NOT_YET, 13)
        self.observe("CDC-12M-LA-02", Status.NOT_YET, 13)
        self.observe("CDC-12M-MO-01", Status.NOT_YET, 13)
        profile = self.profile(13)
        self.assertRanked(profile, ["Language", "Motor"])
        self.assertAlmostEqual(profile.scores["Motor"], 11 / 21)
        self.assertAlmostEqual(profile.scores["Cognitive"], 1 / 21)

    def test_not_yet_outranks_emerging(self):
        self.observe("CDC-12M-LA-01", Status.NOT_YET, 13)
        self.observe("CDC-12M-CO-01", Status.EMERGING, 13)
        profile = self.profile(13)
        self.assertRanked(profile, ["Language", "Cognitive"])
        self.assertAlmostEqual(profile.scores["Cognitive"], 6 / 11)

    def test_upcoming_milestones_weigh_less_than_due_ones(self):
        # At 10.5 months the 12-month milestone is upcoming; the 9-month one is due.
        self.observe("CDC-12M-LA-01", Status.NOT_YET, 10.5)
        self.observe("CDC-09M-MO-04", Status.NOT_YET, 10.5)
        profile = self.profile(10.5)
        self.assertRanked(profile, ["Motor", "Language"])
        self.assertAlmostEqual(profile.scores["Language"], 3 / 11)
        self.assertTrue(profile.reasons_for("Language")[0].startswith("Coming up:"))

    def test_achieving_a_milestone_clears_its_priority(self):
        self.observe("CDC-12M-LA-01", Status.NOT_YET, 12.5)
        self.observe("CDC-12M-LA-01", Status.ACHIEVED, 13.5)
        self.assertEqual(self.profile(13).top_domain, "Language")
        self.assertEqual(self.profile(14).scores, {d: 1.0 for d in DOMAINS})

    def test_milestone_evidence_outweighs_a_single_concern(self):
        self.child.concerns = ["Motor"]
        self.child.save()
        self.observe("CDC-12M-LA-01", Status.NOT_YET, 13)
        profile = self.profile(13)
        self.assertRanked(profile, ["Language", "Motor"])
        self.assertAlmostEqual(profile.scores["Motor"], 6 / 11)

    def test_prenatal_profile_uses_caregiver_concerns(self):
        due_date = datetime.date(2027, 2, 1)
        expecting = ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Baby",
            date_of_birth=due_date,
            concerns=["Sensory"],
        )
        profile = build_profile(expecting, on_date=datetime.date(2026, 11, 1))
        self.assertLess(profile.age_months, 0)
        self.assertEqual(profile.top_domain, "Sensory")
        self.assertEqual(
            profile.reasons_for("Sensory"),
            ["You told us you'd like support with Sensory development."],
        )

    def test_sensory_interests_raise_sensory_for_on_track_child(self):
        self.child.interests = ["Sand play", "animals"]
        self.child.save()
        self.observe("CDC-12M-LA-01", Status.ACHIEVED, 13)
        profile = self.profile(13)
        self.assertEqual(profile.top_domain, "Sensory")
        self.assertAlmostEqual(profile.scores["Language"], 1 / 3)

    def test_who_motor_windows_and_crawling_exception(self):
        self.observe("WHO-MO-03", Status.NOT_YET, 18)
        self.assertEqual(self.profile(18).firings, ())
        self.observe("WHO-MO-06", Status.NOT_YET, 18)
        profile = self.profile(18)
        self.assertEqual(profile.top_domain, "Motor")
        (reason,) = profile.reasons_for("Motor")
        self.assertIn("almost all children do this by 17.6 months (WHO)", reason)

    def test_profile_output_is_serializable(self):
        self.observe("CDC-12M-LA-01", Status.NOT_YET, 13)
        data = json.loads(json.dumps(self.profile(13).to_dict()))
        self.assertEqual(len(data["ranked_domains"]), 5)
        self.assertEqual(data["ranked_domains"][0], "Language")
        self.assertEqual(data["scores"]["Language"], 1.0)
        self.assertEqual(data["scores"]["Motor"], round(1 / 11, 3))
        self.assertEqual(data["reasons"][0]["rule"], "due-milestone-not-yet")
        self.assertIn("ASQ-3", data["reasons"][0]["source"])
