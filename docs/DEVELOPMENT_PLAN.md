# Nurtura — Development Plan & GitHub Workflow

Ordered by dependency, not by calendar date. Sprint 1 (environment setup) is already
complete.

---

## Part A — Working GitHub Like a Junior Full-Stack Dev

This is the one-time setup, done once now, then reused for every sprint below. The
goal is a repo history that looks like real engineering practice, not a pile of
"final_v2" commits.

### 1. Milestones = Sprints

In GitHub → Issues → Milestones, create one milestone per sprint below (Sprint 2
through Sprint 10). Leave due dates blank since yours aren't fixed, or set soft
target dates you can move. Put each sprint's "Definition of Done" text directly
into the milestone's description field — that description becomes your own
checklist for closing it.

### 2. Issues = individual tasks

Every discrete piece of work — a model, an endpoint, a screen, a bug — gets its own
Issue, assigned to the relevant Milestone. Each sprint section below lists example
Issues you can create almost verbatim. Use labels to keep things scannable:

```
feature   — new functionality
bug       — something broken
docs      — documentation/report updates
test      — test coverage
sofia     — items tied to the SOFIA alignment fixes
```

### 3. Branches — one per issue

Never commit directly to main. For each Issue, branch off main using this naming
convention:

```
feature/<issue-number>-<short-description>
fix/<issue-number>-<short-description>
docs/<issue-number>-<short-description>

# Examples
feature/12-rule-engine-milestone-evaluation
feature/18-sbert-batch-embedding-pipeline
fix/24-migration-null-constraint
docs/31-chapter5-implementation-draft
```

```bash
git checkout main
git pull
git checkout -b feature/12-rule-engine-milestone-evaluation
```

### 4. Commit messages — Conventional Commits

Use this format so your history is readable and each commit says what it actually
did:

```
<type>: <short description> (#<issue-number>)

feat: implement rule engine milestone evaluation (#12)
feat: add SBERT batch embedding pipeline (#18)
fix: correct null constraint on activity migration (#24)
docs: draft Chapter 5 implementation section (#31)
test: add unit tests for weighted ranking function (#20)
```

Types to use: **feat**, **fix**, **docs**, **test**, **chore** (setup/config/
dependencies), **refactor**.

### 5. Pull Requests — even solo

When a branch is ready, open a PR into main rather than merging locally. This is
what makes your repo look like real practice instead of a personal notebook:

```bash
gh pr create --title "feat: rule engine milestone evaluation" \
  --body "Implements FR-05. Closes #12." --base main
```

In the PR description, always include **"Closes #\<issue-number\>"** — GitHub will
auto-close the Issue and move its card to Done when the PR merges. Give yourself a
2-minute self-review pass (read your own diff before merging) rather than merging
blind — this is genuinely what junior devs are expected to do, solo project or not.
Then:

```bash
git checkout main
git pull
git branch -d feature/12-rule-engine-milestone-evaluation
```

### 6. GitHub Projects board

Create a Projects (Kanban) board with columns: **Backlog → In Progress → In Review
→ Done**. Add every Issue to it. Drag cards as you work — this is your visible
"appropriate use of automation for workflow management," and it's the first thing
worth pulling up on screen during a progress check.

---

## Part B — Sprint-by-Sprint Plan

Activity curation and your dev log run continuously across every sprint below, not
as their own blocks — see the running notes at the end.

---

### Sprint 2 — Core Data Layer

**GitHub Milestone:** "Sprint 2: Core Data Layer"

**Entry condition:** Environment setup complete, SBERT installed and verified.

**Build:**
- Django models for all four apps, matching your class diagram exactly —
  `ChildProfile`, `DevelopmentalActivity` (including `content_status`:
  Draft/Under Review/Published), `DevelopmentalMilestone`, `Recommendation`,
  `CompletedActivity`, `Feedback`.
- Migrations run against PostgreSQL, matching your Logical Database Schema
  (Section 4.4.2).
- User authentication with role separation (Caregiver / Administrator) — FR-01,
  FR-02, NFR-02, NFR-03.
- Admin interface for Activity Repository management including `content_status` —
  FR-13, DR-12 (SOFIA content-validation fix).
- Load your curated CSV batch into PostgreSQL as seed data.

**Example Issues to open for this milestone:**
```
#10 feat: create ChildProfile, DevelopmentalActivity, DevelopmentalMilestone models
#11 feat: create Recommendation, CompletedActivity, Feedback models
#12 feat: add content_status field + admin workflow (FR-13, DR-12)
#13 feat: caregiver/administrator role-based authentication (FR-01, FR-02)
#14 chore: seed database from data/processed/activities_clean.csv
```

**Definition of done:** You can create a caregiver account, create a child profile,
and insert a Published activity via the admin — all persisted in PostgreSQL.
`python manage.py test` runs cleanly.

---

