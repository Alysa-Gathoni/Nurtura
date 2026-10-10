# Explanation reader test: Google Form

An anonymous Google Form version of the reader test, for when the test can't be run in person. The cards are the same 10 as in [`explanation_reader_test_cards.md`](explanation_reader_test_cards.md) (tag `sprint6-explanations-v1`). The answer key stays in [`explanation_reader_test.md`](explanation_reader_test.md) and is never put in the form.

There are two ways to build the form:

1. **Automatically (recommended).** Paste [`scripts/reader_test_forms.gs`](../scripts/reader_test_forms.gs) into a new project at script.google.com, set `CONTACT` at the top, and run `createReaderTestForms()`. It creates **"Nurtura wording check (A)"** (cards 1 to 10) and **"(B)"** (cards 10 to 1) in your own Drive. It uses only the Forms service and needs one permission, `https://www.googleapis.com/auth/forms`. It stops with a message if `CONTACT` still says FILL IN.
2. **By hand**, using the copy-paste blocks below. Build version A in the order shown; for version B, duplicate A and move the card pages into reverse order (10 to 1). **Keep every question title exactly as written**, including the `C01 Q1:` prefix: the scoring script matches columns by these titles.

Send half of the respondents the A link and half the B link, so card order doesn't favour any card.

## Settings

In the form's **Settings**:

- **Responses:** collect email addresses **off**; *Limit to 1 response* **off**; *Allow response editing* **off**.
- **Responses / sign-in:** don't require sign-in (on a Google Workspace account, turn off *Restrict to users in …*).
- **Presentation:** *Show progress bar* **on**; *Show link to submit another response* **off**.
- **Presentation → Confirmation message:**

```
Thank you. You can close this page.
```

## Page 1: about this check

Form description (replace `{CONTACT}` with how respondents can reach you):

```
Nurtura is a student project that suggests early-childhood activities to caregivers. I'm checking whether its explanations are easy to understand. You'll see 10 made-up children and the activity the app suggested for each. For every one, please say in your own words why you think it was suggested, and whether anything worried or confused you. It takes about 10 to 15 minutes. There are no right or wrong answers: I'm testing the wording, not you. This form is anonymous. I don't collect your name or email, so please don't type any personal details. Taking part is voluntary and you can stop at any time by closing the page. Answers are used only in my project report. If you continue, you agree to take part. Questions: {CONTACT}.
```

Then two **required** multiple-choice questions, each with the options `Yes` and `No`:

```
Do you look after a child under 5 (as a parent, relative or carer)?
```

```
Had you seen or heard about this project before today?
```

Respondents who answer **Yes** to the second question are excluded from scoring.

## Card pages

Add a **section** (page break) for each card. The section title is the card's own number, so "Card 7 of 10" stays card 7 in version B too. Paste the description, then add the three questions.

### Card 1

Section title:

```
Card 1 of 10
```

Section description:

```
Your child: You're expecting: your baby is due in about 4 months. You asked for support with: social and emotional development.

Suggested activity: Sharing Hopes and Worries About the Baby

You said you'd like support with social and emotional development. It's an activity for parents during pregnancy. Its aim is to support your emotional wellbeing, which shapes your baby's early surroundings.
```

Questions:

1. **Paragraph, required:** `C01 Q1: In your own words, why was this activity suggested for this child?`
2. **Multiple choice, required**, options `No` and `Yes (tell us below)`: `C01 Q2: Did any sentence worry or confuse you?`
3. **Paragraph, optional:** `C01 Q3: If yes, which sentence, and why?`

### Card 2

Section title:

```
Card 2 of 10
```

Section description:

```
Your child: Your child is 2½ months old. Milestones you recorded: “Holds head up when on tummy”: Not yet.

Suggested activity: Tummy Time

You recorded “Holds head up when on tummy” as not yet; most children do this by 2 months. It's designed for children aged 0–3 months, your child's age group. Its aim is to help your baby build the neck, shoulder and upper-body strength needed for rolling, sitting and crawling.
```

Questions:

