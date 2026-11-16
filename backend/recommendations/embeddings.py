"""SBERT sentence embeddings for semantic retrieval (all-MiniLM-L6-v2).

The model is the one saved by setup_sbert.py (settings.SBERT_MODEL_PATH). It is
loaded once per process, on first use, so importing this module or starting
Django doesn't pay for loading PyTorch.
"""

import hashlib
import threading
from collections import OrderedDict

import numpy as np
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

MODEL_NAME = "all-MiniLM-L6-v2"

_encoder = None


class SentenceTransformerEncoder:
    """Encodes texts into L2-normalised float32 vectors.

    Single-text calls (a child's profile query, an Explore search) are
    cached, up to cache_size texts, least recently used first out (#226): a
    child whose profile hasn't changed, or a repeated search, doesn't run
    SBERT again. Calls with several texts (embedding activities) are never
    cached, so batch results are exactly as before. A cached vector is the
    same array SBERT returned for that text, copied on the way out.
    """

    def __init__(self, model, name=MODEL_NAME, cache_size=0):
        self._model = model
        self.name = name
        self.dimensions = model.get_embedding_dimension()
        self._cache_size = cache_size
        self._cache = OrderedDict()
        self._lock = threading.Lock()

    def _encode(self, texts):
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    def encode(self, texts):
        texts = list(texts)
        if len(texts) != 1 or self._cache_size <= 0:
            return self._encode(texts)
        text = texts[0]
        with self._lock:
            hit = self._cache.get(text)
            if hit is not None:
                self._cache.move_to_end(text)
                return hit[np.newaxis, :].copy()
        vector = self._encode(texts)[0]
        with self._lock:
            self._cache[text] = vector
            self._cache.move_to_end(text)
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
        return vector[np.newaxis, :].copy()


def get_encoder():
    """The process-wide encoder, loading the saved model on first use."""
    global _encoder
    if _encoder is None:
        path = settings.SBERT_MODEL_PATH
        if not path.exists():
            raise ImproperlyConfigured(
                f"SBERT model not found at {path}. "
                "Run `python setup_sbert.py` from backend/ to download it."
            )
        from sentence_transformers import SentenceTransformer

        if settings.SBERT_TORCH_THREADS > 0:
            import torch

            # See settings.SBERT_TORCH_THREADS (#226).
            torch.set_num_threads(settings.SBERT_TORCH_THREADS)
        _encoder = SentenceTransformerEncoder(
            SentenceTransformer(str(path)),
            cache_size=settings.SBERT_QUERY_CACHE_SIZE,
        )
    return _encoder


def set_encoder(encoder):
    """Replace the encoder (tests use a lightweight stand-in)."""
    global _encoder
    _encoder = encoder


def activity_text(activity):
    """The text embedded for an activity: what a caregiver reads about it.

    The domain label is left out on purpose: domain priority comes from the
    rule engine, and the two signals are combined in the weighted ranking
    (Sprint 5), so the semantic signal shouldn't count the domain twice.
    """
    parts = [activity.activity_name, activity.developmental_goal, activity.description]
    return ". ".join(p.strip().rstrip(".") for p in parts if p.strip()) + "."


def text_hash(model_name, text):
    """Fingerprint of what was embedded, to detect stale embeddings."""
    return hashlib.sha256(f"{model_name}\n{text}".encode("utf-8")).hexdigest()


def to_bytes(vector):
    return np.asarray(vector, dtype=np.float32).tobytes()


def from_bytes(data):
    return np.frombuffer(bytes(data), dtype=np.float32)