### Sprint 3 — Developmental Profiling (Rule Engine)

**GitHub Milestone:** "Sprint 3: Rule Engine"

**Entry condition:** Core models exist; at least one child profile can be created.

**Build:**
- Rule engine implementation (`experta`, or your documented custom IF-THEN
  fallback).
- Rules derived from WHO/CDC/ASQ guidelines mapping milestones/concerns/
  observations to per-domain priority scores.
- `DevelopmentalProfile` construction logic (FR-05) — normalized 0–1 priority
  scores across the five domains.

**Example Issues to open for this milestone:**
```
#15 feat: implement rule engine core evaluator (FR-05)
#16 feat: encode WHO/CDC/ASQ milestone-to-domain rules
#17 test: unit tests for DevelopmentalProfile scoring
```

**Definition of done:** Given a sample input (e.g. "language milestone delayed"),
the engine returns a profile with Language correctly weighted higher — captured as
an actual test case, not a manual check.

---

### Sprint 3.5 — Minimal Mobile Shell (thin-slice checkpoint)

**GitHub Milestone:** "Sprint 3.5: Minimal Mobile Shell"

**Entry condition:** Sprint 3 merged — models, auth, and the rule engine all exist
and are reachable via Django REST Framework's browsable API or admin.

**Why this sprint exists:** the full recommendation pipeline (Sprints 4–6) is one
inseparable chain — there's nothing meaningful to show on screen until SBERT,
ranking, and explainability are all done together on top of the rule engine.
Waiting until Sprint 8 to build any mobile UI means going five more sprints
without visual proof the Flutter ↔ Django ↔ PostgreSQL round trip actually works.
This sprint proves that round trip now, while integration problems (CORS, auth
tokens, serialization) are still cheap to fix — and while you have a real,
working rule engine behind it, not just empty models.

**Build:**
- Flutter registration/login screen, calling the real Django auth endpoint (no
  mock data).
- Child profile creation screen, writing a real `ChildProfile` record to
  PostgreSQL through the API.
