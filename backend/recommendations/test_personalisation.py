"""Tests for learning from a child's feedback (#179)."""

import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from activities.choices import AgeRange, ContentStatus, Domain
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields
from feedback.models import Feedback
from profiles.models import ChildProfile

from . import embeddings, generation
from .models import Recommendation
from .personalisation import BOOST, DISLIKED, LIKED, personalise, signals
from .ranking import RankedActivity
from .test_embeddings import FakeEncoder

User = get_user_model()

# Pairs that share most of their words, so the stand-in encoder finds them
# similar: ACT-0911/0912 (songs) and ACT-0913/0914 (blocks).
ACTIVITIES = [
    ("ACT-0911", "Singing Songs", "Sing songs and rhymes with your baby every day."),
    ("ACT-0912", "Songs and Rhymes", "Sing rhymes and songs with your baby daily."),
    ("ACT-0913", "Stacking Blocks", "Stack wooden blocks and knock the blocks down."),
    ("ACT-0914", "Block Towers", "Build a tower of wooden blocks, then knock it down."),
    ("ACT-0915", "Water Play", "Pour water between cups in a shallow basin."),
]


class PersonalisationTestCase(TestCase):
    def setUp(self):
        embeddings.set_encoder(FakeEncoder())
        self.addCleanup(embeddings.set_encoder, None)
        self.caregiver = User.objects.create_user(username="carer@example.com")
        self.child = ChildProfile.objects.create(
            caregiver=self.caregiver,
            name="Amani",
            date_of_birth=timezone.localdate() - datetime.timedelta(days=230),
        )
        self.a = {}
        for aid, name, text in ACTIVITIES:
            self.a[aid] = DevelopmentalActivity.objects.create(
                **activity_fields(
                    activity_id=aid,
                    activity_name=name,
                    description=text,
                    developmental_goal="Play together",
                    developmental_domain=Domain.LANGUAGE,
                    age_range=AgeRange.MONTHS_6_12,
                    content_status=ContentStatus.PUBLISHED,
                )
            )
        call_command("embed_activities", stdout=StringIO())

    def give(self, aid, outcome="", rating=3, when=None):
        rec = Recommendation.objects.create(
            child=self.child,
            activity=self.a[aid],
            similarity_score=0.5,
            ranking_score=0.5,
        )
        return Feedback.objects.create(
            recommendation=rec,
            rating=rating,
            outcome=outcome,
            date_submitted=when or timezone.now(),
        )

    def ranked(self, score=0.5):
        return [
            RankedActivity(
                activity=self.a[aid],
                score=score,
                similarity=0.5,
                similarity_norm=0.5,
                priority=0.5,
                age_weight=1.0,
            )
            for aid, _, _ in ACTIVITIES
        ]


class SignalsTests(PersonalisationTestCase):
    def test_outcomes_decide(self):
        self.give("ACT-0911", "went_well")
        self.give("ACT-0913", "didnt_work")
        self.give("ACT-0915", "partly")
        found = signals(self.child)
        self.assertEqual(found[self.a["ACT-0911"].pk][0], LIKED)
        self.assertEqual(found[self.a["ACT-0913"].pk][0], DISLIKED)
        self.assertNotIn(self.a["ACT-0915"].pk, found)

    def test_interest_decides_when_there_is_no_outcome(self):
        for aid, interest, kind in (
            ("ACT-0911", "loved_it", LIKED),
            ("ACT-0912", "happy", LIKED),
            ("ACT-0913", "bored", DISLIKED),
            ("ACT-0914", "okay", None),
        ):
            f = self.give(aid, rating=None)
            f.interest = interest
            f.save()
        found = signals(self.child)
        for aid, kind in (
            ("ACT-0911", LIKED),
            ("ACT-0912", LIKED),
            ("ACT-0913", DISLIKED),
        ):
            self.assertEqual(found[self.a[aid].pk][0], kind)
        self.assertNotIn(self.a["ACT-0914"].pk, found)

    def test_an_outcome_outranks_interest(self):
        f = self.give("ACT-0911", "didnt_work", rating=None)
        f.interest = "loved_it"
        f.save()
        self.assertEqual(signals(self.child)[self.a["ACT-0911"].pk][0], DISLIKED)

    def test_older_feedback_falls_back_to_the_rating(self):
        self.give("ACT-0911", rating=5)
        self.give("ACT-0913", rating=1)
        self.give("ACT-0915", rating=3)
        found = signals(self.child)
        self.assertEqual(found[self.a["ACT-0911"].pk][0], LIKED)
        self.assertEqual(found[self.a["ACT-0913"].pk][0], DISLIKED)
        self.assertNotIn(self.a["ACT-0915"].pk, found)

    def test_the_latest_feedback_on_an_activity_wins(self):
        now = timezone.now()
        self.give("ACT-0911", "didnt_work", when=now - datetime.timedelta(days=2))
        self.give("ACT-0911", "went_well", when=now)
        self.assertEqual(signals(self.child)[self.a["ACT-0911"].pk][0], LIKED)


