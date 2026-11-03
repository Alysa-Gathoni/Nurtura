"""Predict an activity's area and age band from its text (#181).

Transfer learning on top of the pre-trained SBERT model: the features are
the activity embeddings already stored for retrieval (all-MiniLM-L6-v2, 384
numbers per activity), and a logistic regression is trained for each target
using the labels the activities already have:

- developmental_domain: 5 classes;
- age_range: 7 classes (Prenatal and six bands after birth).

Each is evaluated with stratified k-fold cross-validation, so every
activity is predicted by a model that never saw it. The regularisation
strength C is chosen inside each training fold by a further cross-validation
(nested), so the test folds play no part in choosing it. The classifier is
then trained on all activities and saved to settings.ACTIVITY_CLASSIFIER_PATH
(gitignored).
Out-of-fold predictions that confidently disagree with the stored label are
flagged for review.

The classifier only suggests and flags. It changes no activity, and the
ranking and the evaluation don't use it.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

import numpy as np
from django.conf import settings

from recommendations import embeddings
from recommendations.models import ActivityEmbedding

from .choices import AgeRange, ContentStatus, Domain

TARGETS = {"developmental_domain": Domain, "age_range": AgeRange}
FOLDS = 5
SEED = 2026
FLAG_CONFIDENCE = 0.7  # out-of-fold probability needed to flag a label
TOP_SUGGESTIONS = 3
C_GRID = (0.1, 1.0, 10.0, 100.0)


class ClassifierUnavailable(Exception):
    """No trained classifier, or it was trained on another embedding model."""


@dataclass(frozen=True)
class Flag:
    activity: object
    field: str
    label: str
    predicted: str
    confidence: float


def _model():
    from sklearn.linear_model import LogisticRegressionCV

    # Balanced class weights, so smaller areas aren't swamped; C chosen by
    # an inner stratified cross-validation on the training data only, by log
    # loss, since the probabilities are shown to administrators.
    return LogisticRegressionCV(
        Cs=list(C_GRID),
        cv=3,
        scoring="neg_log_loss",
        l1_ratios=(0.0,),
        use_legacy_attributes=False,
        max_iter=5000,
        class_weight="balanced",
    )


def _order(field, values):
    """Classes in their natural order (the choice order: age bands by age)."""
    order = [v for v, _ in TARGETS[field].choices]
    return sorted(values, key=lambda v: order.index(v) if v in order else len(order))


def training_data():
    """(Published activities with an embedding, their vectors as a matrix)."""
    rows = list(
        ActivityEmbedding.objects.filter(
            activity__content_status=ContentStatus.PUBLISHED
        )
        .select_related("activity")
        .order_by("activity__activity_id")
    )
    activities = [r.activity for r in rows]
    if not rows:
        return activities, np.zeros((0, 0), dtype=np.float32)
    return activities, np.vstack([embeddings.from_bytes(r.vector) for r in rows])


def cross_validate(X, y, field=None):
    """Out-of-fold predictions and metrics for one target."""
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_recall_fscore_support,
    )
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    y = np.asarray(y)
    model_order = sorted(set(y))  # predict_proba columns follow this order
    folds = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    proba = cross_val_predict(_model(), X, y, cv=folds, method="predict_proba")
    predicted = np.asarray(model_order)[proba.argmax(axis=1)]
    classes = _order(field, model_order) if field else model_order
    precision, recall, f1, support = precision_recall_fscore_support(
        y, predicted, labels=classes, zero_division=0
    )
    majority = max(classes, key=lambda c: (y == c).sum())
    position = {c: i for i, c in enumerate(classes)}
    # Age bands are ordered, so a neighbouring band is a near miss.
    within_one = float(
        np.mean([abs(position[a] - position[b]) <= 1 for a, b in zip(y, predicted)])
    )
    return {
        "within_one": within_one,
        "classes": classes,
        "proba": proba,
        "predicted": predicted,
        "accuracy": accuracy_score(y, predicted),
        "macro_f1": f1_score(y, predicted, average="macro", zero_division=0),
        "baseline_accuracy": float((y == majority).mean()),
        "baseline_class": majority,
        "per_class": [
            {
                "class": c,
                "precision": float(p),
                "recall": float(r),
                "f1": float(f),
                "support": int(s),
            }
            for c, p, r, f, s in zip(classes, precision, recall, f1, support)
        ],
        "confusion": confusion_matrix(y, predicted, labels=classes).tolist(),
    }


def embedding_model_name():
    """The model the stored vectors came from (one per activity)."""
    names = set(
        ActivityEmbedding.objects.filter(
            activity__content_status=ContentStatus.PUBLISHED
        ).values_list("model_name", flat=True)
    )
    if len(names) != 1:
        raise ClassifierUnavailable(
            f"Stored embeddings come from {len(names)} models; run "
            "embed_activities first."
        )
    return names.pop()


def train():
    """Cross-validate, then fit on everything.

    Returns (models by field, reports by field, flags, number of activities).
    """
    activities, X = training_data()
    models, reports, flags = {}, {}, []
    for field in TARGETS:
        y = [getattr(a, field) for a in activities]
        report = cross_validate(X, y, field)
        reports[field] = report
        models[field] = _model().fit(X, y)
        for activity, label, predicted, row in zip(
            activities, y, report["predicted"], report["proba"]
        ):
            confidence = float(row.max())
            if predicted != label and confidence >= FLAG_CONFIDENCE:
                flags.append(Flag(activity, field, label, str(predicted), confidence))
    flags.sort(key=lambda f: (-f.confidence, f.activity.activity_id))
    return models, reports, flags, len(activities)


def save(models, reports, count, path=None):
    import joblib

    path = path or settings.ACTIVITY_CLASSIFIER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "models": models,
            "embedding_model": embedding_model_name(),
            "activities": count,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                field: {
                    "accuracy": float(r["accuracy"]),
                    "macro_f1": float(r["macro_f1"]),
                    "baseline_accuracy": r["baseline_accuracy"],
                }
                for field, r in reports.items()
            },
        },
        path,
    )
    global _loaded
    _loaded = None
    return path


_loaded = None


def load(path=None):
    """The saved classifier bundle (cached until the file changes)."""
    import joblib

    global _loaded
    path = path or settings.ACTIVITY_CLASSIFIER_PATH
    if not path.exists():
        raise ClassifierUnavailable(
            "The activity classifier hasn't been trained. Run "
            "`python manage.py train_activity_classifier`."
        )
    stamp = path.stat().st_mtime
    if _loaded is None or _loaded[0] != (path, stamp):
        _loaded = ((path, stamp), joblib.load(path))
    return _loaded[1]


def suggest(name, goal, description):
    """{field: [(value, label, probability), ...]}, most likely first."""
    bundle = load()
    encoder = embeddings.get_encoder()
    if encoder.name != bundle["embedding_model"]:
        raise ClassifierUnavailable(
            f"The classifier was trained on {bundle['embedding_model']} but the "
            f"app now uses {encoder.name}. Run train_activity_classifier again."
        )
    text = embeddings.activity_text(
        SimpleNamespace(
            activity_name=name, developmental_goal=goal, description=description
        )
    )
    vector = encoder.encode([text])
    result = {}
    for field, choices in TARGETS.items():
        model = bundle["models"][field]
        proba = model.predict_proba(vector)[0]
        labels = dict(choices.choices)
        ranked = sorted(zip(model.classes_, proba), key=lambda x: -x[1])
        result[field] = [
            (str(value), labels.get(value, value), float(p))
            for value, p in ranked[:TOP_SUGGESTIONS]
        ]
    return result
