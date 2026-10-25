# Caregiver evaluation: the questionnaire (Google Form)

At the end of each session, the participant fills in an anonymous Google Form on their own phone. It holds the usability (SUS) and satisfaction questions from [`caregiver_evaluation.md`](caregiver_evaluation.md). There is no paper version.

The relevance ratings and the "why was this suggested?" answer are **not** in the form. The participant gives them aloud, and the researcher writes them on the [session sheet](caregiver_evaluation_session_sheet.md). Spoken answers are fuller than typed ones on a phone, and the researcher can copy the explanation shown in the app next to the answer.

## Building the form

1. Go to [script.google.com](https://script.google.com), create a new project and paste in [`scripts/caregiver_questionnaire_form.gs`](../scripts/caregiver_questionnaire_form.gs).
2. Set `CONTACT` at the top to how participants can reach you. The script stops with a message while it still says FILL IN.
3. Run `createCaregiverQuestionnaire()`. It uses only the Forms service and asks for one permission, `https://www.googleapis.com/auth/forms`.
4. The execution log shows the edit link and the respondent link. Turn the respondent link into a QR code (for example with Google Chrome's "Create QR code for this page"), so participants can open it by scanning.

The script applies these settings. Check them once in the form's **Settings**:

- **Responses:** collect email addresses **off**; *Limit to 1 response* **off** (several participants may use the same phone); *Allow response editing* **off**.
- **Sign-in:** not required.
- **Presentation:** progress bar **on**; *Show link to submit another response* **off**; confirmation message "Thank you for taking part. You can close this page."

**Don't change the question titles.** The scorer finds the columns by their `SUS01`, `S1` and `O1` prefixes.

## The questions

**Page 1.** Form description, with `{CONTACT}` replaced:

> Thank you for trying Nurtura. Please answer these questions on your own, about the app you have just used. It takes about 5 minutes. There are no right or wrong answers: I'm testing the app, not you. This form is anonymous. It doesn't collect your name or email, so please don't type any personal details. You can skip the open questions, and you can stop at any time by closing the page. Questions: {CONTACT}.

- **Short answer, required**, accepting only P and two digits (help text: "Type P and then two digits, for example P03."): Participant number (the researcher will tell you, for example P03)

**Page 2: Using the app.** Each is a **required 1 to 5 scale**, from "Strongly disagree" (1) to "Strongly agree" (5). These are the 10 SUS items (Brooke, 1996), with "app" for "system" and "awkward" for "cumbersome" (Finstad, 2006).

- SUS01: I think that I would like to use this app frequently.
- SUS02: I found the app unnecessarily complex.
- SUS03: I thought the app was easy to use.
- SUS04: I think that I would need the support of a technical person to be able to use this app.
- SUS05: I found the various functions in this app were well integrated.
- SUS06: I thought there was too much inconsistency in this app.
- SUS07: I would imagine that most people would learn to use this app very quickly.
- SUS08: I found the app very awkward to use.
- SUS09: I felt very confident using the app.
- SUS10: I needed to learn a lot of things before I could get going with this app.

**Page 3: The suggestions.** The same required 1 to 5 scale.

- S1: I trust the activities the app suggested for my child.
- S2: The suggested activities would be useful for my child.
- S3: The "Why this?" explanations helped me understand why each activity was suggested.
- S4: I could do the suggested activities at home with things I already have.
- S5: I would keep using this app with my child.
- S6: I would recommend this app to another parent or carer.

**Page 4: In your own words.** **Paragraph, optional.**

- O1: What did you like most about the app?
- O2: What would you change?

## During the session

- **Hand over the participant number** (for example on a small card with the QR code). It's the only link between the form and the session sheet.
- **The participant answers alone,** on their own phone if they're happy to; otherwise on the session phone, after closing the app. The researcher doesn't read the answers or comment on them.
- **Every scale item is required,** so a submitted response always has a complete SUS score.
- **No internet:** the form needs a connection to submit. If there's none, give the participant the QR code and their number, and ask them to fill it in the same day. Note this on the session sheet.

## Scoring

After all sessions, export the responses (**Responses → Download responses (.csv)**), keep the file **outside the repository**, and run:

```
python scripts/score_caregiver_questionnaire.py responses.csv --participants P01 P02 P03
```

List after `--participants` the numbers on your session sheets. The script prints each participant's SUS score, the mean and range, each satisfaction item's median and answer counts, and every open answer. It warns about a participant number given more than once, a number not on your list, and a listed number with no response, so you can decide which response to keep. It only prints; it never edits the file.

## References

- Brooke, J. (1996). SUS: A "quick and dirty" usability scale. In P. W. Jordan, B. Thomas, B. A. Weerdmeester & I. L. McClelland (Eds.), *Usability Evaluation in Industry* (pp. 189–194). Taylor & Francis.
- Finstad, K. (2006). The System Usability Scale and non-native English speakers. *Journal of Usability Studies*, 1(4), 185–188.
