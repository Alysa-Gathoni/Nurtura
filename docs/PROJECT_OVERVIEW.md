# Nurtura: Project Overview

*An AI-based early childhood development activity recommender, and a component of the SOFIA platform (client: Webmasters Kenya).*

> **Last updated: 2026-10-10.** The figures describe `main` at commit `9d5c2ed` (tag `sprint5-eval-v1`), after Sprint 5. They will go out of date as work continues; check the date before quoting them.

---

## 1. What Nurtura is

Nurtura helps parents and caregivers of children from **pregnancy up to 3 years** answer one everyday question:

> *"What can I do with my child today that actually helps their development?"*

Caregivers tell the app about their child: age, interests, any worries, and which developmental milestones the child has reached. Nurtura then recommends **simple, evidence-based activities** to do at home, and explains **why** each one was suggested.

Nurtura is one part of **SOFIA**, a larger platform being built for Webmasters Kenya. It is the part that turns information about a child into personalised activity suggestions.

Two principles guide the design:

- **Evidence-based.** Milestones come from published guidelines (CDC, WHO). Every activity is traceable to WHO, CDC, UNICEF, Montessori or Pathways.org guidance. Nothing is invented.
- **Safe content.** No activity reaches a caregiver until an administrator has reviewed and published it.

---

## 2. What it does: the pipeline

```
 Caregiver input        Rule engine            Semantic search        Ranking                Explanation
 (child, milestones,    (CDC/WHO/ASQ rules)    (SBERT AI model)       (weighted              ("Suggested
  concerns, interests)  Which areas need       Which activities       combination, α = 0.7)  because…")
                        attention most?        match those needs?
      BUILT                  BUILT                  BUILT              BUILT + EVALUATED       NEXT (Sprint 6)
```

