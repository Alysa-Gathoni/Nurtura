"""TF-IDF retrieval: word-based similarity alongside SBERT (#248).

SBERT compares meaning; TF-IDF compares words, weighted by how rare they are
across the activity library. Both are compared by cosine similarity with the
same needs sentence (retrieval.profile_query) and the same activity text
(embeddings.activity_text), so the only difference is how text becomes
numbers.

retrieval.retrieve combines them as

    similarity = beta * SBERT cosine + (1 - beta) * TF-IDF cosine

with beta = settings.RETRIEVAL_BETA, 0.25 by default since #250. At beta = 1
TF-IDF isn't computed at all, which reproduces the frozen sprint9-eval-v2
SBERT configuration.

The vectoriser is fitted on every Published activity (so a word's rarity
doesn't depend on the child's age band) and kept in memory until the
library's text changes. Its settings are fixed, not tuned.
"""

import hashlib
import threading

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from activities.models import DevelopmentalActivity

from .embeddings import activity_text

# Fixed choices, recorded in the provenance when beta < 1.
SETTINGS = {
    "stop_words": "english",
    "sublinear_tf": True,
    "lowercase": True,
    "ngram_range": [1, 1],
    "norm": "l2",
}

_lock = threading.Lock()
_cache = {"key": None, "index": None}


class TfidfIndex:
    """A TF-IDF vectoriser fitted on the library, with each activity's row."""

    def __init__(self, activities):
        texts = [activity_text(a) for a in activities]
        self.vectorizer = TfidfVectorizer(
            stop_words=SETTINGS["stop_words"],
            sublinear_tf=SETTINGS["sublinear_tf"],
            lowercase=SETTINGS["lowercase"],
            ngram_range=tuple(SETTINGS["ngram_range"]),
            norm=SETTINGS["norm"],
        )
        self.matrix = self.vectorizer.fit_transform(texts)
        self.row = {a.pk: i for i, a in enumerate(activities)}

    def similarities(self, query, activity_pks):
        """Cosine similarity of the query with each activity, in order.

        Rows are L2-normalised, so the dot product is the cosine. An activity
        not in the index (added since) scores 0.
        """
        q = self.vectorizer.transform([query])
        scores = (self.matrix @ q.T).toarray().ravel()
        return np.array(
            [scores[self.row[pk]] if pk in self.row else 0.0 for pk in activity_pks]
        )


def _library():
    activities = list(DevelopmentalActivity.objects.published().order_by("pk"))
    key = hashlib.sha256(
        "\n".join(f"{a.pk}\t{activity_text(a)}" for a in activities).encode("utf-8")
    ).hexdigest()
    return activities, key


def get_index():
    """The index for the current Published library (rebuilt when it changes)."""
    activities, key = _library()
    with _lock:
        if _cache["key"] != key:
            _cache["index"] = TfidfIndex(activities) if activities else None
            _cache["key"] = key
        return _cache["index"]


def similarities(query, activity_pks):
    index = get_index()
    if index is None:
        return np.zeros(len(activity_pks))
    return index.similarities(query, activity_pks)
