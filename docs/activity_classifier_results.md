# Activity classifier: results (#181)

> **Last updated: 2026-11-04.** Every figure below is from `python manage.py train_activity_classifier --markdown`, run on the 449 Published activities.

## What it is

A supervised classifier that reads an activity's text and predicts its **area** (5 classes) and its **age band** (7 classes). It is transfer learning on top of the pre-trained SBERT model:

- **Features:** the SBERT embedding of each activity's name, goal and description (`all-MiniLM-L6-v2`, 384 numbers), the same vectors used for recommendations. SBERT itself is not changed.
- **Model:** logistic regression, one for area and one for age band, with balanced class weights. The regularisation strength C is chosen from 0.1, 1, 10 and 100 by an inner 3-fold cross-validation on log loss, inside each training fold only.
- **Labels:** the area and age band each activity already has.

It only suggests and flags. It changes no activity, and the ranking and the held-out evaluation don't use it.

## Evaluation

**5-fold stratified cross-validation** (seed 2026). Every activity is predicted by a model trained without it, and because C is chosen inside each training fold, the test folds play no part in any choice. The baseline always predicts the largest class.

### Area (5 classes)

| Measure | Classifier | Baseline (always Cognitive) |
|---|---|---|
| Accuracy | **0.764** | 0.212 |
| Macro-F1 | **0.764** | — |

| Class | Precision | Recall | F1 | Activities |
|---|---|---|---|---|
| Cognitive | 0.677 | 0.705 | 0.691 | 95 |
| Language | 0.856 | 0.856 | 0.856 | 90 |
| Motor | 0.828 | 0.837 | 0.832 | 92 |
| Sensory | 0.723 | 0.698 | 0.710 | 86 |
| Socio-Emotional | 0.738 | 0.721 | 0.729 | 86 |

Confusion matrix (rows: label, columns: prediction):

| | Cog | Lang | Motor | Sens | S-E |
|---|---|---|---|---|---|
| **Cog** | 67 | 4 | 8 | 8 | 8 |
| **Lang** | 4 | 77 | 2 | 3 | 4 |
| **Motor** | 7 | 1 | 77 | 5 | 2 |
| **Sens** | 12 | 2 | 4 | 60 | 8 |
| **S-E** | 9 | 6 | 2 | 7 | 62 |

- Language and Motor are recognised best.
- Cognitive is the most common wrong guess, especially for Sensory activities (12). Exploring objects is both sensory and cognitive, so the line between them is genuinely blurred.

### Age band (7 classes)

| Measure | Classifier | Baseline (always 24–36 months) |
|---|---|---|
| Accuracy | **0.541** | 0.149 |
| Macro-F1 | **0.543** | — |
| Within one band | **0.862** | — |

| Class | Precision | Recall | F1 | Activities |
|---|---|---|---|---|
| Prenatal | 0.903 | 0.933 | 0.918 | 60 |
| 0–3 months | 0.618 | 0.646 | 0.632 | 65 |
| 3–6 months | 0.477 | 0.484 | 0.481 | 64 |
| 6–12 months | 0.534 | 0.477 | 0.504 | 65 |
| 12–18 months | 0.478 | 0.492 | 0.485 | 65 |
| 18–24 months | 0.375 | 0.333 | 0.353 | 63 |
| 24–36 months | 0.411 | 0.448 | 0.429 | 67 |

Confusion matrix (rows: label, columns: prediction):

| | Pre | 0–3 | 3–6 | 6–12 | 12–18 | 18–24 | 24–36 |
|---|---|---|---|---|---|---|---|
| **Prenatal** | 56 | 3 | 0 | 0 | 0 | 0 | 1 |
| **0–3** | 3 | 42 | 12 | 8 | 0 | 0 | 0 |
| **3–6** | 2 | 14 | 31 | 16 | 1 | 0 | 0 |
| **6–12** | 1 | 9 | 21 | 31 | 1 | 2 | 0 |
| **12–18** | 0 | 0 | 1 | 1 | 32 | 14 | 17 |
| **18–24** | 0 | 0 | 0 | 2 | 15 | 21 | 25 |
| **24–36** | 0 | 0 | 0 | 0 | 18 | 19 | 30 |

- Pregnancy activities are almost always recognised (F1 0.918).
- Most mistakes are a neighbouring band: 86.2% of predictions are right or one band off.
- Baby activities (0–12 months) and toddler activities (12–36 months) are almost never mixed up (8 of 389 post-natal activities). Within each group, the text often suits a range of ages, so the exact band is hard to tell from words alone.

## Flags for review

**60 labels** where the out-of-fold prediction disagreed with at least 70% probability are listed in `data/review/classifier_flags.csv`, most confident first. For example:
- `ACT-0289` *Blowing Raspberries*: labelled Language, predicted Sensory (93%);
- `ACT-0384` *Balloon Chase*: labelled 12–18 months, predicted 18–24 months (92%).

A flag is a prompt to check, not a correction. Many flagged activities fit two areas or two bands. The `reviewer_decision` column is for whoever reviews them.

## Suggestions for new activities

`POST /api/admin/activities/suggest/` returns the three most likely areas and age bands, with probabilities, for an activity's name, goal and description. The in-app activity form has a **Suggest area and age** button; tapping a suggestion fills the field. For example, a new "Clapping Songs" activity (sing, clap the beat, pause for the toddler to fill in the word) gets Sensory 68% and Language 21%, and 18–24 months 39%.

## How to reproduce

```
cd backend
python manage.py train_activity_classifier --markdown
```

This writes the flags sheet and saves the model to `backend/models/activity_classifier.joblib` (gitignored). Run it again after activities are added or embeddings change. The suggestion endpoint refuses (503) if the saved model came from a different embedding model.

## Limitations

- **The labels came with the content.** The activities were written to fit their area and age, and some labels were drafted together with the text, so agreement partly reflects how the catalogue was made. The disagreements are the more useful output.
- **One run, one seed.** No confidence intervals are given.
- **Age is hard from text alone.** Neighbouring bands share skills; within-one-band accuracy (0.862) is the fairer measure.