| Stage | What it does | Status |
|---|---|---|
| 1. Caregiver input | The caregiver creates a child profile (including a pregnancy profile) in the mobile app, and records milestones from a searchable checklist, e.g. *"Waves bye-bye: Not yet"*. | **Built.** Runs on an Android phone. |
| 2. Rule engine | Compares the child's milestones with what CDC and WHO expect at that age, and gives each of the **five developmental areas** (Cognitive, Language, Motor, Sensory, Socio-Emotional) a priority score from 0 to 1. | **Built.** |
| 3. Semantic search | An AI language model (Sentence-BERT, `all-MiniLM-L6-v2`) compares the meaning of the child's needs with every published activity. It works on meaning, not keywords. | **Built.** Sprint 4's hand check of sample results (#31) is still open. |
| 4. Weighted ranking | Combines rule priority and semantic match, weighted by how well the activity's age range suits the child. The balance (α) was chosen experimentally. | **Built and evaluated** (Sprint 5, α = 0.7). |
| 5. Explanation | A plain-language reason for each recommendation. | **Next** (Sprint 6). First, ranked recommendations are being connected end to end (#52). |

---

## 3. A worked example

The child here is **hypothetical**, but the numbers come from running the real system (rule engine and ranking at α = 0.7) on the current catalogue, on 2026-10-10.

**The child:** Amani, **6 months old**. Her caregiver adds one interest: *music*.

**Step 1: The caregiver records a milestone.** In the app, the caregiver searches the checklist for *"cooing"* and finds:

> *Makes sounds like "oooo" or "aahh" (cooing)*: Language, expected **by 4 months** (CDC)

They mark it as **Not yet**.

**Step 2: The rule engine builds Amani's developmental profile.** Two rules fire:

| Rule | Why it fired | Effect |
|---|---|---|
| Due milestone not yet reached | Amani is 6 months; CDC expects this by 4 months | Language **+10** |
| Sensory interest | "Music" is a sensory interest | Sensory **+2** |

Every area starts at 1. After the rules, the scores are scaled so the most urgent area is 1.0:

| Area | Priority score |
|---|---|
| **Language** | **1.00** (highest priority) |
| Sensory | 0.27 |
| Cognitive, Motor, Socio-Emotional | 0.09 each |

**Steps 3 and 4: Search and ranking.** The profile becomes a plain-language query, and the system ranks all 46 published activities for babies and toddlers (the 8 pregnancy activities are excluded once a baby is born). Amani's top five:

1. *Turn-Taking Sound Games* (Language, 6–12 months)
2. *Waiting for Baby's Response* (Language, 6–12 months)
3. *Animal Sound Imitation Game* (Language, 3–6 months)
4. *Naming Everyday Objects* (Language, 12–18 months)
5. *Naming Pictures in a Book* (Language, 12–18 months)

**Step 5: Explanation.** *(Sprint 6; illustrative.)* The caregiver would see something like:

> **Turn-Taking Sound Games**
> *Suggested because Amani hasn't started cooing yet, which most babies do by 4 months. Copying her sounds and pausing for her to reply builds the back-and-forth of early conversation.*

**Before birth:** an expecting parent can create a profile from the **due date** and choose an area they'd like support with. They then see only pregnancy activities, ranked for that area.

---

## 4. Does the ranking work? Sprint 5 results

The balance between the rule engine and the AI search (α) was chosen by experiment, not by guesswork:

- **The children:** **20 sample children** were built from real CDC milestones, separate from the children used during development. They were split in advance into 11 for **tuning**, 8 for **testing**, and 1 reported separately because the catalogue has no matching content for that child.
- **The labels:** the researcher graded **205 child–activity pairs** (0 = not relevant, 1 = somewhat, 2 = clearly relevant) without seeing any rankings or scores.
- **Choosing α:** α was chosen on the tuning children only, using a rule written down before labelling: the middle of the range of values within 0.02 of the best score. That gave **α = 0.7**.

**On the 8 test children:**

| | AI search only (baseline) | Nurtura ranking (α = 0.7) |
|---|---|---|
| Top-5 activities graded relevant (≥ 1) | 70% | 92.5% |
| Top-5 activities graded clearly relevant (2) | 30% | 67.5% |
| Ranking quality (nDCG@5, 0 to 1) | 0.45 | 0.81 |

- **7 of the 8 test children got better recommendations** than with AI search alone. One expecting parent got slightly worse.
- **Most of the gain comes from age weighting**, which favours activities meant for the child's age. Adding it alone raised the tuning score from 0.49 to 0.74. On the test children, the age-weighted search without rule priority (α = 0) scored even higher than the chosen setting (0.87 against 0.81).
- **Caveats:** this is a small study, with 8 test children and one person grading, so no statistical-significance claims are made. Full details are in `docs/sprint5_alpha_results.md`.
- **Scope change:** caregiver-preference and contextual weighting, planned in the proposal (Section 3.2.3), were dropped from scope. Only α was tuned.

---

## 5. What has been done so far

The project follows a sprint plan, with a GitHub issue, branch, pull request and automated tests for every change.

| Sprint | Goal | Status |
|---|---|---|
| 1. Setup | Django + PostgreSQL backend, Flutter app, SBERT model, CI | ✅ Complete |
| 2. Core data layer | Data models, login with roles, content review workflow, activity data | ✅ Complete |
| 3. Rule engine | Developmental profiling from CDC/WHO/ASQ guidelines | ✅ Complete |
| 3.5 Mobile shell | First app screens connected to the real backend, run on an Android phone | ✅ Complete |
| 4. Semantic search | SBERT embeddings and similarity search | ✅ Built; hand check of results pending (#31) |
| 5. Weighted ranking | Combine the signals, choose α on a held-out set | ✅ Complete (tag `sprint5-eval-v1`) |
| 6. Explainability | Plain-language reasons for each recommendation | 🔄 Next: connecting ranked recommendations end to end (#52) |
| 7–8 | Feedback, history, full mobile app | Planned |
| 9–10 | Evaluation with caregivers, documentation | Planned |

### By the numbers

| | |
|---|---|
| Activities | **54**, all reviewed and Published: Socio-Emotional 17, Language 12, Cognitive 10, Motor 8, Sensory 7; 8 of them for pregnancy |
| Reference milestones | **133**: 127 CDC (2022 checklists) and 6 WHO (motor study). **25 verified** against the source: the 6 WHO ones and the 19 CDC ones used in the evaluation. The other 108 are still to check. |
| Automated tests | **249** backend tests and **26** app tests, run on every change (GitHub Actions) |
| Engineering history | **26** merged pull requests, **71** commits on `main` |

### Highlights

**Backend (Django + PostgreSQL)**
- All six core classes from the design are implemented: Child Profile, Developmental Activity, Developmental Milestone, Recommendation, Completed Activity and Feedback.
- **Two user roles.** Caregivers use the app and see only their own children. Administrators manage the activity library.
- **Content review workflow (the SOFIA fix):** each activity moves Draft → Under Review → Published, and only Published activities can be recommended.
- **Security basics:** strong-password rules, one account per email, and limited login attempts.

**Rule engine**
- A custom IF-THEN engine. Weights follow the ASQ-3 scoring convention: Not yet = +10, Emerging = +5.
- Sensory has its own path, through caregiver concerns and interests, because the CDC/WHO checklists have no Sensory category.

**AI search and ranking**
- Every published activity is converted into a vector (embedding) once. The child's profile is matched against all of them at request time.
- The ranking multiplies by an **age-fit weight**, which is asymmetric: an activity one age bracket younger keeps 70% of its score, one bracket older keeps 50%, because a child who is behind usually needs the earlier skills.
- **Reproducible evaluation:** the labelling sheet records exactly which activities, rules and model it was built from, and the evaluation warns if anything has changed since.

**Mobile app (Flutter)**
- Four screens: register/log in, a list of children, create a child profile (including pregnancy), and record milestones from a searchable checklist.
- Built to the agreed visual design: teal, coral and gold colours, rounded cards, Nunito and Quicksand fonts.
- Runs on a real Android phone against the local backend.

---

## 6. What's next and open items

- **Sprint 6, explanations:** first, connect the ranking end to end, so recommendations are generated, saved and served to the app (#52). Then write the plain-language explanations.
- **Sprint 4 hand check (#31):** review the saved search results for the sample children.
- **Verify the remaining 108 CDC milestones** against the official checklists.
- **Recruit caregivers for the Sprint 9 evaluation.** It has the longest lead time.