class PersonaliseTests(PersonalisationTestCase):
    def test_no_feedback_changes_nothing(self):
        ranked = self.ranked()
        result = personalise(self.child, ranked)
        self.assertEqual(result.ranked, ranked)
        self.assertEqual((result.excluded, result.notes), (set(), {}))

    def test_went_well_raises_similar_ones_and_says_why(self):
        self.give("ACT-0911", "went_well")
        result = personalise(self.child, self.ranked())
        top = result.ranked[0]
        self.assertEqual(top.activity.activity_id, "ACT-0912")
        self.assertGreater(top.score, 0.5)
        self.assertLessEqual(top.score, 0.5 + BOOST)
        self.assertEqual(
            result.notes_for([top.activity.pk]),
            {
                top.activity.pk: "It's similar to “Singing Songs”, which went "
                "well for Amani."
            },
        )

    def test_didnt_work_lowers_similar_ones_and_is_not_suggested_again(self):
        self.give("ACT-0913", "didnt_work")
        result = personalise(self.child, self.ranked())
        self.assertEqual(result.excluded, {self.a["ACT-0913"].pk})
        last = result.ranked[-1]
        self.assertEqual(last.activity.activity_id, "ACT-0914")
        self.assertLess(last.score, 0.5)
        self.assertNotIn(last.activity.pk, result.notes)

    def test_at_most_two_notes_per_batch(self):
        result = personalise(self.child, self.ranked())
        for aid, boost in (("ACT-0912", 0.1), ("ACT-0914", 0.2), ("ACT-0915", 0.05)):
            result.notes[self.a[aid].pk] = (boost, aid)
        chosen = result.notes_for([a.pk for a in self.a.values()])
        self.assertEqual(sorted(chosen.values()), ["ACT-0912", "ACT-0914"])

    def test_scores_stay_between_0_and_1(self):
        self.give("ACT-0911", "went_well")
        self.give("ACT-0913", "didnt_work")
        for score in (0.0, 1.0):
            for r in personalise(self.child, self.ranked(score)).ranked:
                self.assertGreaterEqual(r.score, 0.0)
                self.assertLessEqual(r.score, 1.0)


class GenerationTests(PersonalisationTestCase):
    def test_batch_leaves_out_what_didnt_work_and_explains_boosts(self):
        self.give("ACT-0913", "didnt_work")
        self.give("ACT-0911", "went_well")
        result = generation.generate(self.child.pk, self.caregiver)
        ids = [r.activity.activity_id for r in result.recommendations]
        self.assertNotIn("ACT-0913", ids)
        songs = next(
            r for r in result.recommendations if r.activity.activity_id == "ACT-0912"
        )
        self.assertTrue(
            songs.explanation.endswith(
                "It's similar to “Singing Songs”, which went well for Amani."
            )
        )
        self.assertLessEqual(ids.index("ACT-0912"), ids.index("ACT-0914"))

    def test_a_pin_marked_as_not_working_is_dropped(self):
        pinned = generation.generate(
            self.child.pk, self.caregiver, pin=(self.a["ACT-0915"].pk, "Chosen.")
        ).recommendations[0]
        self.assertTrue(pinned.pinned)
        Feedback.objects.create(recommendation=pinned, rating=1, outcome="didnt_work")
        later = generation.generate(self.child.pk, self.caregiver)
        self.assertNotIn(
            "ACT-0915", [r.activity.activity_id for r in later.recommendations]
        )
