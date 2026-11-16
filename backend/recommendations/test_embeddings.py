"""Tests for the batch SBERT embedding pipeline (#29)."""

import hashlib
import re
import unittest
from io import StringIO

import numpy as np
from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from activities.choices import ContentStatus
from activities.models import DevelopmentalActivity
from activities.tests import activity_fields

from . import embeddings
from .models import ActivityEmbedding


class FakeEncoder:
    """Deterministic stand-in for SBERT: hashed bag of words, L2-normalised.

    Texts sharing words get similar vectors, which is enough to test the
    pipeline without loading the 90 MB model.
    """

    name = "fake-encoder"
    dimensions = 384

    def __init__(self):
        self.calls = []

    def encode(self, texts):
        texts = list(texts)
        self.calls.append(texts)
        vectors = np.zeros((len(texts), self.dimensions), dtype=np.float32)
        for row, text in enumerate(texts):
            for word in re.findall(r"[a-z]+", text.lower()):
                index = (
                    int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dimensions
                )
                vectors[row, index] += 1.0
            norm = np.linalg.norm(vectors[row])
            if norm:
                vectors[row] /= norm
        return vectors


class FakeEncoderMixin:
    def setUp(self):
        super().setUp()
        self.encoder = FakeEncoder()
        embeddings.set_encoder(self.encoder)
        self.addCleanup(embeddings.set_encoder, None)


def published_activity(**overrides):
    return DevelopmentalActivity.objects.create(
        **activity_fields(content_status=ContentStatus.PUBLISHED, **overrides)
    )


class EmbedActivitiesCommandTests(FakeEncoderMixin, TestCase):
    def embed(self, *args):
        out = StringIO()
        call_command("embed_activities", *args, stdout=out)
        return out.getvalue()

    def test_embeds_only_published_activities(self):
        published = published_activity()
        DevelopmentalActivity.objects.create(
            **activity_fields(activity_id="ACT-0002", activity_name="Peekaboo")
        )
        output = self.embed()

        self.assertIn("1 Published: 1 embedded, 0 up to date, 0 removed", output)
        embedding = ActivityEmbedding.objects.get()
        self.assertEqual(embedding.activity, published)
        self.assertEqual(embedding.model_name, "fake-encoder")
        vector = embeddings.from_bytes(embedding.vector)
        self.assertEqual(vector.shape, (384,))
        self.assertEqual(embedding.dimensions, 384)
        self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=5)

    def test_unchanged_activities_are_skipped(self):
        published_activity()
        self.embed()
        output = self.embed()
        self.assertIn("1 Published: 0 embedded, 1 up to date", output)
        self.assertEqual(len(self.encoder.calls), 1)

    def test_changed_text_is_re_embedded(self):
        activity = published_activity()
        self.embed()
        before = ActivityEmbedding.objects.get().vector
        activity.description = "Sing songs and name the sounds animals make."
        activity.save()

        output = self.embed()
        self.assertIn("1 embedded, 0 up to date", output)
        self.assertNotEqual(
            bytes(ActivityEmbedding.objects.get().vector), bytes(before)
        )

    def test_force_re_embeds_everything(self):
        published_activity()
        self.embed()
        self.assertIn("1 embedded, 0 up to date", self.embed("--force"))

    def test_unpublished_activities_lose_their_embedding(self):
        activity = published_activity()
        self.embed()
        activity.transition_to(ContentStatus.DRAFT)
        output = self.embed()
        self.assertIn("0 Published: 0 embedded, 0 up to date, 1 removed", output)
        self.assertFalse(ActivityEmbedding.objects.exists())

    def test_nothing_published_explains_what_to_do(self):
        output = self.embed()
        self.assertIn("No Published activities to embed", output)
        self.assertEqual(self.encoder.calls, [])

    def test_dry_run_saves_nothing_and_skips_encoding(self):
        published_activity()
        output = self.embed("--dry-run")
        self.assertIn("1 would be embedded", output)
        self.assertIn("dry run - nothing saved", output)
        self.assertFalse(ActivityEmbedding.objects.exists())
        self.assertEqual(self.encoder.calls, [])

    def test_embedded_text_excludes_domain_label(self):
        activity = published_activity()
        text = embeddings.activity_text(activity)
        self.assertEqual(
            text,
            "Tummy Time. Build neck strength. Supervised time on the tummy.",
        )
        self.assertNotIn("Motor", text)


