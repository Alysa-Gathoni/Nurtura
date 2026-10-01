"""Tests for the guideline milestone catalogue and rules (#18).

Profile-level scenario tests (including the Sprint 3 Definition of done case)
are in #19.
"""

import datetime
import tempfile
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from activities.choices import Domain

from .models import ChildProfile, DevelopmentalMilestone, ReferenceMilestone
from .rules import GUIDELINE_RULES, RuleEngine, build_profile, child_facts
from .rules.guidelines import (
    CONCERN_WEIGHT,
    EMERGING_DEFICIT,
    NOT_YET_DEFICIT,
    SENSORY_INTEREST_WEIGHT,
    UPCOMING_WEIGHT,
)

Status = DevelopmentalMilestone.Status
DOB = datetime.date(2025, 1, 1)


def on_age(months):
    """Evaluation date when a child born on DOB is about this many months old."""
    return DOB + datetime.timedelta(days=round(months * 30.4375) + 1)


def reference(key, age, domain=Domain.LANGUAGE, source="CDC", description=None):
    return ReferenceMilestone.objects.create(
        milestone_key=key,
        source=source,
        expected_age_months=Decimal(str(age)),
        domain=domain,
        description=description or f"Milestone {key}",
        source_reference="Test reference",
    )


class GuidelineTestCase(TestCase):
    def setUp(self):
        caregiver = get_user_model().objects.create_user(
            username="caregiver", password="x-test-pass"
        )
        self.child = ChildProfile.objects.create(
            caregiver=caregiver, name="Amani", date_of_birth=DOB
        )

    def observe(self, ref, status, months_old):
        return self.child.record_milestone(
            reference=ref, status=status, observation_date=on_age(months_old)
        )

    def evaluate(self, months_old):
        return RuleEngine(GUIDELINE_RULES).evaluate(
            child_facts(self.child, on_age(months_old))
        )


class GuidelineRuleTests(GuidelineTestCase):
    def test_due_not_yet_adds_full_asq_deficit(self):
        ref = reference("CDC-12M-LA-01", 12, description='Waves "bye-bye"')
        self.observe(ref, Status.NOT_YET, 13)
        profile = self.evaluate(13)
        self.assertEqual(profile.raw_scores["Language"], 1 + NOT_YET_DEFICIT)
        self.assertEqual(profile.top_domain, "Language")
        self.assertEqual(
            profile.reasons_for("Language"),
            ['Not yet: “Waves "bye-bye"” — most children do this by 12 months (CDC).'],
        )

    def test_due_emerging_adds_half_deficit(self):
        self.observe(reference("CDC-12M-MO-01", 12, Domain.MOTOR), Status.EMERGING, 13)
        profile = self.evaluate(13)
        self.assertEqual(profile.raw_scores["Motor"], 1 + EMERGING_DEFICIT)
        self.assertEqual(profile.firings[0].rule.name, "due-milestone-emerging")

    def test_achieved_milestones_do_not_raise_priority(self):
        self.observe(reference("CDC-12M-LA-01", 12), Status.ACHIEVED, 13)
        self.assertEqual(self.evaluate(13).firings, ())

    def test_upcoming_milestone_gets_small_boost(self):
        ref = reference("CDC-15M-LA-01", 15)
        self.observe(ref, Status.NOT_YET, 13)
        profile = self.evaluate(13)
        self.assertEqual(profile.raw_scores["Language"], 1 + UPCOMING_WEIGHT)
        self.assertTrue(profile.reasons_for("Language")[0].startswith("Coming up:"))

    def test_milestones_far_ahead_are_ignored(self):
        self.observe(reference("CDC-24M-LA-01", 24), Status.NOT_YET, 13)
        self.assertEqual(self.evaluate(13).firings, ())

    def test_unlinked_milestones_have_no_due_date(self):
        self.child.record_milestone(
            domain=Domain.LANGUAGE,
            description="Says first words",
            status=Status.NOT_YET,
            observation_date=on_age(13),
        )
        self.assertEqual(self.evaluate(13).firings, ())

    def test_latest_observation_wins(self):
        ref = reference("CDC-12M-LA-01", 12)
        self.observe(ref, Status.NOT_YET, 12.5)
        self.observe(ref, Status.ACHIEVED, 13)
        self.assertEqual(self.evaluate(13).firings, ())

    def test_who_wording_and_crawling_exception(self):
        walking = reference(
            "WHO-MO-06", 17.6, Domain.MOTOR, "WHO", description="Walking alone"
        )
        crawling = reference(
            "WHO-MO-03",
            13.5,
            Domain.MOTOR,
            "WHO",
            description="Hands-and-knees crawling",
        )
        self.observe(walking, Status.NOT_YET, 18)
        self.observe(crawling, Status.NOT_YET, 18)
        profile = self.evaluate(18)
        self.assertEqual(
            profile.reasons_for("Motor"),
            [
                "Not yet: “Walking alone” — almost all children do this by "
                "17.6 months (WHO)."
            ],
        )

    def test_caregiver_concern_raises_sensory(self):
        self.child.concerns = ["Sensory"]
        self.child.save()
        profile = self.evaluate(13)
        self.assertEqual(profile.top_domain, "Sensory")
        self.assertEqual(profile.raw_scores["Sensory"], 1 + CONCERN_WEIGHT)

    def test_sensory_interests_raise_sensory(self):
        self.child.interests = ["Water play", "animals"]
        self.child.save()
        profile = self.evaluate(13)
        self.assertEqual(profile.raw_scores["Sensory"], 1 + SENSORY_INTEREST_WEIGHT)
        self.assertEqual(len(profile.firings), 1)
        self.assertIn("water play", profile.firings[0].reason)

    def test_build_profile_uses_guideline_rules_by_default(self):
        self.observe(reference("CDC-12M-LA-01", 12), Status.NOT_YET, 13)
        profile = build_profile(self.child, on_date=on_age(13))
        self.assertEqual(profile.top_domain, "Language")