- Milestone recording screen, feeding the real rule engine from Sprint 3 —
  submitting a milestone observation and confirming a `DevelopmentalProfile` is
  actually generated server-side (the profile itself doesn't need to be displayed
  to the caregiver yet; confirming it's created is enough for this checkpoint).
- Nothing recommendation-related yet — SBERT/ranking/explainability don't exist
  until Sprints 4–6.

**Example Issues to open for this milestone:**
```
#XX feat: Flutter registration/login screen wired to auth API
#XX feat: child profile creation screen wired to backend
#XX feat: milestone recording screen wired to rule engine
```

**Definition of done:** From a real device/emulator, you can register, log in,
create a child profile, and record a milestone observation that triggers the real
rule engine — confirm the resulting `DevelopmentalProfile` exists in the database
(via admin or a quick query), not just that the API returned 200 OK. Full round
trip, zero manual backend poking. This is also your first genuinely demoable
feature for a progress check, well before the recommendation engine exists.

**Note:** until this sprint is done, use DRF's browsable API or Django admin to
sanity-check Sprint 2/3 endpoints — you don't need Flutter running to confirm the
backend itself works.

---

### Sprint 4 — Semantic Retrieval (SBERT)

**GitHub Milestone:** "Sprint 4: Semantic Retrieval"

**Entry condition:** Rule engine produces valid profiles; activity repository has
50+ real activities.

**Build:**
- Batch precompute: encode every Published activity description with
  `all-MiniLM-L6-v2`, store embeddings (DR-09, DR-10, NFR-08).
- Real-time path: encode the caregiver's `DevelopmentalProfile` at request time.
- Cosine similarity retrieval of top-N candidates (FR-06, IR-06).

**Example Issues to open for this milestone:**
```
#18 feat: batch SBERT embedding pipeline for activities
#19 feat: real-time profile embedding + cosine similarity retrieval
#20 test: spot-check retrieval relevance against sample profiles
```

**Definition of done:** A profile emphasizing Language retrieves activities
actually about language development. Spot-checked 5–10 retrievals by hand.

---

### Sprint 5 — Weighted Ranking

**GitHub Milestone:** "Sprint 5: Weighted Ranking"

**Entry condition:** Both the rule engine and semantic retrieval independently
work.

**Build:**
- Weighted scoring function combining rule priority and semantic similarity via α
  (FR-07, IR-06).
- Age-appropriateness, caregiver preference, and contextual-factor weighting
  layered on top.
- α grid search script (0 to 1, step 0.1) against a held-out evaluation set.

**Example Issues to open for this milestone:**
```
#21 feat: implement weighted ranking function (FR-07)
#22 feat: alpha grid search evaluation script
```

**Definition of done:** The system returns a single ranked list combining both
signals, and you have at least a preliminary best-alpha result.

---

### Sprint 6 — Explainability Module

**GitHub Milestone:** "Sprint 6: Explainability"

**Entry condition:** Ranked recommendations exist end-to-end.

**Build:**
- Per-recommendation explanation generation (FR-11, NFR-06, NFR-10) —
  caregiver-readable text, not raw scores.
- Store explanation with the Recommendation record.

**Example Issues to open for this milestone:**
```
#23 feat: generate caregiver-readable recommendation explanations (FR-11)
```

**Definition of done:** A non-technical person can read a generated explanation and
understand why that activity was suggested, unprompted.

---

### Sprint 7 — Caregiver Feedback & History Management

**GitHub Milestone:** "Sprint 7: Feedback & History"

**Entry condition:** Recommendations with explanations are being generated and
stored.

**Build:**
- `CompletedActivity` tracking (FR-14).
- `Feedback` submission tied to a specific recommendation (FR-15), routed through
  `FeedbackManager`.
- Administrator feedback review (FR-16).

**Example Issues to open for this milestone:**
```
#24 feat: mark recommendation as completed (FR-14)
#25 feat: submit feedback via FeedbackManager (FR-15)
#26 feat: administrator feedback review view (FR-16)
```

**Definition of done:** A caregiver can mark an activity complete and leave
feedback; an administrator can see that feedback against the activity it concerns.

---

### Sprint 8 — Mobile App Build-Out (Flutter)

**GitHub Milestone:** "Sprint 8: Mobile App"

**Entry condition:** Backend endpoints exist and are individually testable via
Postman/curl. Registration, login, and child profile creation already work from
Sprint 3.5 — this sprint builds everything after that.

**Build:**
- Remaining screens matching your wireframes: milestone tracking, recommendation
  display, activity detail, feedback. (Onboarding/login/profile creation are
  already done — Sprint 3.5.)
- REST integration for the remaining endpoints (IR-01–IR-04).
- Offline caching (NFR-14) — local cache of last-fetched data, graceful
  degradation offline. The SOFIA gap — build it into core navigation now, not
  later.
- Non-comparative progress view (NFR-15) — child's own history only, no
  rankings.
- Language toggle if keeping NFR-16, otherwise confirm Limitations notes
  English-only.

**Example Issues to open for this milestone:**
```
#27 feat: milestone tracking screen
#28 feat: recommendation display + explanation UI
#29 feat: offline caching for recommendations (NFR-14, SOFIA)
#30 feat: non-comparative progress/milestone view (NFR-15, SOFIA)
```

**Definition of done:** Full round trip on a real device/emulator: enter info →
see ranked recommendations with explanations → mark complete → leave feedback,
with no manual backend poking.

---

### Sprint 9 — Integration, Testing & Evaluation

**GitHub Milestone:** "Sprint 9: Evaluation"

**Entry condition:** The full app works end-to-end for the happy path.

**Build:**
- Expand automated tests across FR/NFR/DR/IR.
- Run the full Section 3.2.4 evaluation: relevance, personalization
  effectiveness, explainability, usability (SUS), caregiver satisfaction.
- Recruit your caregiver evaluation sample now if you haven't — longest lead
  time of anything left.
- Bug-fixing pass from real usage.

**Example Issues to open for this milestone:**
```
#31 test: expand functional/integration test coverage
#32 chore: run SUS + satisfaction questionnaire with caregiver sample
#33 fix: address issues found during evaluation
```

**Definition of done:** Actual numbers/results for all five evaluation
dimensions — this is what Chapter 5's evaluation section is built from.

---

### Sprint 10 — Documentation & Defence Prep

**GitHub Milestone:** "Sprint 10: Documentation"

**Entry condition:** System is feature-complete and evaluated.

**Build:**
- Write Chapter 5 — convert to past tense only for what's actually built; note
  deviations from Chapters 3/4 explicitly.
- Update diagrams if implementation diverged from design.
- Final full-document consistency pass.
- Prepare defence: justify your final α, walk through one real recommendation
  end-to-end, speak plainly about scoped-out SOFIA items.

**Example Issues to open for this milestone:**
```
#34 docs: write Chapter 5 implementation section
#35 docs: update diagrams to match final implementation
#36 docs: final consistency pass across full document
```

**Definition of done:** Someone else could clone this repo, run it, and
understand it from the documentation alone.

---

## Running Notes

**Activity curation:** keep adding activities across all 5 domains × all age
brackets throughout every sprint above — don't front-load or leave it to the end.
Track it as its own recurring Issue, reopened each sprint, rather than a one-time
task.

**Dev log:** three bullet points per working session (what you did, what broke,
what you fixed) — this is your own Section 3.3.7 commitment and what makes
Chapter 5 an accurate record instead of a reconstruction.

**If you're blocked** — e.g., waiting on Webmasters Kenya to clarify the
data-protection division of responsibility (IR-10) — don't stall. Switch to
activity curation or start groundwork on the next sprint instead of waiting idle.