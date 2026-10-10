"""Tests for caregiver-readable explanations (FR-11, #69)."""

import datetime
import re
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from activities.choices import AgeRange, ContentStatus, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from profiles.models import ChildProfile, ReferenceMilestone

from . import embeddings, heldout
from .explanations import (
    AREA,
    EXPLANATION_VERSION,
    MAX_SENTENCES,
    SUPPORT,
    explain,
    used_interests,
)
from .models import Recommendation
from .ranking import rank
from .test_embeddings import FakeEncoder
from .test_recommendations_api import EXTRA_ACTIVITIES
from .test_spot_check import DOMAIN_ACTIVITIES

User = get_user_model()

# Words that would turn an explanation into a judgement or a diagnosis.
BANNED = re.compile(
    r"\b(delay|delayed|behind|deficit|disorder|abnormal|normal|at risk|fail|"
    r"failing|diagnos\w*|problem(?!-solving)|worry|worrying|concern\w*|should|"
    r"lagging|slow|score|priority|similarity|rank\w*)\b",
    re.I,
)
SUPPORT_TO_DOMAIN = {phrase: domain for domain, phrase in SUPPORT.items()}


def months_old(months):
    return timezone.localdate() - datetime.timedelta(
        days=round(months * 365.25 / 12) + 1
    )


def named_in(text):
    """What an explanation names, read back from its text alone."""
    milestones = [
        m.replace("‘", '"').replace("’", '"') for m in re.findall(r"“(.*?)”", text)
    ]
    concerns = [
        SUPPORT_TO_DOMAIN[m]
        for m in re.findall(r"like support with (.+?)(?: and that|\.|,)", text)
    ]
    interests = []
    for phrase in re.findall(
        r"(?:enjoys|activity uses|It uses) (.+?)(?:, which|;|\.|,)", text
    ):
        interests.extend(p.strip() for p in phrase.split(" and "))
    return milestones, concerns, interests


class ExplanationTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_milestones", stdout=StringIO())

    def setUp(self):
        embeddings.set_encoder(FakeEncoder())
        self.addCleanup(embeddings.set_encoder, None)
        for fields in DOMAIN_ACTIVITIES + EXTRA_ACTIVITIES:
            DevelopmentalActivity.objects.create(
                **activity_fields(content_status=ContentStatus.PUBLISHED, **fields)
            )
        call_command("embed_activities", stdout=StringIO())
        self.caregiver = User.objects.create_user(username="caregiver@example.com")

    def child(self, months, observations=(), **fields):
        child = ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Kim",
            date_of_birth=months_old(months),
            **fields,
        )
        for key, status_value in observations:
            child.record_milestone(
                reference=ReferenceMilestone.objects.get(milestone_key=key),
                status=status_value,
                observation_date=timezone.localdate(),
            )
        return child

    def explain_activity(self, child, activity_id):
        result = rank(child)
        ranked = next(r for r in result.ranked if r.activity.activity_id == activity_id)
        return explain(child, result.evaluation, ranked)

    def all_children(self):
        """Every held-out child plus profiles that exercise each path."""
        children = [
            heldout.create_child(c, self.caregiver) for c in heldout.HELDOUT_CHILDREN
        ]
        children += [
            self.child(
                13,
                [("WHO-MO-02", "not_yet"), ("CDC-12M-MO-01", "not_yet")],
                concerns=["Motor"],
                interests=["blocks", "music"],
            ),
            self.child(
                14,
                [
                    ("CDC-12M-LA-01", "not_yet"),
                    ("CDC-12M-LA-02", "not_yet"),
                    ("CDC-12M-LA-03", "not_yet"),
                    ("CDC-09M-LA-01", "not_yet"),
                    ("CDC-15M-LA-01", "emerging"),
                ],
                concerns=["Language"],
                interests=["books", "singing"],
            ),
            self.child(8, concerns=["Sensory"], interests=["water play", "textures"]),
        ]
        return children


