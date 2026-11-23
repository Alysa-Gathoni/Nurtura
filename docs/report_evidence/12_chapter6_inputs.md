# Chapter 6 inputs

> Generated 2026-11-23T10:55:47+03:00 at commit `36a36a4` by `backend\venv\Scripts\python.exe scripts\report_evidence\chapter6.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

## 5a. Open issues, TODO/FIXME and known defects

**Open issues** (`gh issue list --state open`; `raw/open_issues.csv`): 1.

| # | Title | Labels | Milestone | Opened |
|---|---|---|---|---|
| 274 | Add the graded v3 pairs and complete the full v3 evaluation | test | Sprint 9: Evaluation | 2026-11-23 |

**TODO / FIXME / XXX / HACK comments** in backend, app and scripts code (`raw/todo_fixme.csv`): 0.

None found.

**Known defects** (`docs/known_limitations.md`, "Outstanding defects"):

- line 7: None known. Every defect found so far has been fixed and is recorded with its correction in [testing_and_evaluation_record.md](testing_and_evaluation_record.md) (section 3).

## 5b. Stated limitations

60 statements (`raw/limitations.csv`): every item in `docs/known_limitations.md`, lines that say "limitation" elsewhere in the README and docs, and code comments that state a limitation.

| Source | Statement |
|---|---|
| docs/known_limitations.md:13 | Explanation reader test (5 non-technical readers) / Materials ready ([explanation_reader_test.md](explanation_reader_test.md)); not run. Until it's scored, explanation wording and the evaluated ranking stay frozen / Before Sprint 9 |
| docs/known_limitations.md:14 | Evaluation with caregivers: relevance, personalisation, explainability, usability (SUS), satisfaction / Materials drafted ([caregiver_evaluation.md](caregiver_evaluation.md)); tasks inspected by a cognitive walkthrough, which finds likely problems but gives no |
| docs/known_limitations.md:18 | **Small and constructed.** α was chosen on 11 tune children and checked on 8 test children. They are realistic but hypothetical profiles. The results describe these children only and support no statistical claims ([sprint5_alpha_results.md](sprint5_alpha_resul |
| docs/known_limitations.md:19 | **Two raters, one of them the designer** (#218). The v2 labels are the researcher's. A registered nurse graded all 257 rows independently and blind: quadratic-weighted κ 0.661 (95% CI 0.589–0.718), with the nurse usually one grade stricter. The main result hol |
| docs/known_limitations.md:20 | **v2 kept α = 0.7 against the rule's choice** (#170). On 449 activities the rule fixed before labelling chose α = 1.0, but at α = 1.0 ties are broken by activity ID, which puts the first-written activities first. α = 0.7 was kept and reported (test nDCG@5 0.83 |
| docs/known_limitations.md:21 | **Recommendations concentrate on the priority area** (#199). At α = 0.7 a top 5 covers about 1.4 of the five areas on average, by design. A child flagged in one area sees few ideas from the others in Today; Explore lets caregivers browse every area. See [eval_ |
| docs/known_limitations.md:22 | **The age weights were never tuned** (1 / 0.7 / 0.5 / 0.25 / 0.1). The v2 sensitivity check (#196) found that softer, harsher, symmetric and reversed weights give the same top 5 for every test child, so the exact values don't drive the results. Rule priority o |
| docs/known_limitations.md:23 | **Retrieval mixes SBERT with TF-IDF at β = 0.25** (#248, #250). |
| docs/known_limitations.md:29 | **α is a reasonable default, not an optimum.** The test set preferred the α = 0 ablation (nDCG@5 0.873 against 0.814 for α = 0.7), and the tune curve is flat from 0.4 to 1.0. |
| docs/known_limitations.md:30 | **Only the top 5 were labelled,** so the metrics can't be extended beyond k = 5. |
| docs/known_limitations.md:34 | **54 Published activities, 396 more awaiting review** (batch 5, #156, and batch 6, #158). Five whose source did not support them were removed in #160, including `ACT-0021`, one of the original 54. The 54 Published ones were uneven: Socio-Emotional 17, Language |
| docs/known_limitations.md:35 | **The options after feedback follow simple rules** (#177). Each thing that went wrong maps to one rule: too hard means a lower difficulty or the age band below, no materials means an activity listing none, and so on, with ties broken by how similar the activit |
| docs/known_limitations.md:36 | **Activity difficulty levels are future work** (#262). Each activity has a difficulty label, but of the 449 Published activities 399 are Beginner, 49 Intermediate and 1 Advanced, and the ranking doesn't use it. Only the "too hard" and "too easy" options after  |
| docs/known_limitations.md:37 | **Learning from feedback is per child and simple** (#179). After the evaluated ranking, each score moves by up to 0.25 towards activities similar to ones that went well and away from ones similar to ones that didn't work (cosine similarity of the stored embedd |
| docs/known_limitations.md:38 | **The activity classifier only suggests** (#181). It predicts an activity's area (cross-validated accuracy 0.764) and age band (0.541; 0.862 within one band) from its text, for admin suggestions and review flags. Its labels came with the content, so agreement  |
| docs/known_limitations.md:39 | **Skills seen during an activity are recorded as Emerging** (#185). The "Well done!" sheet offers milestones of the activity's area that are due or coming up; ticking one records it as Emerging ("sometimes"), because seeing a skill once doesn't show it is secu |
| docs/known_limitations.md:40 | **The Nurtura observation is written from templates** (#192). The weekly card on the Milestones tab is built from the child's own records (activities tried and how they went, milestones noted, the rule engine's focus area) using fixed sentences, not a language |
| docs/known_limitations.md:41 | **Explore's search is by meaning, not by words** (#194). A search is encoded with SBERT and compared with the activity embeddings, so it finds related activities without exact words, but an exact name isn't guaranteed to come first. "Quick" means a Beginner ac |
| docs/known_limitations.md:42 | **The clinic-visit suggestion is simple** (#161). It appears when at least one CDC or WHO milestone the child is past the expected age for is marked "Not yet", following CDC's "one or more milestones" advice. It can't notice lost skills (CDC's other sign), "Em |
| docs/known_limitations.md:43 | **Sensory has no guideline milestones.** The CDC and WHO checklists have no Sensory category, so Sensory priority comes only from caregiver concerns and interests. |
| docs/known_limitations.md:44 | **The milestone catalogue paraphrases CDC in places** (#235). All 133 milestones are verified against their sources. 28 of the 127 CDC entries leave out CDC's example or reword it slightly, and all use "they" where CDC alternates he and she; ages and domains a |
| docs/known_limitations.md:45 | **English only.** A language toggle (a SOFIA suggestion, not in Chapter 4) is undecided; if it isn't built, English-only is a stated limitation. |
| docs/known_limitations.md:49 | **Ideas come as a weekly plan** (#244), Monday to Sunday (#253), the same weeks as the streak. A plan made mid-week starts on that week's Monday, so its first week is shorter; one made on a Sunday runs to the following Sunday instead of lasting one day. Plans  |
| docs/known_limitations.md:50 | **Portrait only** (#214). The app is locked to portrait on Android. The screens weren't designed for landscape, and Milestones overflowed when the phone was turned. |
| docs/known_limitations.md:51 | **Not hosted yet.** The backend runs on a laptop. The phone reaches it over USB (`adb reverse`), because campus Wi-Fi blocks devices from reaching each other. Hosting is Sprint III ([deployment_requirements.md](deployment_requirements.md)). |
| docs/known_limitations.md:52 | **The server address is built into the app** at build time (`--dart-define=API_BASE_URL`). A new address means rebuilding the app. |
| docs/known_limitations.md:53 | **Android debug builds only.** No signed release build yet (the app has been tested on an Android phone, in Chrome, and on four emulated configurations from Android 7.0 at 360 × 640 dp to a tablet, all passing the end-to-end test; see [device_tests.md](device_ |
| docs/known_limitations.md:54 | **Offline use is partial.** The last recommendations and the child list are kept on the phone and shown offline. Recording milestones, Progress, and marking done or rating need a connection, and actions taken offline aren't queued. |
| docs/known_limitations.md:55 | **Deleting an account is immediate and final** (#134). A caregiver deletes their account, with all their children's data, from the Family tab after confirming their password (or, for an account made with Google that has no password, its email); there is no gra |
| docs/known_limitations.md:56 | **Sessions last 30 days, then end** (#162). A log-in token stops working 30 days after it was issued, however often it is used, so a caregiver logs in again about once a month (fingerprint log-in makes that quick). There is no sliding renewal or refresh token. |
| docs/known_limitations.md:57 | **Fingerprint log-in is per phone** (#150). Turning it on gives the phone a random key from the server, kept in the phone's secure storage and sent only after Android's own fingerprint check (the phone's PIN or pattern is accepted too). The fingerprint never r |
| docs/known_limitations.md:58 | **The email address can't be changed** in the app. Doing it safely needs a code sent to the new address first, so nobody can take over an account by typing someone else's email. A caregiver can delete the account and register again, or ask the privacy contact  |
| docs/known_limitations.md:59 | **Continue with Google is Android only** (#130). Chrome needs its own OAuth client and set-up. Each signing key (every laptop's debug key, and the release key) needs its SHA-1 registered, and while the consent screen is in *Testing* only listed test users (up  |
| docs/known_limitations.md:60 | **The privacy notice gates only a child's own data** (#136). Until a caregiver agrees to the current notice, adding or changing a child and recording milestones are refused; generating ideas, marking done and rating for children who already exist are not. Acco |
| docs/known_limitations.md:61 | **Registration says when an email is already registered,** so an address's account can be confirmed there, although the password-reset request deliberately doesn't say. |
| docs/known_limitations.md:62 | **Sign-in codes need email.** With no internet, codes can only be read from the backend console (development). The Gmail account used for sending has a daily sending limit (about 500 messages). |
| docs/known_limitations.md:63 | **"Active caregivers" is approximate.** Token sign-ins don't update Django's `last_login`, so the admin dashboard counts a caregiver as active if they generated ideas, recorded a milestone, or marked done or rated in the last 7 days. |
| docs/known_limitations.md:64 | **Memory and start-up.** With the SBERT model loaded, the backend committed about 1.2 GB of memory on the development laptop. Without the warm-up, the first recommendation after a start takes about 14–15 s ([performance_recommendations.md](performance_recommen |
| docs/known_limitations.md:65 | **Load tested on the laptop only** (#224, #226). The first run, on the development server, failed about half the requests at 200 caregivers at once, because PostgreSQL's 100 connections ran out. A connection pool, fewer PyTorch threads per request, a query-emb |
| docs/known_limitations.md:66 | **The end-to-end test needs a person** to type the emailed code. It can't run unattended in CI. |
| docs/known_limitations.md:67 | **The admin's fonts come from Google Fonts.** Offline, the admin falls back to system fonts. |
| README.md:7 | **Where things stand:** see [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) for the project in plain language, [docs/sprint_ii_review.md](docs/sprint_ii_review.md) for the current sprint status, and [docs/known_limitations.md](docs/known_limitations.md) f |
| README.md:307 | / [docs/known_limitations.md](docs/known_limitations.md) / Known limitations and outstanding defects / |
| docs/activity_classifier_results.md:102 | ## Limitations |
| docs/alpha_sensitivity_tfidf.md:14 | - **Reading:** apply the v2 α rule (every α within 0.02 of the best tune mean qualifies; the middle of that range wins). If 0.7 is within 0.02 of the best, the check supports it; otherwise it's a limitation for Chapter 5. |
| docs/cognitive_walkthrough.md:104 | / 3 / The clinic message appears after a single "Not yet" / B3 / 3 / Keep (it follows CDC), and watch reactions in the sessions; have the wording reviewed by a health worker (already a known limitation). / |
| docs/cognitive_walkthrough.md:110 | / 9 / Search and all text are English only / B2 / 2 / Known limitation (English only). / |
| docs/cognitive_walkthrough.md:117 | ## Limitations |
| docs/DEVELOPMENT_PLAN.md:359 | - Language toggle if keeping NFR-16, otherwise confirm Limitations notes |
| docs/eval_v2_beyond_accuracy.md:48 | ## Limitations |
| docs/eval_v2_results.md:116 | ## Limitations |
| docs/eval_v2_statistics.md:152 | ## Limitations |
| docs/load_test_results.md:90 | ## Limitations |
| docs/PROJECT_OVERVIEW.md:197 | - **Language toggle (a SOFIA suggestion):** build it, or record English-only as a limitation. |
| docs/sprint5_alpha_results.md:131 | **On test, the α = 0 ablation scored higher than the chosen α**: mean nDCG@5 was 0.873 against 0.814. On tune it was the other way round (0.737 against 0.873). Rule priority helped more on the tune children than on the test children. In particular, α = 0 alrea |
| docs/sprint5_alpha_results.md:156 | ## Limitations |
| docs/sprint_ii_review.md:31 | / Known limitations and outstanding defects documented honestly / Met / [known_limitations.md](known_limitations.md) / |
| docs/sprint_ii_review.md:79 | / Language toggle (NFR-16) or English-only as a limitation / Decision needed / |
| docs/testing_and_evaluation_record.md:180 | **Limitations:** small numbers, one rater who also designed the system, and constructed (not real) children. The test set preferred the α = 0 ablation (nDCG@5 0.873), so 0.7 is a reasonable default rather than an optimum. Caregiver feedback in Sprint 9 is the  |
| backend/recommendations/management/commands/alpha_sensitivity.py:127 | f"{TOLERANCE}: record it as a limitation." |

## 5c. Decision log

From the "decisions" sections of merged pull requests (8 PRs, 32 decisions), grouped by theme by keyword. `raw/decision_log.csv`.

### Content and data

| Merged | PR | Decision |
|---|---|---|
| 2026-09-29 | #10 | **Status values are stored as `draft` / `under_review` / `published`** (displayed as Draft / Under Review / Published), matching the other status fields. Unlike domain/age range, this field isn't in the CSV. |
| 2026-09-29 | #10 | **Anyone with admin access can publish for now.** Restricting publishing to the Administrator role comes with role-based auth in #4. |
| 2026-09-29 | #10 | **Editing a Published activity doesn't send it back to review.** Admins can use *Return to Draft* first if an edit needs re-review. This could be automated later if the proposal requires it. |
| 2026-09-29 | #10 | **Existing recommendations are unaffected by unpublishing.** If a published activity is returned to Draft, its past recommendations stay in history (activities with recommendations can't be deleted, from #2). However, editing and re-saving one of those old recommendations in the admin will fail vali |
| 2026-09-29 | #9 | **Activities referenced by a recommendation can't be deleted** (`on_delete=PROTECT`). This keeps each child's recommendation history and feedback intact; activities should be retired by unpublishing them via `content_status` (#3) rather than deleted. |
| 2026-09-29 | #8 | **`source` field on `DevelopmentalActivity`** — not in the class diagram, but every dataset row has one and `data/README.md` requires traceability. Needed for seeding in #5 without losing that information. |
| 2026-09-29 | #8 | **`activity_id`** is a unique `CharField` (e.g. `ACT001`) matching the dataset; Django's auto `id` stays the primary key. |
| 2026-09-29 | #8 | **Unique constraint on (lower(activity_name), developmental_domain)** — mirrors the duplicate check in `clean_activities.py`, enforced by the database. |

### Evaluation

| Merged | PR | Decision |
|---|---|---|
| 2026-09-29 | #9 | **`ranking_score` has no bounds** yet; its range depends on the α weighting designed in Sprint 5. |
| 2026-10-01 | #20 | **Max-normalization (top domain = 1.0)** rather than scores summing to 1. It keeps the rule signal on the same 0–1 scale as cosine similarity for the α-weighted ranking in Sprint 5; with a sum-to-1 split the top domain would often be only around 0.3. If your proposal specifies a different normalizat |
| 2026-10-08 | #33 | **The query is text, not a vector average.** Describing the profile in words lets SBERT match it like any sentence, keeps the semantic signal **independent** of the rule engine's domain *labels* (activity embeddings exclude the domain label; #32), and the query is readable, which helps the Sprint 6  |
| 2026-10-08 | #32 | **What's embedded:** `name. goal. description.` and **not the domain label**. Domain priority already comes from the rule engine, and Sprint 5 combines both signals with α, so including the domain in the text would count it twice. It's a one-function change (`activity_text`) if you'd rather follow t |

### Other

| Merged | PR | Decision |
|---|---|---|
| 2026-09-29 | #9 | **`generateExplanation()` is not in this PR.** It belongs to the explainability module (Sprint 6); the `explanation` field is ready for it. |
| 2026-09-29 | #9 | **Feedback has no direct caregiver field.** The submitter is reachable through `feedback.recommendation.child.caregiver`, matching the class diagram. |
| 2026-09-29 | #8 | **`date_of_birth` accepts future dates** so a prenatal profile can store the expected due date. |

### Ranking and rules

| Merged | PR | Decision |
|---|---|---|
| 2026-09-29 | #9 | **`similarity_score` is limited to [-1, 1]** (the cosine similarity range) and **`rating` to 1–5**, both by form validators *and* database check constraints, so bad values can't get in through the ORM either. |
| 2026-09-29 | #8 | **Milestone status values** (Achieved / Emerging / Not yet) are a proposal — the class diagram doesn't define them. Worth confirming before the rule engine (Sprint 3) depends on them. |
| 2026-10-01 | #21 | **Rules use catalogue entries whether or not they're verified yet**, so the engine works while you verify. If you'd rather only verified entries count (safer for production, but nothing fires until you've checked entries), it's a one-line filter. |
| 2026-10-01 | #21 | **Unlinked milestones don't fire rules.** A free-text milestone has no due age. The mobile app (Sprint 8) should record milestones by picking from the catalogue. |
| 2026-10-01 | #21 | **Upcoming (+2), concern (+5), sensory interest (+2) and the sensory keyword list** are my proposals; the ASQ-3 convention only fixes 10/5. Worth stating in your methodology alongside the 10/5 derivation. |
| 2026-10-01 | #21 | **"Due" uses the child's current age**, so a milestone last observed as Not yet before it was due counts once the child passes the expected age, until a newer observation is recorded. |
| 2026-10-01 | #20 | **Additive adjustments.** Several delayed milestones in one domain add up, so a domain with more concerns ranks higher. There's no rule chaining, which is simpler than `experta` and enough for milestone-to-domain rules. |
| 2026-10-01 | #20 | **No database model for the profile.** It's computed on demand from current data, so it can't go stale. It could be persisted later if Sprint 6 or Sprint 9 needs a history of profiles. |
| 2026-10-08 | #33 | **Focus threshold 0.5.** Only domains the rules clearly raised shape the query, so small interest boosts (e.g. Sensory 0.27 from "music") don't dilute it. |
| 2026-10-08 | #33 | **Prenatal ↔ postnatal is a hard filter, not a weight.** A pregnancy activity is never right for a born baby, whatever its similarity. |
| 2026-10-08 | #32 | **Batch, not on publish:** embeddings are refreshed by running the command after publishing or editing, as the plan's "batch precompute" describes. #30's retrieval only uses activities that are both Published **and** embedded. |
| 2026-10-08 | #32 | **Stored as bytes, not JSON:** compact and fast to load into a numpy matrix for retrieval. |

### Security and privacy

| Merged | PR | Decision |
|---|---|---|
| 2026-09-29 | #13 | **Token auth over JWT.** DRF's built-in tokens need no extra package, and the mobile app already has `flutter_secure_storage` to hold them. Tokens don't expire; logout deletes them. JWT with expiry (`djangorestframework-simplejwt`) is a straightforward swap later if NFR-02 requires expiring sessions |
| 2026-09-29 | #13 | **Administrators can't use the child-profile API** (403). They manage content, not children's data, which fits the data-protection requirement (NFR-03). Superusers can still see children in the Django admin. |
| 2026-09-29 | #13 | **Email is required and unique, but not verified** (no email sending is configured). |
| 2026-09-29 | #13 | **Throttle counts live in Django's cache.** The default in-memory cache is per process, which is fine for development. A multi-process production deployment should point `CACHES` at a shared cache (e.g. Redis) so the limit applies across processes. |
| 2026-09-29 | #9 | **Deleting a child or a recommendation cascades.** A child's recommendations go with the child, and a recommendation's completion and feedback go with the recommendation. |


## 5d. Handover

| Task | How | Where |
|---|---|---|
| Run the backend | `cd backend`, activate the venv, `pip install -r requirements-dev.txt`, `python setup_sbert.py`, `python manage.py migrate`, then `make run-backend` (or `NURTURA_MODEL_WARMUP=1 python manage.py runserver`) | README.md:63; Makefile:31 |
| Run the app | `cd mobile/nurtura_app`, `flutter pub get`, `adb reverse tcp:8000 tcp:8000`, `flutter run -d <device> --dart-define=API_BASE_URL=http://127.0.0.1:8000` | mobile/nurtura_app/README.md |
| Add an activity | In the app as an administrator: Activities → add; or the web admin. New activities start as Draft | backend/activities/api.py:62; backend/activities/models.py:26 |
| Publish it | Draft → Under Review → Published (skipping review is refused); then `python manage.py embed_activities` if the app didn't embed it | backend/activities/models.py:26; backend/recommendations/management/commands/embed_activities.py |
| Bulk-load activities | `python manage.py seed_activities` (validates every row; new rows are Draft) | backend/activities/management/commands/seed_activities.py |
| Change α | Set `RANKING_ALPHA` in `backend/.env` and restart; stored batches record the α they used | backend/nurtura_backend/settings.py:316 |
| Change a rule or its weight | Edit the constants or `Rule` objects, then run the tests; the ranking version changes | backend/profiles/rules/guidelines.py:29 |
| Rerun the evaluation | `python manage.py evaluate_alpha_grid --check-provenance`, then `evaluate_alpha_grid --markdown --report-alpha 0.7`, `evaluate_statistics`, `evaluate_beyond_accuracy`. A changed rule, α, activity or embedding makes the provenance check fail: label the new pool first | data/evaluation/README.md:14 |
| Regenerate this evidence pack | `powershell -File scripts\report_evidence\run_all.ps1` | scripts/report_evidence/run_all.ps1 |
