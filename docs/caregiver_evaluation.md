# Caregiver evaluation (Sprint 9)

This is the plan for evaluating Nurtura with real caregivers, as described in Section 3.2.4 of the proposal. It covers four of the five evaluation dimensions in Objective (v):

| Dimension | How it's measured here | Requirement |
|---|---|---|
| Usability | The System Usability Scale (SUS), after a short task-based walkthrough | NFR-06 |
| Caregiver satisfaction | A post-use questionnaire: trust, usefulness, likelihood of continued use | NFR-13 |
| Relevance | The caregiver rates each of the 5 suggestions for their own child | NFR-12 |
| Explainability | The caregiver says, in their own words, why the top suggestion was made | NFR-10, NFR-12 |

The fifth dimension, **personalisation effectiveness** (diversity, novelty and coverage), is measured offline from the system's outputs. It isn't part of these sessions.

**The materials:**
- [`caregiver_evaluation_consent.md`](caregiver_evaluation_consent.md): information sheet and consent form, given to the participant first.
- [`caregiver_evaluation_questionnaire.md`](caregiver_evaluation_questionnaire.md): the participant's questionnaire (SUS, then satisfaction).
- [`caregiver_evaluation_session_sheet.md`](caregiver_evaluation_session_sheet.md): the researcher's sheet for one session (tasks, relevance ratings, the explanation question).

> **Status: draft.** Confirm the two open decisions at the end with the supervisor before the first session.

---

## Who takes part

- **Adults (18 or over)** who look after a child aged **0 to 36 months**, or who are **expecting** a baby. Parents, relatives, nannies and other regular carers all count.
- **Not** people who worked on Nurtura or have seen it demonstrated.
- **A convenience sample** (Section 3.2.4): people the researcher can reach, for example through classmates, family, church or a clinic waiting room where permission has been given. The target number is an open decision (below).
- Participants are recorded only as **P01, P02, …**. No names appear on any sheet except the consent form.

## Set-up

- **One phone, run by the researcher:** an Android phone with the Nurtura app. Until the backend is hosted, the phone is connected to the laptop over USB (`adb reverse`), so sessions are **in person only**.
- **A fixed version:** every session uses the same build. Before the first session, tag the commit (for example `sprint9-caregiver-eval-v1`) and write the tag on each session sheet. Don't change the app, the activities, the ranking or the explanations between sessions.
- **A session account per participant,** made by the researcher beforehand, so the participant's own email is never collected:
  1. Register `nurtura.sofia+p01@gmail.com` (and so on; Gmail delivers `+` addresses to the same inbox) on the session phone.
  2. Type the emailed code and keep **"trust this phone"** on, so the participant isn't asked for a code.
  3. Leave the account signed in, with **no children** on it.
- **The child:** the participant uses their own child, under a **nickname**. For the date of birth, the 1st of the child's birth month is close enough. A participant who would rather not use their own child, or who is expecting, can also use their own due date. If they prefer, they use the scenario card on the session sheet instead, and the sheet records that.

## Procedure (about 30 minutes)

1. **Welcome and consent (5 min).** Give the information sheet. Answer questions. The participant signs the consent form, or gives verbal consent, which the researcher records on the form. Consent forms are kept apart from all other sheets.
2. **Background (1 min).** The three questions at the top of the session sheet.
3. **Tasks (10–15 min).** Read each task aloud from the session sheet, exactly as written. Then watch and record:
   - **Outcome:** *completed unaided*, *completed with help*, or *not completed*.
   - **Help rule:** don't help unless the participant asks or has been stuck for about a minute. Then give the smallest hint that gets them moving, and record it as *with help*.
   - **Problems:** note anything that confused or slowed them, in their own words where possible.
   - Don't explain how Nurtura works, before or during the tasks.
4. **Relevance and explanation (5 min).** On the list of 5 suggestions, ask the two questions in Part C of the session sheet.
5. **Questionnaire (5 min).** Hand over the questionnaire. The participant fills it in alone. The researcher doesn't read it or comment on the answers.
6. **Close.** Thank the participant. Afterwards, **delete the session account** in the Django admin. This deletes its child, milestones, recommendations, completions and ratings.

## Measures and scoring

### Usability: SUS (NFR-06)

The standard 10-item System Usability Scale (Brooke, 1996), with "system" replaced by "app", and "cumbersome" replaced by "awkward" in item 8. Both are common, accepted changes; "awkward" is easier for non-native English speakers (Finstad, 2006).