class WordingTests(ExplanationTestCase):
    def test_cdc_not_yet_is_one_sentence(self):
        child = self.child(2.5, [("CDC-02M-MO-01", "not_yet")])
        e = self.explain_activity(child, "ACT-0962")  # Motor, 3-6 months
        self.assertEqual(
            e.sentences[0],
            "You recorded “Holds head up when on tummy” as not yet; most "
            "children do this by 2 months.",
        )
        self.assertIn("slightly older children (3–6 months)", e.text)

    def test_who_wording_rounds_up_and_mixed_sources(self):
        child = self.child(13, [("WHO-MO-02", "not_yet"), ("CDC-12M-MO-01", "not_yet")])
        e = self.explain_activity(child, "ACT-0952")  # Motor, 12-18 months
        self.assertEqual(
            e.sentences[0],
            "You recorded “Standing with assistance” and “Pulls up to "
            "stand” as not yet; almost all children do “Standing with "
            "assistance” by about 12 months, and most do “Pulls up to "
            "stand” by 12 months.",
        )

    def test_who_alone(self):
        child = self.child(13, [("WHO-MO-02", "not_yet")])
        e = self.explain_activity(child, "ACT-0952")
        self.assertEqual(
            e.sentences[0],
            "You recorded “Standing with assistance” as not yet; almost all "
            "children do this by about 12 months.",
        )

    def test_same_status_milestones_share_one_sentence_capped_at_three(self):
        child = self.child(
            14,
            [
                ("CDC-12M-LA-01", "not_yet"),
                ("CDC-12M-LA-02", "not_yet"),
                ("CDC-12M-LA-03", "not_yet"),
                ("CDC-09M-LA-01", "not_yet"),
            ],
        )
        e = self.explain_activity(child, "ACT-0951")
        first = e.sentences[0]
        lead = first.split(";")[0]
        self.assertTrue(lead.startswith("You recorded “"))
        self.assertTrue(lead.endswith("and 1 more you recorded as not yet"))
        self.assertEqual(lead.count("“"), 3)

    def test_inner_quotes_become_single_quotes(self):
        child = self.child(14, [("CDC-12M-LA-01", "not_yet")])
        e = self.explain_activity(child, "ACT-0951")
        self.assertIn("“Waves ‘bye-bye’”", e.text)

    def test_two_groups_not_yet_first(self):
        child = self.child(
            16,
            [("CDC-15M-LA-01", "emerging"), ("CDC-12M-LA-01", "not_yet")],
        )
        e = self.explain_activity(child, "ACT-0951")  # Language, 6-12 months
        self.assertRegex(e.sentences[0], r"as not yet; most children do this by 12")
        self.assertRegex(
            e.sentences[1], r"as just starting; most children do this by 15"
        )
        self.assertLessEqual(len(e.sentences), MAX_SENTENCES)

    def test_at_most_two_groups(self):
        child = self.child(
            16,
            [
                ("CDC-12M-LA-01", "not_yet"),
                ("CDC-15M-LA-01", "emerging"),
                ("CDC-18M-LA-01", "not_yet"),  # upcoming at 16 months
            ],
        )
        e = self.explain_activity(child, "ACT-0951")
        self.assertNotIn("often comes next", e.text)
        self.assertIn("just starting", e.text)

    def test_ages_name_only_the_milestones_shown(self):
        child = self.child(
            14,
            [
                ("CDC-09M-LA-01", "not_yet"),
                ("CDC-12M-LA-01", "not_yet"),
                ("CDC-12M-LA-02", "not_yet"),
                ("CDC-12M-LA-03", "not_yet"),
            ],
        )
        lead, ages = (
            self.explain_activity(child, "ACT-0951").sentences[0].split("; ", 1)
        )
        shown = set(re.findall(r"“(.*?)”", lead))
        aged = set(re.findall(r"“(.*?)”", ages))
        self.assertLessEqual(aged, shown)

    def test_concern_and_interest_merge_with_literal_use(self):
        child = self.child(
            8, concerns=["Sensory"], interests=["water play", "textures"]
        )
        e = self.explain_activity(child, "ACT-0955")  # Textures and Water Play
        self.assertEqual(
            e.sentences[0],
            "You said you'd like support with sensory development and that your "
            "child enjoys water play and textures, which points us towards "
            "activities for the senses; this activity uses water play and textures.",
        )

    def test_stand_alone_use_of_a_non_sensory_interest(self):
        child = self.child(9, interests=["books"])
        e = self.explain_activity(child, "ACT-0951")  # mentions picture books
        self.assertIn("It uses books, which you said your child enjoys.", e.text)

    def test_fallback_for_a_child_with_no_requests(self):
        child = self.child(9)
        e = self.explain_activity(child, "ACT-0953")
        self.assertEqual(
            e.sentences[0],
            "You haven't asked for help with a particular area, so this is a general "
            "activity for your child's age.",
        )

    def test_fallback_for_an_area_outside_the_childs_requests(self):
        child = self.child(9, concerns=["Language"])
        e = self.explain_activity(child, "ACT-0953")  # Cognitive
        self.assertEqual(
            e.sentences[0],
            "This one is a good fit for your child's age and supports thinking and "
            "problem-solving.",
        )

    def test_prenatal(self):
        child = self.child(-3, concerns=["Sensory"])
        e = self.explain_activity(child, "ACT-0956")
        self.assertIn("It's an activity for parents during pregnancy.", e.text)

    def test_aim_sentence_only_with_plain_aim(self):
        child = self.child(9)
        self.assertNotIn("Its aim is to", self.explain_activity(child, "ACT-0953").text)
        DevelopmentalActivity.objects.filter(activity_id="ACT-0953").update(
            plain_aim="help your baby learn that hidden things are still there"
        )
        self.assertTrue(
            self.explain_activity(child, "ACT-0953").text.endswith(
                "Its aim is to help your baby learn that hidden things are still there."
            )
        )

    def test_cap_drops_uses_then_plain_age_keeps_first_reason_and_aim(self):
        DevelopmentalActivity.objects.filter(activity_id="ACT-0951").update(
            plain_aim="help your child talk and listen"
        )
        # Two groups + support + uses + age + aim = 6 sentences before the cap.
        child = self.child(
            8,
            [("CDC-06M-LA-01", "not_yet"), ("CDC-06M-LA-02", "emerging")],
            concerns=["Language"],
            interests=["books"],
        )
        e = self.explain_activity(child, "ACT-0951")  # Language, 6-12 months
        self.assertEqual(len(e.sentences), MAX_SENTENCES)
        self.assertNotIn("It uses books", e.text)  # dropped first
        self.assertNotIn("your child's age group", e.text)  # plain age, second
        self.assertTrue(e.sentences[0].startswith("You recorded"))  # first reason
        self.assertTrue(e.sentences[-1].startswith("Its aim is to"))  # aim kept
        self.assertIn("You said you'd like support with", e.text)

    def test_cap_keeps_a_non_plain_age_and_drops_support_instead(self):
        DevelopmentalActivity.objects.filter(activity_id="ACT-0961").update(
            plain_aim="help your baby enjoy taking turns with sounds"
        )
        child = self.child(
            8,
            [("CDC-06M-LA-01", "not_yet"), ("CDC-06M-LA-02", "emerging")],
            concerns=["Language"],
        )
        e = self.explain_activity(child, "ACT-0961")  # Language, 3-6 months
        self.assertEqual(len(e.sentences), MAX_SENTENCES)
        self.assertIn("slightly younger children (3–6 months)", e.text)
        self.assertNotIn("like support with", e.text)
        self.assertTrue(e.sentences[-1].startswith("Its aim is to"))

    def test_support_is_kept_when_it_is_the_first_reason(self):
        DevelopmentalActivity.objects.filter(activity_id="ACT-0955").update(
            plain_aim="help your baby explore textures"
        )
        child = self.child(8, concerns=["Sensory"], interests=["textures", "books"])
        e = self.explain_activity(child, "ACT-0955")
        self.assertTrue(e.sentences[0].startswith("You said you'd like support"))
        self.assertLessEqual(len(e.sentences), MAX_SENTENCES)

    def test_used_interests_matches_whole_words_only(self):
        activity = DevelopmentalActivity.objects.get(activity_id="ACT-0955")
        self.assertEqual(
            used_interests(["Textures", "water play", "sand", "tex"], activity),
            ["textures", "water play"],
        )


