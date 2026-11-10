# Requirements traceability

> **Last updated: 2026-11-09.** Traces every requirement in Chapter 4 (Section 4.2) of the June 2026 proposal to where it is built, how it is tested and its status. Figures come from real runs. The proposal text hasn't been updated yet; where the built system differs from the wording, the row says so and [Wording to update in Chapter 4](#wording-to-update-in-chapter-4) lists the change.

Status key:

- **Met:** built and tested as written.
- **Met, with a deviation:** built, but differs from the wording in a stated way.
- **Partly met:** some of the requirement is built.
- **Not met:** not built.
- **Evidence pending:** built, but the evaluation that verifies it hasn't run yet.

## Summary

| Group | Met | Met, with a deviation | Partly met | Evidence pending | Not met |
|---|---|---|---|---|---|
| Functional (FR-01 to FR-18) | 13 | 3 | 2 | 0 | 0 |
| Non-functional (NFR-01 to NFR-13) | 8 | 1 | 1 | 3 | 0 |
| Data (DR-01 to DR-11) | 8 | 0 | 3 | 0 | 0 |
| Interface (IR-01 to IR-09) | 8 | 0 | 1 | 0 | 0 |

## Old IDs in the repository

Before this document, code and docs cited IDs from an older requirements list. Live code and current docs now use the Chapter 4 IDs (#198). Historical documents ([DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), [sprint_ii_review.md](sprint_ii_review.md)) are left as written; read their IDs with this table.

| Old ID in the repo | Meant | Chapter 4 ID |
|---|---|---|
| FR-06 | Semantic retrieval with SBERT | **FR-09** |
| FR-07 | Weighted ranking | **FR-10** |
| FR-13 | Activity management and content status | **FR-06** (content status is a SOFIA addition) |
| DR-10 (on embeddings) | Precomputed embeddings | **DR-09** |
| DR-12 | Content status: Draft, Under Review, Published | Not in Chapter 4: SOFIA addition |
| NFR-14 | Offline use | Not in Chapter 4: SOFIA addition |
| NFR-15 | Non-comparative progress | Not in Chapter 4: SOFIA addition |
| NFR-16 | Language toggle | Not in Chapter 4: SOFIA suggestion, not built |
| IR-10 | Data-protection split with Webmasters Kenya | Not in Chapter 4: SOFIA addition, open |
| NFR-06 (development plan, for explanations) | Explanations | **FR-11, NFR-10** (Chapter 4 NFR-06 is usability) |
| NFR-08 (development plan, for embeddings) | Embeddings | **DR-09** (Chapter 4 NFR-08 is compatibility) |

All other IDs in the repo (FR-01, FR-02, FR-05, FR-11, FR-14 to FR-16, NFR-02, NFR-03, NFR-06, NFR-10, NFR-12, NFR-13, DR-09, IR-01 to IR-04, IR-06) already mean what Chapter 4 says.

## Functional requirements

| ID | Requirement | Where it is built | Tests and evidence | Status |
|---|---|---|---|---|
| FR-01 | Registration and authentication | `profiles`: register, log in with a two-step email code, Google sign-in, password reset, token expiry (#162). App sign-in screens. | `profiles/test_api.py`, `test_two_factor.py`, `test_google_sign_in.py`, `test_password_reset*.py`, `test_token_expiry.py`; app `auth_screen_test.dart`, `google_sign_in_test.dart` | **Met, with a deviation:** self-registration always creates a Caregiver. The first administrator is made with `createsuperuser` and others from the web admin, so nobody can register as one. Apple sign-in (wireframe) was not built. |
| FR-02 | Role management | `User.role`; `IsCaregiver` and `IsAdministrator` permissions | `profiles/test_api.py` (another caregiver's child → 404, administrator → 403, no token → 401) | **Met** |
| FR-03 | Child profile management | `ChildProfile` with name, date of birth, gender, interests, concerns; create, view, edit and delete (#134) | `profiles/tests.py`, `test_account_deletion.py`; app `children_screen_test.dart`, `edit_and_delete_test.dart` | **Partly met:** `preferences` is stored and accepted by the API, but the app doesn't ask for it and nothing uses it. Contextual information (home, resources, routines) isn't collected. |
| FR-04 | Developmental information recording | Milestones chosen from the CDC/WHO catalogue with status Achieved, Emerging or Not yet; concerns by area; observations from activities (#192) | `profiles/test_milestone_api.py`, `test_tracker.py`; app `milestone_screen_test.dart`, `milestone_tracker_test.dart` | **Partly met:** developmental goals aren't collected. Free-text milestones aren't accepted, so every observation maps to a catalogue milestone. |
| FR-05 | Developmental profile generation | Custom IF-THEN rule engine, `profiles/rules/`; `DevelopmentalProfile` with 0–1 priority per area | `profiles/test_rules.py`, `test_profile_scenarios.py`, `test_guidelines.py` | **Met, with a deviation:** a custom engine, not experta (Section 3.2.2 allowed either). |
| FR-06 | Activity repository management | In-app administrator screens (#122, #123) and the Django admin; Draft → Under Review → Published, with history | `activities/tests.py`, `test_seed.py`; app `admin_test.dart` | **Met.** Content status is a SOFIA addition beyond the wording. |
| FR-07 | Activity information management | `DevelopmentalActivity`: every Table 3.1 attribute, plus source, source URL and a plain-language aim | `activities/tests.py`, `test_load_plain_aims.py` | **Met** |
| FR-08 | Personalised recommendation | `recommendations/generation.py`: rule engine → retrieval → ranking → top 5 stored as a batch | `recommendations/test_recommendations_api.py` | **Met** |
| FR-09 | Semantic retrieval | `recommendations/retrieval.py`: `all-MiniLM-L6-v2` query from the profile, cosine similarity against stored vectors | `recommendations/test_retrieval.py`, `test_embeddings.py`; spot check ([sprint4_retrieval_spot_check.md](sprint4_retrieval_spot_check.md)) | **Met** |
| FR-10 | Ranking and scoring | `recommendations/ranking.py`: `age_weight × ((1 − α)·similarity + α·priority)`, α = 0.7 | `recommendations/test_ranking.py`; held-out evaluation ([eval_v2_results.md](eval_v2_results.md), [eval_v2_statistics.md](eval_v2_statistics.md)) | **Met, with a deviation:** ranks by developmental need, similarity and age fit. Caregiver preferences and context aren't weighted. Interests enter only through the retrieval query and the explanation. Feedback changes later suggestions only through the options and personalisation steps (#175 to #180). |
| FR-11 | Recommendation explanation | `recommendations/explanations.py`: the area, the milestones or concerns behind it, the age fit and any matched interest | `recommendations/test_explanations.py` (explanations read back against stored profiles; no diagnostic words) | **Met.** Scores are deliberately not shown to caregivers; they are stored with each recommendation (DR-05). |
| FR-12 | View recommendations | Today tab; `GET`/`POST /api/children/<id>/recommendations/` | app `recommendations_screen_test.dart`; `test_recommendations_api.py` | **Met** |
| FR-13 | Activity details | Activity screen: description, materials, Kenyan context, source and link (#138) | app `activity_detail_screen_test.dart`, `activity_details_and_polish_test.dart` | **Met** |
| FR-14 | Completion tracking | Done, partly done and undo (#94) | `feedback/test_api.py`; app `activity_progress_test.dart` | **Met** |
| FR-15 | Caregiver feedback | `FeedbackManager`: how it went, issues, interest level, optional rating and comment (#175, #185) | `feedback/tests.py`, `test_api.py`, `test_observations.py`; app `well_done_sheet_test.dart`, `feedback_options_test.dart` | **Met** |
| FR-16 | Feedback review | Administrator feedback screens in the app and the Django admin, without the child or caregiver shown | `feedback/test_admin.py`; app `admin_test.dart` | **Met** |
| FR-17 | Request validation | Child and milestone input validated on entry (required fields, known areas only, observations neither in the future nor before birth); the app checks forms before sending | `profiles/tests.py`, `test_milestone_api.py`; app `children_screen_test.dart` | **Met.** Validation happens when data is entered, so a recommendation request needs nothing further. |
| FR-18 | Recommendation storage | `Recommendation`: batch, position, scores, α, profile fingerprint, explanation and versions | `recommendations/test_recommendations_api.py` | **Met** |

## Non-functional requirements

| ID | Requirement | Evidence | Status |
|---|---|---|---|
| NFR-01 | Performance | Warm POST in process p95 34 ms; over local HTTP p95 146 ms (100 requests, one laptop). Cold start removed by loading the model at start-up ([performance_recommendations.md](performance_recommendations.md)). | **Met** on the development laptop; not measured on a hosted server. |
| NFR-02 | Security | Token authentication with expiry, login and code throttling, password validators, role permissions | `profiles/test_api.py` (throttling, roles), `test_token_expiry.py` | **Met** |
| NFR-03 | Data privacy | Caregivers see only their own children; administrators see no child data; privacy notice and consent (#136); account deletion | `profiles/test_api.py`, `test_privacy.py`, `test_account_deletion.py`; app `privacy_consent_test.dart` | **Met** |
| NFR-04 | Data integrity | Database constraints (score ranges, unique positions), atomic batch writes | `recommendations/tests.py`, `test_recommendations_api.py` (out-of-range values rejected by the database) | **Met** |
| NFR-05 | Reliability | Row lock so two simultaneous requests store one batch; invalid input refused without partial writes | `test_recommendations_api.py` (`test_simultaneous_posts_store_one_batch`) | **Met** |
| NFR-06 | Usability (SUS) | SUS in the caregiver sessions ([caregiver_evaluation.md](caregiver_evaluation.md)) | **Evidence pending:** sessions not yet run. |
| NFR-07 | Accessibility | Flutter's Android tap-target (48 × 48), labelled tap-target and WCAG AA text-contrast (4.5:1) guidelines on sign-in and every caregiver tab, in light and dark themes; every tab at twice the text size without overflow (#206) | app `accessibility_test.dart` | **Met.** Not yet tried with TalkBack on a phone; the automated checks cover labels, sizes and contrast. |
| NFR-08 | Compatibility | Flutter app on Android; REST API | app tests; end-to-end run on a phone ([evidence/e2e_2026-10-15](evidence/e2e_2026-10-15)) | **Met, with a deviation:** Android only. iOS was removed (#186). |
| NFR-09 | Maintainability | Separate Django apps: `profiles`, `activities`, `recommendations`, `feedback`, `insights` | Code inspection | **Met** |
| NFR-10 | Explainability | Explanations traced to the profile (FR-11); the explanation reader test checks caregivers understand them ([explanation_reader_test.md](explanation_reader_test.md)) | **Evidence pending:** the automated trace is done; the reader test hasn't run. |
| NFR-11 | Human oversight | Wording is guidance, never diagnosis; the clinic-visit referral is gentle and outside the ranking (#161) | `test_explanations.py` (no diagnostic words), `test_referral.py`, `test_tracker.py` | **Met** |
| NFR-12 | Recommendation quality | Relevance: graded human labels on 20 held-out children, nDCG@5 0.836 against 0.582 for SBERT alone (95% CI of the difference +0.136 to +0.379). Explainability: as NFR-10. Diversity, novelty and coverage: not yet computed. | **Partly met:** relevance is judged by human labels, not similarity scores (a stated deviation); the diversity, novelty and coverage metrics are still to do. |
| NFR-13 | Caregiver satisfaction | Post-use questionnaire in the caregiver sessions | **Evidence pending:** sessions not yet run. |

## Data requirements

| ID | Requirement | Where | Status |
|---|---|---|---|
| DR-01 | User data | `User` (email, password hash, role) | **Met** |
| DR-02 | Child profile data | `ChildProfile` | **Partly met:** age, interests, gender and concerns are stored; preferences are stored but unused; context isn't stored. |
| DR-03 | Developmental data | `DevelopmentalMilestone`, concerns, observations | **Partly met:** goals aren't stored. |
| DR-04 | Activity data | `DevelopmentalActivity`; 449 Published activities from WHO, UNICEF, CDC, Montessori and Pathways.org | **Met** |
| DR-05 | Recommendation data | `Recommendation` (similarity, rule priority, age weight, ranking score, explanation, child) | **Met** |
| DR-06 | Completion data | `CompletedActivity` | **Met** |
| DR-07 | Feedback data | `Feedback` | **Met** |
| DR-08 | Data validation | Serializer validation; the seed command saves nothing if any row is invalid | **Met** (`activities/test_seed.py`) |
| DR-09 | Preprocessing and embeddings | `embed_activities` precomputes vectors in batch; only the profile is encoded per request | **Met** (`test_embeddings.py`) |
| DR-10 | Provenance and traceability | `source`, `source_url`, `created_at`, `updated_at` and status history on each activity | **Met** |
| DR-11 | Data protection | Role-restricted access; data kept until the caregiver deletes it | **Partly met:** access is restricted by role (NFR-03). Data is in a local PostgreSQL on the development machine; secure hosting waits for deployment. |

## Interface and integration requirements

| ID | Requirement | Where | Status |
|---|---|---|---|
| IR-01 | Mobile interface | Flutter app: sign-in, Family, Today, Explore (#194), Progress, Milestones | **Met** |
| IR-02 | Administrator interface | Administrator screens in the app (#122, #123) and the Django admin | **Met** |
| IR-03 | REST API | `/api/…` endpoints (README API table) | **Met** |
| IR-04 | JSON format | DRF JSON requests and responses | **Met** |
| IR-05 | Recommendation engine interface | `generation.generate()` called by the view | **Met** |
| IR-06 | Processing stages | Rule engine → SBERT retrieval → cosine similarity → weighted ranking | **Met** |
| IR-07 | Database interface | Django ORM on PostgreSQL | **Met** |
| IR-08 | Error handling | DRF error responses without internal detail; the app shows plain messages | **Met** (`profiles/test_api.py`, app `email_failure_test.dart`) |
| IR-09 | Secure communication | Token authentication on every call | **Partly met:** HTTPS depends on deployment, which is on hold. Development runs over local HTTP (`adb reverse` or the hotspot). |

## Built beyond Chapter 4

These were added after the proposal: from the Webmasters Kenya (SOFIA) review, the supervisor's feedback or the lecturer's demo feedback. They have no Chapter 4 ID.

| Addition | Where | Reason |
|---|---|---|
| Content status (Draft, Under Review, Published) | `activities/models.py` | SOFIA: only reviewed content reaches caregivers |
| Offline use | `recommendation_cache.dart` | SOFIA |
| Non-comparative progress | Progress tab, tracker, weekly observation | SOFIA |
| Privacy notice and consent (Kenya Data Protection Act 2019) | `profiles/privacy.py` | SOFIA; NFR-03 |
| Data-protection split with Webmasters Kenya | Open, see [deployment_requirements.md](deployment_requirements.md) | SOFIA; to agree with the client |
| Clinic-visit referral | `profiles/rules/referral.py` | Gap analysis; NFR-11 |
| Options after feedback, personalisation, interest level | `recommendations/options.py`, `personalisation.py` | Lecturer feedback |
| Activity area and age classifier (logistic regression on SBERT vectors) | `activities/classifier.py` | Machine learning on the curated labels; [activity_classifier_results.md](activity_classifier_results.md) |
| Learned ranker experiment | `recommendations/learned_ranker.py` | Compared with the formula; α = 0.7 kept ([experiment_learned_ranker.md](experiment_learned_ranker.md)) |
| Milestone tracker and weekly Nurtura observation | `profiles/tracker.py`, `observation.py` | Wireframe Figure 4.8; template-based, not AI |
| Explore: browse, search and saved activities | `recommendations/browse.py`, Explore tab (#194) | Wireframe Figure 4.9 |
| Language toggle | Not built | SOFIA suggestion; English only, see [known_limitations.md](known_limitations.md) |

## Wording to update in Chapter 4

Where the system differs from the wording, Chapter 4 (or Chapter 5, as a recorded deviation) should say so:

- **FR-01:** administrators are created with `createsuperuser` or the web admin, not by registration.
- **FR-03, DR-02:** preferences and context are not collected, or are future work.
- **FR-04, DR-03:** milestones come from the CDC/WHO catalogue with status Achieved, Emerging or Not yet; developmental goals are not collected.
- **FR-05:** a custom IF-THEN engine (not experta).
- **FR-10:** ranking is `age_weight × ((1 − α)·similarity + α·priority)`; preferences and context aren't weighted.
- **FR-11, NFR-10:** explanations name the area, milestones or concerns, age fit and interests; scores aren't shown to caregivers.
- **NFR-01:** a measurable threshold, for example "95% of requests within 1 second after start-up on the reference environment".
- **NFR-08:** Android only.
- **NFR-12:** relevance judged by graded human labels with precision@k and nDCG@k, not similarity scores.
- **DR-09 and Section 3.2.2:** vectors stored in PostgreSQL, not FAISS.
- **Additions:** state the SOFIA additions above, with their own IDs if the chapter is renumbered.
