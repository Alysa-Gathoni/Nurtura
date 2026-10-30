# Known limitations and outstanding defects

> **Last updated: 2026-10-30.** Each item is something the project knows about and says plainly. Where it's planned, the sprint is named; where it isn't, it's a limitation of this version.

## Outstanding defects

None known. Every defect found so far has been fixed and is recorded with its correction in [testing_and_evaluation_record.md](testing_and_evaluation_record.md) (section 3).

## Evaluation not yet done

| Item | State | Planned |
|---|---|---|
| Explanation reader test (5 non-technical readers) | Materials ready ([explanation_reader_test.md](explanation_reader_test.md)); not run. Until it's scored, explanation wording and the evaluated ranking stay frozen | Before Sprint 9 |
| Hand check of retrieval results (#31) | Results generated; the researcher's relevant / not relevant judgements are still to do | Before Sprint 9 |
| Evaluation with caregivers: relevance, personalisation, explainability, usability (SUS), satisfaction | Materials drafted ([caregiver_evaluation.md](caregiver_evaluation.md)); ethics question and sample size to confirm with the supervisor; participants still to recruit | Sprint 9 |
| Requirement-by-requirement test map | Tests reference the requirement IDs found in the repository; the full list from Chapter 3 is needed to map all of them | Sprint 9 |

## Evaluation limits

- **Small and constructed.** α was chosen on 11 tune children and checked on 8 test children. They are realistic but hypothetical profiles, labelled by one rater who also designed the system, with no agreement measure. The results describe these children only and support no statistical claims ([sprint5_alpha_results.md](sprint5_alpha_results.md)).
- **α is a reasonable default, not an optimum.** The test set preferred the α = 0 ablation (nDCG@5 0.873 against 0.814 for α = 0.7), and the tune curve is flat from 0.4 to 1.0.
- **Only the top 5 were labelled,** so the metrics can't be extended beyond k = 5.

## Content

- **54 Published activities, 400 more awaiting review** (batch 5, #156, and batch 6, #158). The 54 Published ones are uneven: Socio-Emotional 17, Language 12, Cognitive 10, Motor 8, Sensory 7, and 8 of them for pregnancy; some age and area combinations have nothing (no Sensory activity for 18–24 months made one held-out child, H17, a content-gap case). The 400 new activities bring every combination to at least 10, including pregnancy Cognitive and Motor, but they are Draft: none is recommended until an administrator checks it against its source and publishes it. Publishing them changes the evaluation's activity fingerprint, as planned (the 25 Oct unfreeze decision).
- **Sensory has no guideline milestones.** The CDC and WHO checklists have no Sensory category, so Sensory priority comes only from caregiver concerns and interests.
- **108 of 133 catalogue milestones are not yet verified** against the source documents (the 6 WHO ones and 19 CDC ones used in the evaluation are).
- **English only.** A language toggle (NFR-16) is undecided; if it isn't built, English-only is a stated limitation.

## App and backend

- **Not hosted yet.** The backend runs on a laptop. The phone reaches it over USB (`adb reverse`), because campus Wi-Fi blocks devices from reaching each other. Hosting is Sprint III ([deployment_requirements.md](deployment_requirements.md)).
- **The server address is built into the app** at build time (`--dart-define=API_BASE_URL`). A new address means rebuilding the app.
- **Android debug builds only.** No signed release build yet; iOS hasn't been run (the app has been tested on an Android phone and in Chrome).
- **Offline use is partial.** The last recommendations and the child list are kept on the phone and shown offline. Recording milestones, Progress, and marking done or rating need a connection, and actions taken offline aren't queued.
- **Deleting an account is immediate and final** (#134). A caregiver deletes their account, with all their children's data, from the Family tab after confirming their password (or, for an account made with Google that has no password, its email); there is no grace period or undo, and administrators are removed in the Django admin instead. Children can be edited or deleted from the Family tab. A forgotten password can be reset in the app with an emailed code (#126), and a signed-in caregiver or administrator can change theirs from Family or the Account tab; an account made with Google sets one with an emailed code (#142).
- **Fingerprint log-in is per phone** (#150). Turning it on gives the phone a random key from the server, kept in the phone's secure storage and sent only after Android's own fingerprint check (the phone's PIN or pattern is accepted too). The fingerprint never reaches Nurtura. Logging out keeps it; turning it off, a password reset or deleting the account revokes it. Anyone who can unlock the phone with an enrolled fingerprint or its PIN can open Nurtura. The AppCompat theme it needs on Android 7 and 8 has only been run on Android 15.
- **The email address can't be changed** in the app. Doing it safely needs a code sent to the new address first, so nobody can take over an account by typing someone else's email. A caregiver can delete the account and register again, or ask the privacy contact (the Data Protection Act's right to correction); an administrator's email is changed in the Django admin.
- **Continue with Google is Android only** (#130). Chrome and iOS need their own OAuth clients and set-up. Each signing key (every laptop's debug key, and the release key) needs its SHA-1 registered, and while the consent screen is in *Testing* only listed test users (up to 100) can use it.
- **The privacy notice gates only a child's own data** (#136). Until a caregiver agrees to the current notice, adding or changing a child and recording milestones are refused; generating ideas, marking done and rating for children who already exist are not. Accounts made before the notice are asked at their next sign-in. The notice says where to complain (the Data Protection Commissioner) but hasn't been reviewed by a lawyer, and the contact address comes from `PRIVACY_CONTACT`.
- **Registration says when an email is already registered,** so an address's account can be confirmed there, although the password-reset request deliberately doesn't say.
- **Sign-in codes need email.** With no internet, codes can only be read from the backend console (development). The Gmail account used for sending has a daily sending limit (about 500 messages).
- **"Active caregivers" is approximate.** Token sign-ins don't update Django's `last_login`, so the admin dashboard counts a caregiver as active if they generated ideas, recorded a milestone, or marked done or rated in the last 7 days.
- **Memory and start-up.** With the SBERT model loaded, the backend committed about 1.2 GB of memory on the development laptop. Without the warm-up, the first recommendation after a start takes about 14–15 s ([performance_recommendations.md](performance_recommendations.md)).
- **The end-to-end test needs a person** to type the emailed code. It can't run unattended in CI.
- **The admin's fonts come from Google Fonts.** Offline, the admin falls back to system fonts.
