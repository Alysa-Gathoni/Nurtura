# Simulated-participant pre-test: usability, satisfaction and the reader test

> **Last updated: 2026-11-16** (#222).
>
> **SIMULATED. These are not real participants.** Every response below was written for a fictional persona by a large language model, following the session sheet. It is a pre-test of the materials and the app, not evidence of what caregivers think. It doesn't replace the caregiver sessions in [caregiver_evaluation.md](caregiver_evaluation.md) or the reader test in [explanation_reader_test.md](explanation_reader_test.md), and it doesn't by itself meet NFR-06.

## Why a simulated pre-test

No real sessions have been run yet. A simulated run answers three practical questions before real people are asked:

1. **Do the materials work end to end?** Session sheet, form exports, both scorers.
2. **Which usability problems are likely?** So that obvious ones aren't left for participants to find.
3. **Which explanation sentences might confuse or worry readers?**

Simulated personas are a recognised way to pre-test a study design. Their answers reflect the simulator's assumptions about people, not people.

## What is real and what is simulated

| Part | Real or simulated |
|---|---|
| The app's screens and wording (current `main`) | **Real**: read from the screen code and the 15 Oct 2026 phone screenshots |
| Each persona's top 5 activities and their "Why this?" text | **Real**: the system's own output, from `generate()` in a rolled-back transaction ([persona_recommendations.py](../scripts/simulated_evaluation/persona_recommendations.py)) |
| The 10 reader-test cards and the answer key | **Real**: unchanged from [explanation_reader_test.md](explanation_reader_test.md) |
| The scorers | **Real**: `score_caregiver_questionnaire.py` and `score_reader_test.py`, run unchanged on CSVs in the Google Forms export format |
| The personas (8 caregivers, 10 readers) | **Simulated**: fictional Kenyan caregivers and readers ([personas_SIMULATED.json](simulated_evaluation/personas_SIMULATED.json)) |
| Task outcomes, times and problems; relevance ratings; "why" answers; SUS, satisfaction and open answers; reader answers and concerns | **Simulated**: written by a large language model in the role of each persona ([sessions_SIMULATED.json](simulated_evaluation/sessions_SIMULATED.json)) |

**For the report (Chapter 5):** if you mention this run, say that the participants were simulated with a large language model, that it was a pre-test of the protocol, and that its figures are not user results. Don't put simulated SUS or satisfaction figures next to real ones without that label.

## Personas

| ID | Persona (fictional) | Child | Task B2 |
|---|---|---|---|
| P01 | Wanjiru, 24, first-time mother, Nairobi; daily smartphone user, no parenting app before | 5 months; interest: songs | "Pushes up onto elbows… on tummy": Not yet |
| P02 | Otieno, 31, teacher, Kisumu; very confident with phones | 14 months; Motor; balls | "Walks, holding on to furniture": Achieved |
| P03 | Mama Njeri, 58, grandmother, Murang'a; Kikuyu first, reads English slowly; scenario card | Zawadi, 10 months; Language; music, peekaboo | "Makes a lot of different sounds…": Not yet |
| P04 | Achieng, 27, bank clerk, Nairobi; expecting in 3 months | Prenatal; Socio-Emotional | N/A: expecting |
| P05 | Fatuma, 35, mother of three, Mombasa; Swahili first | 22 months; Language; animals | "Tries to say three or more words…": Not yet |
| P06 | Kevin, 29, software tester, Nairobi | 8 months; water | "Rolls from tummy to back": Achieved |
| P07 | Mercy, 20, young mother, Nakuru; small data bundles | 3 months | "Smiles when you talk to… them": Achieved |
| P08 | Joyce, 40, day-care worker, Thika | 30 months (in her care); Cognitive; drawing | "Shows they know at least one colour…": Not yet |

Readers R01–R10: nine look after a child under 5, one is a student with no children; R01–R05 on form A, R06–R10 on form B (reversed order). None had seen the project.

## Results (simulated)

### Tasks B1–B5

| Task | Unaided | With help | Not done | Median minutes |
|---|---|---|---|---|
| B1 Add a child | 6 | 2 | 0 | 2.0 |
| B2 Record a milestone | 6 | 1 | 1 (expecting, N/A) | 2.5 |
| B3 Find the suggestions | 8 | 0 | 0 | 0.5 |
| B4 Find out why | 8 | 0 | 0 | 0.5 |
| B5 Give feedback | 7 | 1 | 0 | 1.5 |

Help was needed by the oldest persona (P03: date picker, a button below the fold, Done! or Partly) and the day-care worker (P08: whether a child in her care counts).

### SUS and satisfaction

From `score_caregiver_questionnaire.py` ([questionnaire_scores_SIMULATED.txt](simulated_evaluation/questionnaire_scores_SIMULATED.txt)):

| | P01 | P02 | P03 | P04 | P05 | P06 | P07 | P08 | Mean |
|---|---|---|---|---|---|---|---|---|---|
| SUS (0–100) | 82.5 | 92.5 | 50 | 87.5 | 75 | 75 | 97.5 | 75 | **79.4** |

| Item | Median | Counts 3 / 4 / 5 |
|---|---|---|
| S1 Trust the activities | 4 | 2 / 6 / 0 |
| S2 Useful for my child | 4 | 2 / 4 / 2 |
| S3 "Why this?" helped | 4 | 1 / 5 / 2 |
| S4 Can do with things I have | 5 | 0 / 2 / 6 |
| S5 Would keep using | 4 | 2 / 5 / 1 |
| S6 Would recommend | 4 | 1 / 4 / 3 |

No item had a 1 or 2. A simulated SUS mean says little: it mostly reflects how the personas were written. The useful part is the spread (P03 at 50) and the reasons behind it.

### Relevance of the real top 5 (C1)

40 ratings of the system's real suggestions: **23 clearly useful (2), 17 somewhat useful (1), 0 not useful**. Mean by position: 1.63, 1.63, 1.63, 1.38, 1.63.

### "Why was this suggested?" (C2)

**7 of 8** gave the main reason of the explanation shown. P08 gave the activity's aim ("To help him think and solve problems"), not the colour milestone.

### Reader test

From `score_reader_test.py` ([reader_test_scores_SIMULATED.txt](simulated_evaluation/reader_test_scores_SIMULATED.txt)), 10 valid respondents:

| Card | Auto mark (keyword) | Reviewed against the key | Passes (≥ 80%)? |
|---|---|---|---|
| 1 Prenatal | 10 | 8 | yes |
| 2 Head up | 10 | 9 | yes |
| 3 Smiling | 9 | 9 | yes |
| 4 Interest | 10 | 10 | yes |
| 5 No requests | 9 | 9 | yes |
| 6 Steps | 10 | 9 | yes |
| 7 Toys | 10 | 10 | yes |
| 8 Interest, younger | 10 | 10 | yes |
| 9 Two groups | 10 | 9 | yes |
| 10 WHO | 9 | 9 | yes |

**10 of 10 cards pass** on both marks (the test needs 8). The reviewed marks are lower because the keyword check accepted answers that give only the activity's aim (for example "To build neck strength for rolling and crawling" for card 2).

Concerns raised (Q2/Q3): 8, from 5 readers:
- **"Most children do this by…" / "almost all children…"** worried three readers (cards 2, 3, 10).
- **"Sensory"** wasn't understood by the Swahili-first reader (cards 4, 8).
- **"Often comes next"** (card 9) and **"may find it easy"** (card 8) each confused one reader.

## Findings to act on

Each finding is marked by what it rests on. **Verified** findings come from the real system or code and hold whatever the simulation says. **Simulated** findings are plausible problems to confirm with real participants.

| # | Finding | Rests on | Suggested action |
|---|---|---|---|
| 1 | **Every "Why this?" in a batch starts with the same one or two sentences**; only the aim differs. | Verified (all 8 personas' real output) | Consider showing the shared reason once above the list, and only the aim per card. |
| 2 | **An interest can be stretched to an area**: "your child enjoys water, which points us towards activities for the senses" for activities that don't use water (P06: 4 of 5). | Verified (real output) | Mention the interest only on activities that use it (the explanation already adds "this activity uses water" when it does). |
| 3 | **The clinic-visit message appears after a single "Not yet"** (P01, P03, P05, P08: half the personas). This is deliberate: the threshold follows CDC's "one or more milestones" (`backend/profiles/rules/referral.py:21`). | Verified (real output and code) | Keep, but watch caregivers' reactions in the sessions: it is the message most likely to worry. |
| 4 | **Interests that match no activity are silently ignored** (P08 "drawing"); P02's "balls" was used once. | Verified (real output) | Acceptable; could be stated in the explanation or the Family tab. |
| 5 | **The most on-target activity can rank last**: for P01 (tummy push-ups), "Front Reach on the Tummy" was 5th. | Verified ordering; the judgement is simulated | Note as a known effect of α = 0.7 within one area; no change before the sessions. |
| 6 | **Area names are jargon** on the child form ("Cognitive", "Socio-Emotional", "Sensory") and in explanations ("sensory development"). | Verified wording; the effect is simulated (P03, P08, R04) | Add a short plain description under each area chip, e.g. "Cognitive: thinking and problem-solving". |
| 7 | **"Most children do this by…" may worry anxious readers.** | Simulated (3 readers) | Don't reword yet: the protocol says real readers' concerns decide. Watch for it in the real test. |
| 8 | **First load takes up to 30 seconds** and people wonder if it's stuck. | Verified (start-up 21 s in the evidence pack) | Warm the model at server start (already possible with `NURTURA_MODEL_WARMUP=1`); use it for the sessions. |
| 9 | **English only**: two personas asked for Kiswahili. | Verified (no localisation in the app) | Known limitation; state it in Chapter 6. |
| 10 | **Date picker for older children and a Save button below the fold** slowed the oldest persona. | Simulated | Check on the phone with large text before the sessions. |
| 11 | **The reader-test scorer's keyword check over-credits aim-only answers.** | Verified (real scorer on these answers) | Keep reviewing every answer by hand, as the scorer already instructs. |

## Limitations

- **Not people.** One language model wrote every response. The personas share its assumptions, so agreement between them means little, and the numbers have no sampling meaning.
- **No real interaction.** The walkthrough was reasoned from the screens' text and screenshots, not done on a phone. Timings are estimates.
- **Optimism risk.** Simulated users tend to be more successful and more positive than real ones. Treat the SUS mean and the pass rates as upper bounds, not predictions.
- **Not a replacement** for the caregiver sessions or the reader test, which still need real participants, ethics clearance and the agreed sample size.

## What it showed about the materials

The protocol works end to end:
- the session sheet's tasks map onto the app;
- simulated form exports in the real format were read by both scorers without errors;
- the summary steps produce every figure the plan asks for.

## Reproducing

From the repository root:

```
backend\venv\Scripts\python.exe scripts\simulated_evaluation\persona_recommendations.py
backend\venv\Scripts\python.exe scripts\simulated_evaluation\build_and_score.py
```

The first regenerates each persona's real top 5 (it changes if activities, rules or α change). The second rebuilds the CSVs from `sessions_SIMULATED.json`, runs both scorers and writes `summary_SIMULATED.json`. Every file in [simulated_evaluation/](simulated_evaluation/) has SIMULATED in its name.