class ReferenceLinkTests(GuidelineTestCase):
    def test_reference_fills_domain_and_description(self):
        ref = reference("CDC-12M-LA-01", 12, description='Waves "bye-bye"')
        milestone = self.observe(ref, Status.ACHIEVED, 12)
        self.assertEqual(milestone.domain, "Language")
        self.assertEqual(milestone.description, 'Waves "bye-bye"')

    def test_domain_must_match_reference(self):
        ref = reference("CDC-12M-LA-01", 12)
        with self.assertRaises(ValidationError) as ctx:
            self.child.record_milestone(
                reference=ref, domain=Domain.MOTOR, status=Status.NOT_YET
            )
        self.assertIn("domain", ctx.exception.message_dict)

    def test_concerns_validated(self):
        for bad in (["Visual"], ["Sensory", "Sensory"], "Sensory"):
            with self.subTest(concerns=bad):
                self.child.concerns = bad
                with self.assertRaises(ValidationError):
                    self.child.full_clean()


class ConcernsAPITests(APITestCase):
    def test_concerns_set_and_validated_through_api(self):
        caregiver = get_user_model().objects.create_user(
            username="wanjiru", password="x-test-pass"
        )
        self.client.force_authenticate(caregiver)
        url = reverse("child-list")
        data = {"name": "Amani", "date_of_birth": "2025-06-01"}
        response = self.client.post(
            url, {**data, "concerns": ["Sensory"]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["concerns"], ["Sensory"])
        response = self.client.post(
            url, {**data, "concerns": ["Visual"]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("concerns", response.data)


class SeedMilestonesTests(TestCase):
    def seed(self, *args):
        out = StringIO()
        call_command("seed_milestones", *args, stdout=out, stderr=StringIO())
        return out.getvalue()

    def test_loads_real_catalogue_unverified(self):
        self.assertIn("133 milestones: 133 created", self.seed())
        self.assertEqual(ReferenceMilestone.objects.count(), 133)
        self.assertFalse(ReferenceMilestone.objects.filter(verified=True).exists())
        self.assertEqual(
            set(ReferenceMilestone.objects.values_list("domain", flat=True)),
            {"Socio-Emotional", "Language", "Cognitive", "Motor"},
        )
        walking = ReferenceMilestone.objects.get(milestone_key="WHO-MO-06")
        self.assertEqual(walking.expected_age_months, Decimal("17.6"))

    def test_reseed_keeps_verified_unless_content_changes(self):
        self.seed()
        ReferenceMilestone.objects.update(verified=True)
        self.assertIn("133 unchanged", self.seed())
        self.assertEqual(ReferenceMilestone.objects.filter(verified=True).count(), 133)

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        from .management.commands.seed_milestones import DEFAULT_FILE

        changed = Path(tmp.name) / "milestones.csv"
        text = DEFAULT_FILE.read_text(encoding="utf-8")
        changed.write_text(
            text.replace("Walking alone", "Walks alone"), encoding="utf-8"
        )
        output = self.seed("--file", str(changed))
        self.assertIn("1 marked unverified", output)
        walking = ReferenceMilestone.objects.get(milestone_key="WHO-MO-06")
        self.assertFalse(walking.verified)
        self.assertEqual(walking.description, "Walks alone")

    def test_invalid_row_means_nothing_is_written(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        bad = Path(tmp.name) / "bad.csv"
        bad.write_text(
            "milestone_key,source,expected_age_months,domain,description,"
            "source_reference,notes\n"
            "CDC-12M-LA-01,CDC,12,Language,Waves,Ref,\n"
            "CDC-12M-XX-01,CDC,twelve,Language,Bad age,Ref,\n",
            encoding="utf-8",
        )
        with self.assertRaisesMessage(CommandError, "nothing was written"):
            self.seed("--file", str(bad))
        self.assertFalse(ReferenceMilestone.objects.exists())

    def test_dry_run_saves_nothing(self):
        self.assertIn("dry run - nothing saved", self.seed("--dry-run"))
        self.assertFalse(ReferenceMilestone.objects.exists())


class ReferenceMilestoneAdminTests(TestCase):
    def test_administrators_mark_milestones_verified(self):
        User = get_user_model()
        reference("CDC-12M-LA-01", 12)
        url = reverse("admin:profiles_referencemilestone_changelist")

        caregiver = User.objects.create_user(username="wanjiru", password="x-test-pass")
        self.client.force_login(caregiver)
        self.assertEqual(self.client.get(url).status_code, 302)

        admin = User.objects.create_user(
            username="admin", password="x-test-pass", role=User.Role.ADMINISTRATOR
        )
        self.client.force_login(admin)
        self.assertEqual(self.client.get(url).status_code, 200)
        ref = ReferenceMilestone.objects.get()
        self.client.post(url, {"action": "mark_verified", "_selected_action": [ref.pk]})
        ref.refresh_from_db()
        self.assertTrue(ref.verified)