class EveryExplanationTests(ExplanationTestCase):
    def test_named_items_exist_in_the_childs_stored_profile(self):
        """Every milestone, concern and interest an explanation names is the child's."""
        checked = 0
        for child in self.all_children():
            stored_milestones = set(
                child.milestones.values_list("description", flat=True)
            )
            stored_interests = {
                " ".join(str(i).lower().split()) for i in child.interests
            }
            result = rank(child)
            for ranked in result.ranked[:5]:
                e = explain(child, result.evaluation, ranked)
                milestones, concerns, interests = named_in(e.text)
                with self.subTest(child=child.pk, activity=ranked.activity.activity_id):
                    self.assertLessEqual(set(milestones), stored_milestones)
                    self.assertLessEqual(set(concerns), set(child.concerns))
                    self.assertLessEqual(set(interests), stored_interests)
                    # The parser and the generator agree on what was named.
                    self.assertEqual(set(milestones), set(e.milestones))
                    self.assertEqual(set(concerns), set(e.concerns))
                    self.assertEqual(sorted(set(interests)), sorted(set(e.interests)))
                checked += 1
        self.assertGreaterEqual(checked, 100)

    def test_no_judgemental_or_technical_words_and_at_most_four_sentences(self):
        for child in self.all_children():
            result = rank(child)
            for ranked in result.ranked[:5]:
                e = explain(child, result.evaluation, ranked)
                with self.subTest(child=child.pk, activity=ranked.activity.activity_id):
                    self.assertIsNone(BANNED.search(e.text), e.text)
                    self.assertLessEqual(len(e.sentences), MAX_SENTENCES)
                    self.assertTrue(e.text.endswith("."))