- Responses run 1 (strongly disagree) to 5 (strongly agree).
- **Score per participant:** for odd items (1, 3, 5, 7, 9), take the response minus 1. For even items (2, 4, 6, 8, 10), take 5 minus the response. Add the ten numbers and multiply by 2.5. This gives a score from 0 to 100.
- **Report:** each participant's score, the mean and the range. A SUS score is **not a percentage**. Around 68 is commonly treated as average.
- **A missing item:** ask the participant to answer it before they leave. If it's still blank, report that participant's score as incomplete and leave it out of the mean.

### Satisfaction (NFR-13)

Six statements, 1 (strongly disagree) to 5 (strongly agree), plus two open questions. They cover the three areas in Section 3.2.4 (trust, perceived usefulness of the activities and explanations, likelihood of continued use) and one about whether the activities are practical at home.

- **Report each item on its own:** the median and how many chose each answer. Don't add the items into one score; they measure different things.
- **Open answers:** group them into themes, and quote short examples.

### Relevance (NFR-12)

For each of the 5 suggestions, the caregiver chooses one of three options. They use the same 0–2 scale as the Sprint 5 relevance labels:

| | |
|---|---|
| **2** | Clearly useful for my child right now |
| **1** | Somewhat useful |
| **0** | Not useful for my child right now |

- **Report:** the share of suggestions rated at least 1, and the share rated 2, over all participants.
- These can be set **beside** the Sprint 5 test figures (92.5% rated at least 1, 67.5% rated 2), but they aren't the same measurement. Sprint 5 used one grader and constructed children; this uses real caregivers judging their own children. Say this when comparing.
- Scenario-card participants are reported separately.

### Explainability (NFR-10, NFR-12)

For the top suggestion only, the caregiver opens it, reads "Why this?", and then answers in their own words: **"Why do you think the app suggested this activity?"**

- The researcher writes the answer **word for word**.
- **Scoring** follows the explanation reader test ([`explanation_reader_test.md`](explanation_reader_test.md)). The answer is *understood* if it gives the explanation's **main reason** in any words (for example, the milestone recorded as not yet, or the area the caregiver asked for support with). An answer that gives only a secondary point, such as age alone when the main reason is a milestone, is *not understood*.
- Score **blind**, after all sessions, with the sheets shuffled and the participant numbers covered.
- **Report:** how many participants understood, out of how many answered. Satisfaction item S3 adds the caregiver's own view of the explanations.

## Analysis and reporting

- **Small numbers:** report counts, the mean or median and the range. Don't use significance tests, and don't claim results for caregivers in general.
- **Usability problems:** list each problem seen in the tasks, how many participants met it, and whether it stopped them. These feed the Sprint 9 bug-fixing pass. Fixes are made **after** all sessions, so every participant sees the same app.
- Results go into [`testing_and_evaluation_record.md`](testing_and_evaluation_record.md) (section 4) and Chapter 5.

## Data handling

This follows "Access, privacy and ethics" in [`data/README.md`](../data/README.md).

- **Consent forms** are the only sheets with names. They are kept apart from the session sheets and questionnaires, which carry only the participant number.
- **Paper sheets** stay with the researcher. They're typed into a spreadsheet keyed by participant number, kept **outside the repository**.
- **Only aggregated results** (scores, counts, short anonymous quotes) are committed or put in the report.
- **App data** is deleted at the end of each session, with the session account.
- **Retention:** paper sheets and the spreadsheet are kept until the project has been assessed, then destroyed. Confirm this period with the supervisor.

## Open decisions (confirm with the supervisor before the first session)

1. **Ethics approval.** Whether the university's ethics review process applies to this evaluation, and if so, what has to be submitted. This may take time, so ask first.
2. **Sample size.** Section 3.2.4 says "a small convenience sample". A suggested target is **8 participants, with at least 5**. Agree the number, and what happens if fewer can be recruited.

## References

- Brooke, J. (1996). SUS: A "quick and dirty" usability scale. In P. W. Jordan, B. Thomas, B. A. Weerdmeester & I. L. McClelland (Eds.), *Usability Evaluation in Industry* (pp. 189–194). Taylor & Francis.
- Finstad, K. (2006). The System Usability Scale and non-native English speakers. *Journal of Usability Studies*, 1(4), 185–188.
