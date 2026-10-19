# Sprint II review: requirements and evidence

> **Last updated: 2026-10-19,** for `main` at `cddefe5`. This sheet sets the course's Sprint I and Sprint II requirements against what the repository shows, so each can be checked at the review. Items marked **Author** are outside the repository (the report chapters, and agreeing scope with the supervisor) and are listed so nothing is forgotten.

**Course sprints and project sprints.** The repository's plan ([DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)) uses finer-grained sprints. Course Sprint I (data and environment) corresponds to project Sprints 1–3.5; course Sprint II (core functionality, integration and initial testing) corresponds to project Sprints 4–8, plus the testing records.

## Sprint I: data preparation and development environment

| Requirement | Status | Evidence |
|---|---|---|
| Development environment configured | Met | [README](../README.md): prerequisites, backend and mobile setup, environment variables, PostgreSQL |
| Clean, organised codebase with setup and run instructions | Met | README layout and "From an empty database to working recommendations"; one Django app per concern (`profiles`, `activities`, `recommendations`, `feedback`, `insights`) |
| Git with meaningful commits; no secrets in the repository | Met | 150 commits on `main`, 59 merged pull requests; an issue, branch and Conventional Commit message for each change. `.env` is gitignored, `.env.example` holds placeholders only, and the secret key comes from the environment. A scan of tracked files found no keys or passwords (2026-10-19) |
| Data prepared and checked; source, preparation and ethics documented | Met | [data/README.md](../data/README.md): schema, controlled vocabularies, the validating cleaning script, sources, and "Access, privacy and ethics". Milestone catalogue with citations; evaluation labels with a provenance file |
| Automation where it helps | Met | Makefile (`setup`, `seed-data`, `test`); GitHub Actions running backend and app tests on every change; black on commit; idempotent seeding commands; a provenance check for the evaluated state; an end-to-end test on a real phone |
| Earlier chapters corrected; Chapter 4 matches the system | **Author** | Report chapters are kept outside the repository. Design changes to reflect: two-step sign-in, the tabbed app and offline use, the analytics dashboard, and preference/contextual weighting recorded as out of scope (#53) |

## Sprint II: core functionality, integration and initial testing

| Requirement | Status | Evidence |
|---|---|---|
| Sprint tasks linked to objectives; done, in progress and blocked | Met (objectives: **Author**) | The task list below, linked to requirement IDs and issues. Linking each to the approved objective numbers needs the objectives from Chapter 1 |
| Scope and priorities validated with the supervisor | **Author** | – |
| A working core workflow from input through processing to output | Met | A phone run on 2026-10-15 (and again on the restyled app on 2026-10-15): register with an emailed code, create profiles, record a milestone, get ranked recommendations with explanations, mark done, rate ([testing record §1](testing_and_evaluation_record.md), screenshots in [evidence/e2e_2026-10-15](evidence/e2e_2026-10-15/)) |
| Components integrated; data moves correctly; usable output | Met | Flutter app → Django REST API → PostgreSQL → rule engine → SBERT retrieval → weighted ranking → explanations → app. The backend's request log for each step is in the testing record |
| Initial testing: expected behaviour, invalid inputs, failure conditions, with a record | Met | 388 backend and 78 app tests, all passing; 31 invalid-input and failure-condition tests listed with input, expected and actual results; 9 defects with their corrections ([testing record](testing_and_evaluation_record.md)) |
| Evaluation evidence: a baseline and a justified validation approach (AI/ML) | Met | Baseline: SBERT similarity alone. The hybrid ranking was tuned on 11 children and tested on 8 held-out ones, with the split and selection rule fixed before labelling. nDCG@5 0.452 → 0.814 ([sprint5_alpha_results.md](sprint5_alpha_results.md)). See "Evaluation workflow" below |
| Data validation and access controls (information system) | Met | Field validation on every write; caregivers only reach their own children (404 otherwise); administrators are kept out of caregiver data and see feedback without family details; two-step sign-in; rate limits ([testing record](testing_and_evaluation_record.md), "Invalid inputs and failure conditions") |
| Chapter 5 updated, with screenshots and test records; Chapter 4 diagrams updated | **Author** | Material to draw on: [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md), the testing record, [evidence/](evidence/) and this sheet |
| Up-to-date repository, run instructions, reproducible version | Met | README; tags `sprint5-eval-v1` (evaluated ranking) and `sprint6-explanations-v1`; CI on every change |
| Known limitations and outstanding defects documented honestly | Met | [known_limitations.md](known_limitations.md) |
| Deployment requirements identified for Sprint III | Met | [deployment_requirements.md](deployment_requirements.md): what runs, measured memory, production settings, the deploy check's warnings, platform options |
| An AI suggestion that was checked, with what was accepted or rejected | **Author** | To present at the review |

## Evaluation workflow (how the AI/ML guidance applies)

Nurtura uses a **pretrained** sentence model (`all-MiniLM-L6-v2`) without fine-tuning, so there is no training step and no training data to leak into evaluation. The guidance's principles are applied to the part that *is* tuned, the ranking weight α:

- **Question and baseline:** does combining rule-engine priority with semantic similarity rank more relevant activities than similarity alone? The baseline is SBERT similarity alone.
- **Separate data:** 20 held-out children, split *before labelling* into 11 for tuning, 8 for testing and 1 content-gap child reported separately. α was chosen on the tuning children only, by a rule written down beforehand. The test children were scored once.
- **Recorded versions:** the evaluated code is tag `sprint5-eval-v1`. The provenance file records hashes of the 54 activities, the rule weights, the ranking settings, the model files, the stored vectors and the label sheet. `evaluate_alpha_grid --check-provenance` confirms nothing has changed since; it matched on 2026-10-19.
- **Reproducible:** the run is deterministic (ties are broken by fixed rules), and it reruns locally with one command (`evaluate_alpha_grid`) from the repository. A notebook environment (Colab) wasn't needed, because there is no GPU training.
- **Results kept, including unfavourable ones:** the test set preferred the α = 0 ablation, and one content-gap child did worse. Both are reported, not hidden.

## Tasks

**Done in Sprint II** (project Sprints 4–8; each linked to its issue):

| Area | Requirement | Issues |
|---|---|---|
| Semantic retrieval with SBERT | FR-06 | #29, #30, #34 (hand check #31 waiting) |
| Weighted ranking; α chosen on held-out children | FR-07 | #35, #36, #37, #44, #46, #48, #50 |
| Stored, traceable recommendations end to end | FR-07, FR-11 | #52, #60 |
| Plain-language explanations | FR-11 | #69, #70, #76 |
| Mark done; feedback through `FeedbackManager`; admin review | FR-14, FR-15, FR-16 | #94, #95, #96 |
| Mobile: recommendations, activity details, done and feedback, progress | Sprint 8; NFR-15 | #82, #84, #100, #90 |
| Offline use | NFR-14 | #85, #102 |
| Two-step sign-in by emailed code | Security | #86, #91 |
| End-to-end test on a real phone | Testing | #104, #108 |
| Testing and evaluation record; analytics dashboard; village restyle | Evidence; usability | #110, #116, #112, #114 |

**In progress / waiting:**

| Task | State |
|---|---|
| Explanation reader test (5 readers) | Materials ready; needs readers. Explanation wording stays frozen until it's scored |
| Hand check of retrieval results (#31) | Generated; needs the researcher's judgements |

**Outstanding (next sprint):**

| Task | Notes |
|---|---|
| Host the system (Sprint III) | [deployment_requirements.md](deployment_requirements.md); platform to agree |
| Caregiver evaluation: relevance, personalisation, explainability, SUS, satisfaction | Recruit participants now; longest lead time |
| Full requirement-to-test map | Needs the Chapter 3 requirement list |
| Language toggle (NFR-16) or English-only as a limitation | Decision needed |
| Verify the remaining 108 CDC milestones | After the reader test (the catalogue is frozen until then) |
| Password reset; app-side child editing | Not yet built ([known_limitations.md](known_limitations.md)) |

## Demonstrating at the review

Follow [demo_checklist.md](demo_checklist.md): backend on the laptop, phone over USB, the round trip on the phone, then the admin dashboard and feedback review in the browser. The screenshots in [evidence/e2e_2026-10-15](evidence/e2e_2026-10-15/) are the fallback if anything fails on the day.
