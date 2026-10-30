"""Tests for the clinic-visit referral (#161)."""

from activities.choices import Domain

from .rules import GUIDELINE_RULES
from .rules.referral import REFERRAL_MIN_NOT_YET, SOURCE, referral_for
from .test_guidelines import GuidelineTestCase, Status, on_age, reference


class ReferralTests(GuidelineTestCase):
    def referral(self, months_old):
        return referral_for(self.child, on_age(months_old))

    def test_threshold_follows_cdc_one_or_more(self):
        self.assertEqual(REFERRAL_MIN_NOT_YET, 1)

    def test_no_milestones_no_referral(self):
        self.assertIsNone(self.referral(13))

    def test_one_due_not_yet_gives_referral(self):
        ref = reference("CDC-12M-LA-01", 12, description='Waves "bye-bye"')
        self.observe(ref, Status.NOT_YET, 13)
        referral = self.referral(13)
        self.assertIsNotNone(referral)
        self.assertIn("something", referral.message)
        self.assertIn("Amani's age", referral.message)
        self.assertIn("next clinic visit", referral.message)
        self.assertEqual(
            referral.to_dict(),
            {
                "message": referral.message,
                "source": SOURCE,
                "milestones": [
                    {
                        "description": 'Waves "bye-bye"',
                        "domain": "Language",
                        "expected_age_months": 12.0,
                        "source": "CDC",
                    }
                ],
            },
        )

    def test_wording_is_gentle_and_not_diagnostic(self):
        self.observe(reference("CDC-12M-LA-01", 12), Status.NOT_YET, 13)
        message = self.referral(13).message.lower()
        self.assertIn("own pace", message)
        for word in ("delay", "diagnos", "disorder", "risk", "worry", "fail"):
            self.assertNotIn(word, message)

    def test_several_listed_earliest_first(self):
        self.observe(reference("CDC-12M-MO-01", 12, Domain.MOTOR), Status.NOT_YET, 13)
        self.observe(reference("CDC-09M-LA-01", 9), Status.NOT_YET, 13)
        referral = self.referral(13)
        self.assertIn("a few things", referral.message)
        self.assertEqual(
            [m["expected_age_months"] for m in referral.to_dict()["milestones"]],
            [9.0, 12.0],
        )

    def test_not_yet_before_expected_age_does_not_count(self):
        self.observe(reference("CDC-15M-LA-01", 15), Status.NOT_YET, 13)
        self.assertIsNone(self.referral(13))

    def test_emerging_does_not_count(self):
        self.observe(reference("CDC-12M-LA-01", 12), Status.EMERGING, 13)
        self.assertIsNone(self.referral(13))

    def test_latest_observation_wins(self):
        ref = reference("CDC-12M-LA-01", 12)
        self.observe(ref, Status.NOT_YET, 12.5)
        self.observe(ref, Status.ACHIEVED, 13)
        self.assertIsNone(self.referral(13))

    def test_crawling_is_not_a_delay_signal(self):
        ref = reference("WHO-MO-03", 13.5, Domain.MOTOR, source="WHO")
        self.observe(ref, Status.NOT_YET, 14)
        self.assertIsNone(self.referral(14))

    def test_free_text_milestones_do_not_count(self):
        self.child.record_milestone(
            domain=Domain.LANGUAGE,
            description="Sings along",
            status=Status.NOT_YET,
            observation_date=on_age(13),
        )
        self.assertIsNone(self.referral(13))

    def test_referral_is_not_a_scoring_rule(self):
        # Kept out of the rules, so priorities, ranking and the evaluation's
        # rule weights are unchanged.
        self.assertNotIn("referral", " ".join(r.name for r in GUIDELINE_RULES))
