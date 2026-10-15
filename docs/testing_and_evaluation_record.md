# Testing and evaluation record

> **Last updated: 2026-10-15.** Describes `main` at commit `8c547d1`, plus the end-to-end test fixes in #109. Every result below comes from a real run, log or pull request; nothing is estimated.

This record covers what has been tested so far, the results (expected and actual), the defects found and how they were corrected, and the initial evaluation evidence. What is still to evaluate is listed at the end.

---

## 1. The core workflow on a real phone

**Date:** 2026-10-15, 20:45–20:47.
**Set-up:**
- **Phone:** Samsung SM-A145F (Android) over USB, running the Flutter app.
- **Backend:** Django + PostgreSQL on a laptop, reached from the phone through `adb reverse`.
- **Email:** sign-in codes sent by real email through Gmail SMTP (`nurtura.sofia@gmail.com`).
- **How it ran:** the automated end-to-end test `integration_test/app_flow_test.dart` drove the app. The tester's only job was to type the emailed code.

**Result:** **passed** (`02:27 +2: All tests passed!`), the whole flow in 2 minutes 27 seconds.

The table follows the run step by step. *HTTP* is the backend's own log of the request, with its status code. *Screenshot* refers to `docs/evidence/e2e_2026-10-15/`.

| # | Step | Expected | Actual | Evidence |
|---|---|---|---|---|
| 1 | Register a new caregiver | Account created; no token yet; a 6-digit code emailed; the app asks for it | Account created; code emailed and received in Gmail; "Check your email" screen shown | `POST /api/auth/register/` **201** · screenshots 01–03 |
| 2 | Type the emailed code | Code accepted; signed in; phone trusted for 30 days | Code accepted; signed in; "Add your first child" shown | `POST /api/auth/login/verify/` **200** · 04 |
| 3 | Log out and log back in on the same phone | No code asked for, because the phone is trusted | Signed straight in, no code screen | `POST /api/auth/logout/` **204**, `POST /api/auth/login/` **200** |
| 4 | Create an expecting (pregnancy) profile | Profile saved; Milestones explains there's nothing to record before birth | Saved; prenatal message shown | `POST /api/children/` **201** · 05, 06 |
| 5 | Create a 6-month-old child with the interest "music" | Profile saved; Milestones opens for that child | Saved; milestone checklist shown | `POST /api/children/` **201** · 07, 08 |
| 6 | Search "cooing" and record it as **Not yet** | One CDC milestone found; saved; profile updated | Found "Makes sounds like 'oooo' or 'aahh' (cooing)"; saved; "developmental profile was updated" | `GET …/reference-milestones/?search=cooing` **200**, `POST …/milestones/` **201** · 09, 10 |
| 7 | See ideas | Ranked activities (rule engine + SBERT + ranking) with a plain-language reason each, Language first | 5 activities stored and shown; top: *Turn-Taking Sound Games* (Language, 6–12 months) with its explanation | `POST …/recommendations/` **201** · 11 (generating), 12, 16 |
| 8 | Open the top activity | Full details and "Why this?" | Shown: "You recorded "Makes sounds like 'oooo' or 'aahh' (cooing)" as not yet; most children do this by 4 months. It's designed for children aged 6–12 months, your child's age group. Its aim is to help your baby learn to take turns, like in a conversation." | 12 |
| 9 | Mark it **Done** | Saved with today's date; "won't be suggested again" | "Done on 15 Oct 2026" | `PUT …/completion/` **201** · 13 |
| 10 | Rate 4 stars with a comment | Saved; thank-you view | "Thanks for your feedback!", 4 stars, comment shown | `PUT …/feedback/` **201** · 13 |
| 11 | Back to the list | The card shows Done and the rating | **Done** and **★ 4/5** chips on the card | 14, 16 |
| 12 | Progress tab | The child's own records only; no comparison with other children | "0 milestones celebrated · 1 recorded", 1-day streak, "Talking: 0 celebrated · 1 practising" | `GET …/milestones/` **200** · 15 |
| 13 | Switch the app to Dark | The whole app in dark mode | Today shown in dark mode | 16 |

**Notes on the evidence:**
- **Screenshots 01–03** come from the attempt just before (the same screens and flow). In the passing run they were skipped on purpose: on Android, screenshot capture freezes the phone's display, and the tester needed to see the code they were typing. See defect D9.
- **Screenshot 11** caught the "Preparing recommendations…" state just before the list appeared. The list itself is in 14 and 16.
- **Dark mode throughout:** the phone's own setting was dark mode, so every screenshot is dark. The switch from light to dark is covered by the app's widget tests (section 2).
- **The test account was deleted afterwards,** together with its children and records.

---

## 2. Automated tests

All of these run on every change (GitHub Actions) and **all passed** on `main` at `8c547d1` on 2026-10-15.

### Backend (Django): 378 tests