class StoredExplanationTests(ExplanationTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.caregiver)
        self.kid = heldout.create_child(heldout.HELDOUT_BY_ID["H03"], self.caregiver)
        self.url = reverse("child-recommendations", args=[self.kid.pk])

    def test_post_stores_explanations_with_their_version(self):
        cards = self.client.post(self.url).json()["recommendations"]
        result = rank(self.kid)
        for card, ranked in zip(cards, result.ranked):
            self.assertEqual(
                card["explanation"], explain(self.kid, result.evaluation, ranked).text
            )
        self.assertEqual(
            set(Recommendation.objects.values_list("explanation_version", flat=True)),
            {EXPLANATION_VERSION},
        )

    def test_batches_without_explanations_are_kept_and_superseded(self):
        first = self.client.post(self.url).json()
        Recommendation.objects.update(explanation="", explanation_version="")
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response.json()["batch"], first["batch"])
        old = Recommendation.objects.filter(batch=first["batch"])
        self.assertEqual(old.count(), 5)
        self.assertEqual(set(old.values_list("explanation", flat=True)), {""})

    def test_a_new_plain_aim_gives_a_new_batch(self):
        first = self.client.post(self.url).json()
        self.assertEqual(self.client.post(self.url).status_code, status.HTTP_200_OK)
        top = first["recommendations"][0]["activity_id"]
        DevelopmentalActivity.objects.filter(activity_id=top).update(
            plain_aim="help your baby grow stronger"
        )
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            response.json()["recommendations"][0]["explanation"].endswith(
                "Its aim is to help your baby grow stronger."
            )
        )
        self.assertEqual(Recommendation.objects.count(), 10)


class AreaWordsTests(APITestCase):
    def test_every_domain_has_plain_words(self):
        self.assertEqual(set(AREA), {d.value for d in Domain})
        self.assertEqual(set(SUPPORT), {d.value for d in Domain})
        self.assertEqual(SUPPORT["Sensory"], "sensory development")
        self.assertIn(AgeRange.PRENATAL, AgeRange.values)


class ExplanationSamplesCommandTests(ExplanationTestCase):
    def test_prints_scenarios_and_explanations_without_storing(self):
        out = StringIO()
        call_command("explanation_samples", "--markdown", stdout=out)
        text = out.getvalue()
        self.assertEqual(text.count("**Your child:**"), 10)
        self.assertEqual(text.count("\n> "), 10)
        self.assertIn("Your child is 2½ months old.", text)
        self.assertNotIn("most babies", text)  # the scenario mustn't give it away
        self.assertNotIn("H03", text)  # no internal IDs in the reader version
        self.assertFalse(Recommendation.objects.exists())
        self.assertFalse(
            ChildProfile.objects.exclude(caregiver=self.caregiver).exists()
        )

    def test_unknown_child(self):
        with self.assertRaisesMessage(Exception, "Unknown held-out child"):
            call_command("explanation_samples", "--children", "H99", stdout=StringIO())