class EmbeddingHelperTests(SimpleTestCase):
    def test_vector_round_trip(self):
        vector = np.arange(384, dtype=np.float32) / 384
        self.assertTrue(
            np.array_equal(embeddings.from_bytes(embeddings.to_bytes(vector)), vector)
        )

    def test_text_hash_depends_on_model_and_text(self):
        base = embeddings.text_hash("model-a", "text")
        self.assertEqual(base, embeddings.text_hash("model-a", "text"))
        self.assertNotEqual(base, embeddings.text_hash("model-b", "text"))
        self.assertNotEqual(base, embeddings.text_hash("model-a", "other"))


class CountingModel:
    """Stands in for a SentenceTransformer and counts what it encodes."""

    def __init__(self):
        self.calls = []

    def get_embedding_dimension(self):
        return 3

    def encode(self, texts, **kwargs):
        self.calls.append(list(texts))
        return np.array([[len(t), t.count("a"), 1.0] for t in texts], dtype=np.float32)


class QueryCacheTests(SimpleTestCase):
    """Single-text encodes are cached; batches never are (#226)."""

    def encoder(self, size=2):
        self.model = CountingModel()
        return embeddings.SentenceTransformerEncoder(self.model, cache_size=size)

    def test_a_repeated_query_is_encoded_once(self):
        encoder = self.encoder()
        first = encoder.encode(["a baby who loves music"])
        second = encoder.encode(["a baby who loves music"])
        self.assertEqual(len(self.model.calls), 1)
        self.assertTrue(np.array_equal(first, second))
        self.assertEqual(second.shape, (1, 3))

    def test_cached_vectors_are_copies(self):
        encoder = self.encoder()
        encoder.encode(["text"])[0, 0] = 99
        self.assertEqual(encoder.encode(["text"])[0, 0], 4)

    def test_least_recently_used_is_dropped(self):
        encoder = self.encoder(size=2)
        for text in ("one", "two", "one", "three", "one", "two"):
            encoder.encode([text])
        # "two" was dropped when "three" came in; "one" was kept.
        self.assertEqual(
            [c[0] for c in self.model.calls], ["one", "two", "three", "two"]
        )

    def test_batches_are_not_cached(self):
        encoder = self.encoder()
        encoder.encode(["one", "two"])
        encoder.encode(["one", "two"])
        encoder.encode(["one"])
        self.assertEqual(len(self.model.calls), 3)

    def test_size_zero_turns_the_cache_off(self):
        encoder = self.encoder(size=0)
        encoder.encode(["one"])
        encoder.encode(["one"])
        self.assertEqual(len(self.model.calls), 2)


class LoadSettingsTests(SimpleTestCase):
    """The settings the load test asked for (#226)."""

    def test_postgres_uses_a_bounded_pool(self):
        db = settings.DATABASES["default"]
        if db["ENGINE"] != "django.db.backends.postgresql":
            self.skipTest("SQLite run")
        pool = db["OPTIONS"]["pool"]
        self.assertLessEqual(pool["min_size"], pool["max_size"])
        self.assertLess(pool["max_size"], 100)  # PostgreSQL's default limit

    def test_server_errors_are_logged(self):
        logger = settings.LOGGING["loggers"]["django.request"]
        self.assertEqual(logger["level"], "ERROR")
        self.assertIn("console", logger["handlers"])


@unittest.skipUnless(
    settings.SBERT_MODEL_PATH.exists(),
    "SBERT model not downloaded (run setup_sbert.py); skipped in CI",
)
class RealSbertModelTests(SimpleTestCase):
    """Uses the real all-MiniLM-L6-v2 model when it is available locally."""

    def setUp(self):
        embeddings.set_encoder(None)
        self.addCleanup(embeddings.set_encoder, None)

    def test_real_model_ranks_paraphrases_above_unrelated_text(self):
        encoder = embeddings.get_encoder()
        self.assertEqual(encoder.name, "all-MiniLM-L6-v2")
        vectors = encoder.encode(
            [
                "Talk and sing to your baby to build early language.",
                "Chat and sing with the infant so they learn words.",
                "Stack wooden blocks to practise hand-eye coordination.",
            ]
        )
        self.assertEqual(vectors.shape, (3, 384))
        paraphrase = float(vectors[0] @ vectors[1])
        unrelated = float(vectors[0] @ vectors[2])
        self.assertGreater(paraphrase, unrelated + 0.2)
