"""A learned ranker for the held-out evaluation (#183).

The app ranks by a fixed formula, age_weight × ((1−α)·similarity +
α·priority). This module learns how to combine the same signals from the
held-out labels instead. See docs/experiment_learned_ranker.md for the plan
and the decision rule, both fixed before it was run.

Each (child, activity) pair is described by FEATURES; a multinomial logistic
regression (standardised features, C = 1.0, nothing tuned) is trained on the
relevance grades (0, 1, 2) of the tune children's labelled pairs, and a
candidate is scored by its expected nDCG gain, P(1) × 1 + P(2) × 3.

The app does not use this module.
"""

from dataclasses import dataclass

import numpy as np

from activities.choices import Difficulty

from .ranking import rank_candidates
from .retrieval import retrieve

FEATURES = (
    "similarity",
    "similarity_norm",
    "priority",
    "age_weight",
    "top_area",
    "difficulty",
)
DIFFICULTY = {
    Difficulty.BEGINNER: 0,
    Difficulty.INTERMEDIATE: 1,
    Difficulty.ADVANCED: 2,
}
C = 1.0


@dataclass(frozen=True)
class ChildCandidates:
    """A held-out child's candidates, their features and the two fixed
    rankings they are compared with."""

    features: dict  # {activity_id: np.ndarray of len(FEATURES)}
    sbert: list  # activity_ids by raw similarity (SBERT-only)
    hybrid: list  # activity_ids by the app's formula at `alpha`
    activities: dict  # {activity_id: activity}


def candidates_for(profile, alpha):
    """Features and fixed rankings for one (already created) child."""
    retrieval = retrieve(profile, limit=None)
    ranked = rank_candidates(retrieval.candidates, retrieval.evaluation, alpha)
    features, activities = {}, {}
    for r in ranked:
        aid = r.activity.activity_id
        activities[aid] = r.activity
        features[aid] = np.array(
            [
                r.similarity,
                r.similarity_norm,
                r.priority,
                r.age_weight,
                1.0 if r.priority >= 1.0 - 1e-9 else 0.0,
                DIFFICULTY.get(r.activity.difficulty_level, 0),
            ],
            dtype=float,
        )
    return ChildCandidates(
        features=features,
        sbert=[c.activity.activity_id for c in retrieval.candidates],
        hybrid=[r.activity.activity_id for r in ranked],
        activities=activities,
    )


def training_set(children, candidates, relevance):
    """(X, y) from the labelled pairs of the given children."""
    rows, grades = [], []
    for child_id in children:
        for aid, grade in relevance.get(child_id, {}).items():
            vector = candidates[child_id].features.get(aid)
            if vector is not None:
                rows.append(vector)
                grades.append(grade)
    return np.vstack(rows), np.asarray(grades)


def fit(X, y):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=5000)).fit(
        X, y
    )


def expected_gain(model, X):
    proba = model.predict_proba(X)
    gains = np.array([2.0**grade - 1.0 for grade in model.classes_])
    return proba @ gains


def rank(model, child):
    """The child's activity_ids by expected gain, best first."""
    ids = list(child.features)
    scores = expected_gain(model, np.vstack([child.features[a] for a in ids]))
    order = sorted(zip(ids, scores), key=lambda x: (-x[1], x[0]))
    return [aid for aid, _ in order]


def weights(model):
    """{feature: standardised weight towards grade 2 rather than grade 0}."""
    lr = model[-1]
    classes = list(lr.classes_)
    if 0 not in classes or 2 not in classes:
        return {}
    coef = lr.coef_
    if coef.shape[0] == 1:  # only two classes present
        row = coef[0]
    else:
        row = coef[classes.index(2)] - coef[classes.index(0)]
    return dict(zip(FEATURES, (float(w) for w in row)))
