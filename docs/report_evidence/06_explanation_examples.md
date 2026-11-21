# Explanation examples

> Generated 2026-11-21T22:28:54+03:00 at commit `48210e2` by `backend\venv\Scripts\python.exe scripts\report_evidence\explanation_examples.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

Three fictional children (not in the evaluation), created in a rolled-back transaction. Score = age weight × ((1 − α) × normalised similarity + α × priority), α = 0.7. Raw: `raw/explanation_rules_fired.csv`, `raw/explanation_top5.csv`, `raw/explanation_profiles.json`.

## E1: Fictional: expecting in about 3 months; caregiver wants support with language.

- **Query sent to SBERT:** "Activities for an expecting parent during pregnancy to support language and communication: talking, babbling, first words, listening, singing and reading together."
- **Raw area scores** (baseline 1 + rule adjustments): {'Cognitive': 1.0, 'Language': 6.0, 'Motor': 1.0, 'Sensory': 1.0, 'Socio-Emotional': 1.0}
- **Priorities** (normalised, top area = 1): {'Cognitive': 0.167, 'Language': 1.0, 'Motor': 0.167, 'Sensory': 0.167, 'Socio-Emotional': 0.167}
- **Eligible activities scored:** 60

Rules that fired:

| Rule | Adjustments | Reason |
|---|---|---|
| caregiver-concern | Language +5 | You told us you'd like support with Language development. |

Top five at α = 0.7:

| # | Activity | Area | Age | Similarity | Norm. sim. | Priority | Age weight | Score |
|---|---|---|---|---|---|---|---|---|
| 1 | Talking and Singing to the Baby During Pregnancy (ACT-0002) | Language | Prenatal | 0.3717 | 1.0 | 1.0 | 1.0 | 1.0 |
| 2 | Family Voices for the Baby (ACT-0041) | Language | Prenatal | 0.2926 | 0.7824 | 1.0 | 1.0 | 0.9347 |
| 3 | Father's Daily Words to the Baby (ACT-0264) | Language | Prenatal | 0.2469 | 0.6569 | 1.0 | 1.0 | 0.8971 |
| 4 | Reading a Story to the Bump (ACT-0063) | Language | Prenatal | 0.2218 | 0.5877 | 1.0 | 1.0 | 0.8763 |
| 5 | Talking About Your Chores to the Baby (ACT-0265) | Language | Prenatal | 0.1815 | 0.4771 | 1.0 | 1.0 | 0.8431 |

Explanations shown to the caregiver:

1. You said you'd like support with language and communication. It's an activity for parents during pregnancy. Its aim is to help your baby start getting to know your voice and the rhythm of your home language.
2. You said you'd like support with language and communication. It's an activity for parents during pregnancy. Its aim is to let your baby get to know the voices of the people around them.
3. You said you'd like support with language and communication. It's an activity for parents during pregnancy. Its aim is to help the baby's father start talking with the baby before birth.
4. You said you'd like support with language and communication. It's an activity for parents during pregnancy. Its aim is to help your baby get to know your voice before birth.
5. You said you'd like support with language and communication. It's an activity for parents during pregnancy. Its aim is to get into the habit of talking to your baby all through the day.

## E2: Fictional: 13 months; "Waves bye-bye" (CDC, by 12 months) recorded as Not yet.

- **Query sent to SBERT:** "Activities for a 13-month-old toddler to support language and communication: talking, babbling, first words, listening, singing and reading together. Still working on: Waves "bye-bye"."
- **Raw area scores** (baseline 1 + rule adjustments): {'Cognitive': 1.0, 'Language': 11.0, 'Motor': 1.0, 'Sensory': 1.0, 'Socio-Emotional': 1.0}
- **Priorities** (normalised, top area = 1): {'Cognitive': 0.091, 'Language': 1.0, 'Motor': 0.091, 'Sensory': 0.091, 'Socio-Emotional': 0.091}
- **Eligible activities scored:** 389

Rules that fired:

| Rule | Adjustments | Reason |
|---|---|---|
| due-milestone-not-yet | Language +10 | Not yet: “Waves "bye-bye"” — most children do this by 12 months (CDC). |

Top five at α = 0.7:

| # | Activity | Area | Age | Similarity | Norm. sim. | Priority | Age weight | Score |
|---|---|---|---|---|---|---|---|---|
| 1 | Songs About Daily Routines (ACT-0179) | Language | 12-18 months | 0.218 | 0.5275 | 1.0 | 1.0 | 0.8582 |
| 2 | Talking Through a Soft Toy (ACT-0180) | Language | 12-18 months | 0.1786 | 0.403 | 1.0 | 1.0 | 0.8209 |
| 3 | Building on Baby's Words (ACT-0176) | Language | 12-18 months | 0.1784 | 0.4024 | 1.0 | 1.0 | 0.8207 |
| 4 | Real Words, Simple Directions (ACT-0375) | Language | 12-18 months | 0.1674 | 0.3675 | 1.0 | 1.0 | 0.8102 |
| 5 | In and Out Words (ACT-0377) | Language | 12-18 months | 0.1635 | 0.3552 | 1.0 | 1.0 | 0.8066 |

Explanations shown to the caregiver:

1. You recorded “Waves ‘bye-bye’” as not yet; most children do this by 12 months. It's designed for children aged 12–18 months, your child's age group. Its aim is to help your child learn words for the things you do every day.
2. You recorded “Waves ‘bye-bye’” as not yet; most children do this by 12 months. It's designed for children aged 12–18 months, your child's age group. Its aim is to invite your child to talk and pretend with a soft toy.
3. You recorded “Waves ‘bye-bye’” as not yet; most children do this by 12 months. It's designed for children aged 12–18 months, your child's age group. Its aim is to help your child learn new words by building on the ones they say.
4. You recorded “Waves ‘bye-bye’” as not yet; most children do this by 12 months. It's designed for children aged 12–18 months, your child's age group. Its aim is to help your child understand short, simple instructions.
5. You recorded “Waves ‘bye-bye’” as not yet; most children do this by 12 months. It's designed for children aged 12–18 months, your child's age group. Its aim is to help your child learn the words in and out.

## E3: Fictional: 8 months; enjoys water, sand and different textures; no concerns.

- **Query sent to SBERT:** "Activities for a 8-month-old baby to support the senses: touch and textures, sounds and music, sights, and calming sensory play. Enjoys water, sand, textures."
- **Raw area scores** (baseline 1 + rule adjustments): {'Cognitive': 1.0, 'Language': 1.0, 'Motor': 1.0, 'Sensory': 7.0, 'Socio-Emotional': 1.0}
- **Priorities** (normalised, top area = 1): {'Cognitive': 0.143, 'Language': 0.143, 'Motor': 0.143, 'Sensory': 1.0, 'Socio-Emotional': 0.143}
- **Eligible activities scored:** 389

Rules that fired:

| Rule | Adjustments | Reason |
|---|---|---|
| sensory-interest | Sensory +2 | Enjoys “water”, which sensory activities build on. |
| sensory-interest | Sensory +2 | Enjoys “sand”, which sensory activities build on. |
| sensory-interest | Sensory +2 | Enjoys “textures”, which sensory activities build on. |

Top five at α = 0.7:

| # | Activity | Area | Age | Similarity | Norm. sim. | Priority | Age weight | Score |
|---|---|---|---|---|---|---|---|---|
| 1 | Backyard Touch and Talk (ACT-0357) | Sensory | 6-12 months | 0.2965 | 0.9377 | 1.0 | 1.0 | 0.9813 |
| 2 | Texture Exploration (ACT-0006) | Sensory | 6-12 months | 0.2909 | 0.9163 | 1.0 | 1.0 | 0.9749 |
| 3 | New Tastes and Textures at Mealtimes (ACT-0161) | Sensory | 6-12 months | 0.2749 | 0.8545 | 1.0 | 1.0 | 0.9563 |
| 4 | Rain Shaker for Bath Time (ACT-0358) | Sensory | 6-12 months | 0.256 | 0.7817 | 1.0 | 1.0 | 0.9345 |
| 5 | Treasure Basket of Shapes and Textures (ACT-0166) | Sensory | 6-12 months | 0.2402 | 0.7207 | 1.0 | 1.0 | 0.9162 |

Explanations shown to the caregiver:

1. You said your child enjoys water, sand and textures, which points us towards activities for the senses. It's designed for children aged 6–12 months, your child's age group. Its aim is to help your baby explore new feelings, smells and sounds outside.
2. You said your child enjoys water, sand and textures, which points us towards activities for the senses; this activity uses textures. It's designed for children aged 6–12 months, your child's age group. Its aim is to help your baby explore different textures by touch.
3. You said your child enjoys water, sand and textures, which points us towards activities for the senses; this activity uses textures. It's designed for children aged 6–12 months, your child's age group. Its aim is to help your baby get used to many tastes and textures.
4. You said your child enjoys water, sand and textures, which points us towards activities for the senses; this activity uses water. It's designed for children aged 6–12 months, your child's age group. Its aim is to help your baby enjoy using their senses at bath time.
5. You said your child enjoys water, sand and textures, which points us towards activities for the senses; this activity uses textures. It's designed for children aged 6–12 months, your child's age group. Its aim is to help your baby explore objects of different shapes and textures.
