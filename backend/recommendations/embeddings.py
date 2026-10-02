"""SBERT sentence embeddings for semantic retrieval (all-MiniLM-L6-v2).

The model is the one saved by setup_sbert.py (settings.SBERT_MODEL_PATH). It is
loaded once per process, on first use, so importing this module or starting
Django doesn't pay for loading PyTorch.
"""

import hashlib

import numpy as np
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

MODEL_NAME = "all-MiniLM-L6-v2"

_encoder = None


class SentenceTransformerEncoder:
    """Encodes texts into L2-normalised float32 vectors."""

    def __init__(self, model, name=MODEL_NAME):
        self._model = model
        self.name = name
        self.dimensions = model.get_embedding_dimension()

    def encode(self, texts):
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)


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

        _encoder = SentenceTransformerEncoder(SentenceTransformer(str(path)))
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