1. **Paragraph, required:** `C02 Q1: In your own words, why was this activity suggested for this child?`
2. **Multiple choice, required**, options `No` and `Yes (tell us below)`: `C02 Q2: Did any sentence worry or confuse you?`
3. **Paragraph, optional:** `C02 Q3: If yes, which sentence, and why?`

### Card 3

Section title:

```
Card 3 of 10
```

Section description:

```
Your child: Your child is 2½ months old. Milestones you recorded: “Smiles when you talk to or smile at them”: Not yet.

Suggested activity: Face-to-Face Cooing Exchange

You recorded “Smiles when you talk to or smile at them” as not yet; most children do this by 2 months. It's designed for children aged 0–3 months, your child's age group. Its aim is to help you and your baby feel close and take turns with each other.
```

Questions:

1. **Paragraph, required:** `C03 Q1: In your own words, why was this activity suggested for this child?`
2. **Multiple choice, required**, options `No` and `Yes (tell us below)`: `C03 Q2: Did any sentence worry or confuse you?`
3. **Paragraph, optional:** `C03 Q3: If yes, which sentence, and why?`

### Card 4

Section title:

```
Card 4 of 10
```

Section description:

```
Your child: Your child is 4½ months old. You asked for support with: sensory development. Your child enjoys: music, rattles.

Suggested activity: Sound-Making Exploration

You said you'd like support with sensory development and that your child enjoys music, which points us towards activities for the senses. It's designed for children aged 3–6 months, your child's age group. Its aim is to help your baby's listening skills grow through lots of different sounds.
```

Questions:

1. **Paragraph, required:** `C04 Q1: In your own words, why was this activity suggested for this child?`
2. **Multiple choice, required**, options `No` and `Yes (tell us below)`: `C04 Q2: Did any sentence worry or confuse you?`
3. **Paragraph, optional:** `C04 Q3: If yes, which sentence, and why?`

### Card 5

Section title:

```
Card 5 of 10
```

Section description:

```
Your child: Your child is 7 months old. Milestones you recorded: “Laughs”: Achieved; “Rolls from tummy to back”: Achieved.

Suggested activity: Texture Exploration

You haven't asked for help with a particular area, so this is a general activity for your child's age. It's designed for children aged 6–12 months, your child's age group. Its aim is to help your baby explore different textures by touch.
```

Questions:

1. **Paragraph, required:** `C05 Q1: In your own words, why was this activity suggested for this child?`
2. **Multiple choice, required**, options `No` and `Yes (tell us below)`: `C05 Q2: Did any sentence worry or confuse you?`
3. **Paragraph, optional:** `C05 Q3: If yes, which sentence, and why?`

### Card 6

Section title:

```
Card 6 of 10
```

Section description:

```
Your child: Your child is 15½ months old. Milestones you recorded: “Takes a few steps on their own”: Not yet; “Shows you affection (hugs, cuddles, or kisses you)”: Not yet.

Suggested activity: Balancing While Holding Hands

You recorded “Takes a few steps on their own” as not yet; most children do this by 15 months. It's designed for children aged 12–18 months, your child's age group. Its aim is to help your child build balance and confidence in walking.
```

Questions:

1. **Paragraph, required:** `C06 Q1: In your own words, why was this activity suggested for this child?`
2. **Multiple choice, required**, options `No` and `Yes (tell us below)`: `C06 Q2: Did any sentence worry or confuse you?`
3. **Paragraph, optional:** `C06 Q3: If yes, which sentence, and why?`

### Card 7

Section title:

```
Card 7 of 10
```

Section description:

```
Your child: Your child is 20 months old. Milestones you recorded: “Plays with toys in a simple way, like pushing a toy car”: Not yet.

Suggested activity: Buttons and Knobs Exploration Toy

You recorded “Plays with toys in a simple way, like pushing a toy car” as not yet; most children do this by 18 months. It's designed for children aged 18–24 months, your child's age group. Its aim is to help your child see how actions make things happen and solve small problems with their fingers.
```

Questions:

