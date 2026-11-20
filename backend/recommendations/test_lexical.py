"""Tests for TF-IDF retrieval and the SBERT/TF-IDF hybrid (#248)."""

import csv
from io import StringIO
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.test.utils import override_settings

from activities.models import DevelopmentalActivity

from . import embeddings, generation, heldout, lexical, provenance, retrieval
from .management.commands.compare_tfidf import choose_beta
from .models import Recommendation
from .test_embeddings import FakeEncoder
from .test_heldout import HeldOutCommandTestCase
from .test_recommendations_api import publish_catalogue

User = get_user_model()


def fake_activity(pk, name, goal, description):
    return SimpleNamespace(
        pk=pk, activity_name=name, developmental_goal=goal, description=description
    )


class TfidfIndexTests(SimpleTestCase):
    def setUp(self):
        self.index = lexical.TfidfIndex(
            [
                fake_activity(1, "Splash Time", "Water play", "Pour water in a basin."),
                fake_activity(
                    2, "Stack Blocks", "Stacking", "Build a tower of blocks."
                ),
                fake_activity(3, "Animal Sounds", "Listening", "Moo like a cow."),
            ]
        )

    def test_word_overlap_scores_highest(self):
        scores = self.index.similarities("A child who enjoys blocks.", [1, 2, 3])
        self.assertEqual(int(scores.argmax()), 1)
        self.assertGreater(scores[1], 0)
        self.assertEqual(scores[0], 0)  # no shared words

    def test_scores_are_cosines_between_0_and_1(self):
        scores = self.index.similarities("water blocks cow", [1, 2, 3])
        self.assertTrue(all(0.0 <= s <= 1.0 for s in scores))

    def test_stop_words_alone_match_nothing(self):
        scores = self.index.similarities("the and of a", [1, 2, 3])
        self.assertEqual(list(scores), [0.0, 0.0, 0.0])

    def test_an_activity_missing_from_the_index_scores_0(self):
        self.assertEqual(list(self.index.similarities("water", [99])), [0.0])


class ChooseBetaTests(SimpleTestCase):
    """The pre-registered rule: switch only for a gain of at least 0.02."""

    def test_a_large_enough_gain_switches(self):
        self.assertEqual(choose_beta({0.5: 0.80, 1.0: 0.77}), 0.5)

    def test_a_small_gain_keeps_sbert(self):
        self.assertEqual(choose_beta({0.5: 0.785, 1.0: 0.77}), 1.0)

    def test_sbert_best_keeps_sbert(self):
        self.assertEqual(choose_beta({0.0: 0.60, 0.5: 0.70, 1.0: 0.77}), 1.0)

    def test_exactly_the_minimum_gain_switches(self):
        self.assertEqual(choose_beta({0.25: 0.79, 1.0: 0.77}), 0.25)

    def test_no_sbert_mean_keeps_sbert(self):
        self.assertEqual(choose_beta({0.5: 0.9, 1.0: None}), 1.0)


class HybridRetrievalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_milestones", stdout=StringIO())

    def setUp(self):
        embeddings.set_encoder(FakeEncoder())
        self.addCleanup(embeddings.set_encoder, None)
        publish_catalogue()
        caregiver = User.objects.create_user(username="caregiver@example.com")
        self.child = heldout.create_child(heldout.HELDOUT_BY_ID["H03"], caregiver)

    def ordered(self):
        return [
            c.activity.activity_id
            for c in retrieval.retrieve(self.child, limit=None).candidates
        ]

    def test_beta_1_is_sbert_only_and_never_runs_tfidf(self):
        with mock.patch.object(lexical, "similarities") as tfidf:
            with override_settings(RETRIEVAL_BETA=1.0):
                result = retrieval.retrieve(self.child, limit=None)
        tfidf.assert_not_called()
        self.assertTrue(result.candidates)

    def test_beta_0_ranks_by_tfidf(self):
        with override_settings(RETRIEVAL_BETA=0.0):
            result = retrieval.retrieve(self.child, limit=None)
        pks = [c.activity.pk for c in result.candidates]
        expected = lexical.similarities(result.query, pks)
        self.assertEqual(
            [round(c.similarity, 9) for c in result.candidates],
            [round(float(s), 9) for s in expected],
        )
        self.assertEqual(
            [c.similarity for c in result.candidates],
            sorted((c.similarity for c in result.candidates), reverse=True),
        )

    def test_a_hybrid_mixes_both(self):
        with override_settings(RETRIEVAL_BETA=1.0):
            sbert = {
                c.activity.pk: c.similarity
                for c in retrieval.retrieve(self.child, limit=None).candidates
            }
        with override_settings(RETRIEVAL_BETA=0.5):
            result = retrieval.retrieve(self.child, limit=None)
        pks = [c.activity.pk for c in result.candidates]
        tfidf = dict(zip(pks, lexical.similarities(result.query, pks)))
        for c in result.candidates:
            self.assertAlmostEqual(
                c.similarity, 0.5 * sbert[c.activity.pk] + 0.5 * tfidf[c.activity.pk]
            )

    def test_beta_outside_0_to_1_is_refused(self):
        with override_settings(RETRIEVAL_BETA=1.5):
            with self.assertRaises(ValueError):
                retrieval.retrieve(self.child)

    def test_the_index_follows_changes_to_the_library(self):
        first = lexical.get_index()
        self.assertIs(lexical.get_index(), first)  # unchanged: reused
        activity = DevelopmentalActivity.objects.published().first()
        activity.description += " Now with xylophones."
        activity.save()
        second = lexical.get_index()
        self.assertIsNot(second, first)
        self.assertIn("xylophones", second.vectorizer.vocabulary_)


class ProvenanceTests(SimpleTestCase):
    def test_beta_1_keeps_the_evaluated_fingerprint(self):
        self.assertNotIn("retrieval", provenance.ranking_settings())
        self.assertEqual(
            generation.ranking_version(), generation.SPRINT5_EVAL_V1_RANKING_VERSION
        )

    @override_settings(RETRIEVAL_BETA=0.5)
    def test_a_hybrid_changes_the_fingerprint(self):
        settings_ = provenance.ranking_settings()
        self.assertEqual(settings_["retrieval"]["beta"], 0.5)
        self.assertEqual(settings_["retrieval"]["tfidf"], lexical.SETTINGS)
        self.assertNotEqual(
            generation.ranking_version(), generation.SPRINT5_EVAL_V1_RANKING_VERSION
        )


class CompareTfidfCommandTests(HeldOutCommandTestCase):
    def compare(self, *args):
        out = StringIO()
        call_command(
            "compare_tfidf",
            "--labels",
            str(self.path),
            *args,
            stdout=out,
            stderr=StringIO(),
        )
        return out.getvalue()

    def test_reports_every_beta_and_the_rules_decision(self):
        self.publish()
        self.export()
        output = self.compare()
        for name in ("TF-IDF only", "SBERT only", "beta 0.50", "similarity-only"):
            self.assertIn(name, output)
        self.assertIn("alpha 0.7", output)
        self.assertIn("Decision (rule fixed before the results)", output)
        self.assertIn("Tune set (11 children)", output)
        self.assertIn("Test set (for the record) (8 children)", output)

    def test_nothing_is_stored(self):
        self.publish()
        self.export()
        before = Recommendation.objects.count(), User.objects.count()
        self.compare()
        self.assertEqual((Recommendation.objects.count(), User.objects.count()), before)

    def test_unlabelled_pairs_can_be_exported_blind(self):
        self.publish()
        self.export()
        target = self.path.with_name("extra.csv")
        output = self.compare("--export-unlabelled", str(target))
        self.assertIn("unlabelled pair(s)", output)
        with open(target, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertTrue(all(row["relevance"] == "" for row in rows))