| Area | Tests | What they check |
|---|---|---|
| Activities | 36 | The activity model; the Draft → Under Review → Published workflow; only Published activities can be recommended (FR-13, DR-12); seeding and approved plain-language aims |
| Profiles | 117 | Caregiver/administrator roles (FR-01, FR-02); registration, login and two-step codes (expiry, 5 tries, resend limits, trusted phones, hashing); child profiles, including pregnancy; milestone recording; the rule engine's priority scores (FR-05) |
| Recommendations | 193 | Embeddings and similarity retrieval (FR-06); the weighted ranking and its tie-breaks (FR-07); explanations (FR-11); stored batches and when a new one is made; completed activities left out; evaluation harness and provenance checks; access (another caregiver's child → 404, administrators → 403) |
| Feedback | 32 | Mark done / partly done / undo (FR-14); `FeedbackManager` rating and comment rules (FR-15); administrator review, read-only, without the child or the caregiver shown (FR-16) |

### App (Flutter): 78 tests

| Area | Tests | What they check |
|---|---|---|
| Sign-in | 20 | Login and registration, error messages, saved sessions; the code screen (auto-submit, wrong code, resend countdown, "trust this phone", dark mode) |
| Children and milestones | 16 | Child profiles (including pregnancy), the milestone search and recording, "See ideas" |
| Recommendations and activity | 20 | Showing ranked ideas with explanations, generating, errors and retry; activity details; done, partly done, undo and feedback |
| Offline (NFR-14) | 11 | Saved recommendations shown offline with a notice; opening the app offline stays signed in; logout and a 401 clear what's saved |
| Home, progress and theme | 10 | Tabs and child switcher; progress and badges from the child's own records, with banned comparison words checked (NFR-15); day streak; theme remembered |

The app's test runner reports 78; one test is generated for two status codes.

### End-to-end (real backend): 1 test

`integration_test/app_flow_test.dart`, as in section 1.

### Running them

```
cd backend && python manage.py test                 # 378 tests
cd mobile/nurtura_app && flutter test               # 78 tests
# End-to-end: see the header of integration_test/app_flow_test.dart
```

---

## 3. Defects found and corrections

| # | Found by | Expected | Actual (before the fix) | Correction | Ref. |
|---|---|---|---|---|---|
| D1 | Sprint 5 evaluation work | At α = 1 (rule priority only), the order uses no semantic signal | Ties were broken by similarity, so α = 1 still used SBERT | At α = 1, ties are broken by age fit, then activity ID; tests updated | #37 |
| D2 | Code review | Changing a child's interests gives fresh recommendations | Non-sensory interests (e.g. "books") change the search query but not the profile fingerprint, so the old batch came back | The fingerprint also covers the search query; two tests fail without the fix | #60 |
| D3 | Development of offline support | Opening the app offline shows the saved ideas | It showed the login screen; the saved ideas were out of reach | Stay signed in when there's no response; keep the child list on the phone; 4 tests | #102 |
| D4 | Privacy test (data minimisation) | The admin feedback review never shows the child or the caregiver | The feedback detail page title showed the child's name | Feedback and completion labels name the activity only | #99 |
| D5 | Startup (configuration) | Email settings load | Django 6.1 refused the old `EMAIL_*` settings next to `MAILERS` | Email configured through `MAILERS` only | #87 |
| D6 | Phone run 1 | The test starts at the login screen | It reused the phone's saved sign-in and skipped login | The test keeps its token in memory | #109 |
| D7 | Phone run 2 | Screenshots saved | Android needs a surface conversion first, and the capture waited for frames that never came | Convert once, and draw frames during each capture | #109 |
| D8 | Phone runs 3–4 | Taps land on the button named | The keyboard and the "Well done!" message covered targets; two taps missed silently | Close the keyboard before taps; wait for the message; a missed tap now fails at once | #109 |
| D9 | The tester, run 5 | The tester sees the code as they type | The phone's display was frozen by screenshot capture | On Android, screenshots start after the code step | #109 |

D6–D9 were faults in the test, not the app; the app behaved correctly in each case.

---

## 4. Initial evaluation evidence

### Ranking quality (Sprint 5)

The weight α between the rule engine and SBERT similarity was chosen on 11 *tune* children with a rule fixed before labelling, then checked on 8 separate *test* children. The researcher graded 205 child–activity pairs (0, 1 or 2) without seeing rankings or scores. Full details are in [`sprint5_alpha_results.md`](sprint5_alpha_results.md).

**Test set (8 children):**

| Ranking | Top-5 relevant (≥ 1) | Top-5 clearly relevant (= 2) | nDCG@5 |
|---|---|---|---|
| SBERT similarity only (baseline) | 0.700 | 0.300 | 0.452 |
| **Nurtura ranking, α = 0.7** | **0.925** | **0.675** | **0.814** |

7 of the 8 test children got better recommendations than with similarity alone.

**Limitations:** small numbers, one rater who also designed the system, and constructed (not real) children. The test set preferred the α = 0 ablation (nDCG@5 0.873), so 0.7 is a reasonable default rather than an optimum. Caregiver feedback in Sprint 9 is the better test.

### Retrieval (Sprint 4)

An automatic check of SBERT similarity alone: **24 of 35 (69%)** top-5 activities for 7 sample children were in the developmental area the child needed ([`sprint4_retrieval_spot_check.md`](sprint4_retrieval_spot_check.md)). The researcher's hand check of actual relevance (#31) is still to do.

### Explanations (Sprint 6)

Explanations are generated for every recommendation; section 1, step 8, shows a real one. The **reader test** (5 non-technical readers, 10 explanations, passing at 8 of 10 understood) is prepared in [`explanation_reader_test.md`](explanation_reader_test.md) but **has not been run yet**.

---

## 5. Still to test and evaluate

- **Explanation reader test** with 5 readers (Sprint 6 definition of done).
- **Hand check of retrieval results** (#31).
- **Evaluation with caregivers (Sprint 9):** relevance and personalisation from their own children's recommendations, explainability, usability (SUS) and satisfaction. Participants still need to be recruited.
- **Requirement-by-requirement test mapping:** the table in section 2 names the requirements the repo references; the full list from Chapter 3 is needed to map every requirement to its tests and fill any gaps.
- **Light mode on a phone:** covered by widget tests; not yet captured on the device.
- **Remaining 108 CDC milestones** to verify against the official checklists.