1. **Paragraph, required:** `C07 Q1: In your own words, why was this activity suggested for this child?`
2. **Multiple choice, required**, options `No` and `Yes (tell us below)`: `C07 Q2: Did any sentence worry or confuse you?`
3. **Paragraph, optional:** `C07 Q3: If yes, which sentence, and why?`

### Card 8

Section title:

```
Card 8 of 10
```

Section description:

```
Your child: Your child is 20 months old. You asked for support with: sensory development. Your child enjoys: textures.

Suggested activity: Water Play with Containers

You said you'd like support with sensory development and that your child enjoys textures, which points us towards activities for the senses; this activity uses textures. It's written for slightly younger children (12–18 months), so your child may find it easy; adapt it to suit them. Its aim is to help your child explore through their senses by pouring and feeling different textures.
```

Questions:

1. **Paragraph, required:** `C08 Q1: In your own words, why was this activity suggested for this child?`
2. **Multiple choice, required**, options `No` and `Yes (tell us below)`: `C08 Q2: Did any sentence worry or confuse you?`
3. **Paragraph, optional:** `C08 Q3: If yes, which sentence, and why?`

### Card 9

Section title:

```
Card 9 of 10
```

Section description:

```
Your child: Your child is 16 months old. Milestones you recorded: “Waves ‘bye-bye’”: Not yet; “Tries to say three or more words besides ‘mama’ or ‘dada’”: Not yet.

Suggested activity: Naming Everyday Objects

You recorded “Waves ‘bye-bye’” as not yet; most children do this by 12 months. “Tries to say three or more words besides ‘mama’ or ‘dada’” often comes next; most children do this by 18 months. It's designed for children aged 12–18 months, your child's age group. Its aim is to help your child understand and say more words by linking words to real objects.
```

Questions:

1. **Paragraph, required:** `C09 Q1: In your own words, why was this activity suggested for this child?`
2. **Multiple choice, required**, options `No` and `Yes (tell us below)`: `C09 Q2: Did any sentence worry or confuse you?`
3. **Paragraph, optional:** `C09 Q3: If yes, which sentence, and why?`

### Card 10

Section title:

```
Card 10 of 10
```

Section description:

```
Your child: Your child is 13 months old. Milestones you recorded: “Standing with assistance”: Not yet.

Suggested activity: Balancing While Holding Hands

You recorded “Standing with assistance” as not yet; almost all children do this by about 12 months. It's designed for children aged 12–18 months, your child's age group. Its aim is to help your child build balance and confidence in walking.
```

Questions:

1. **Paragraph, required:** `C10 Q1: In your own words, why was this activity suggested for this child?`
2. **Multiple choice, required**, options `No` and `Yes (tell us below)`: `C10 Q2: Did any sentence worry or confuse you?`
3. **Paragraph, optional:** `C10 Q3: If yes, which sentence, and why?`

## Pass rule (form version)

- A respondent is **valid** unless they answered **Yes** to "Had you seen or heard about this project before today?".
- An own-words answer (Q1) is **understood** if it mentions the child's **need**, **age** or **stated interest** behind the card's main reason in the answer key.
- A card **passes** if at least **80%** of valid respondents' answers are understood.
- The test **passes** if at least **8 of 10** cards pass **and** there are at least **10 valid respondents**.
- Every "worried or confused" answer is reviewed, whatever the result.

This replaces the in-person rule (at least 4 of 5 readers per card) only when the test is run with this form.

## Collecting and scoring the responses

1. In each form, open **Responses** and choose **Link to Sheets**, to keep a copy of every response in a Google Sheet.
2. In each Sheet, use **File → Download → Comma-separated values (.csv)**. That gives one CSV for A and one for B.
3. Score both together, from the repository root:

```
python scripts/score_reader_test.py responses_A.csv responses_B.csv
```

It prints:

- the number of valid and excluded respondents;
- for each card, every answer with an automatic understood/not-understood mark, and the card's result;
- the worry and confusion quotes, listed separately;
- the overall result.

The automatic mark is only a keyword check: **read every answer and correct the marks yourself** before reporting. The script never edits the CSVs or any other file.

Keep the CSVs out of the repository: they're research data. The form is anonymous, but a respondent may still have typed something personal.
