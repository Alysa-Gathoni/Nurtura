# Sprint 4 retrieval spot-check

- **Date:** 2026-10-08
- **Published activities:** 54 (all embedded, none stale)
- **Model:** `all-MiniLM-L6-v2` (Sentence-BERT)
- **Method:** retrieval only, i.e. **SBERT cosine similarity with no rule-priority or age weighting**. This is the **SBERT-only baseline** that the Sprint 5 hybrid ranking will be compared against.
- **Generated with:** `python manage.py spot_check_retrieval --markdown` (sample children are created in a rolled-back transaction and never saved).

> **Hand check not yet done.** The *Relevant? (Y/N)* and *Notes* columns are intentionally blank, to be filled in by the researcher. Issue #31 (Sprint 4 Definition of done) stays open until then.

## Domain match: SBERT-only baseline

Share of each sample child's top 5 retrieved activities that are in the domain(s) the child's profile should retrieve. This is an automatic proxy; the hand check in the tables below judges actual relevance.

| Sample child | Expected domain(s) | Domain match |
|---|---|---|
| Language delay | Language | 4/5 (80%) |
| Motor delay | Motor | 5/5 (100%) |
| Cognitive delay | Cognitive | 3/5 (60%) |
| Socio-emotional delay | Socio-Emotional | 2/5 (40%) |
| Sensory concern | Sensory | 4/5 (80%) |
| Language and motor delay | Language + Motor | 4/5 (80%) |
| Expecting parent | Sensory | 2/5 (40%) |
| **Overall** | | **24/35 (69%)** |

## Results by sample child

### Language delay

*6 months, not cooing yet (expected by 4 months).* Expected: **Language**; profile top domain: **Language**

> Query: Activities for a 6-month-old baby to support language and communication: talking, babbling, first words, listening, singing and reading together. Still working on: Makes sounds like "oooo" or "aahh" (cooing).

| # | Similarity | Activity | Domain | Age range | Expected domain? | Relevant? (Y/N) | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 0.640 | ACT-0053 Eye Contact and Mother-Tongue Talk | Language | 0-3 months | yes |  |  |
| 2 | 0.626 | ACT-0030 Turn-Taking Sound Games | Language | 6-12 months | yes |  |  |
| 3 | 0.593 | ACT-0048 Cheering On Baby's Efforts | Socio-Emotional | 6-12 months | no |  |  |
| 4 | 0.564 | ACT-0052 Waiting for Baby's Response | Language | 6-12 months | yes |  |  |
| 5 | 0.544 | ACT-0023 Animal Sound Imitation Game | Language | 3-6 months | yes |  |  |

### Motor delay

*13 months, not pulling up to stand (expected by 12 months).* Expected: **Motor**; profile top domain: **Motor**

> Query: Activities for a 13-month-old toddler to support movement and physical skills: tummy time, rolling, crawling, walking, balance, and using hands and fingers. Still working on: Pulls up to stand.

| # | Similarity | Activity | Domain | Age range | Expected domain? | Relevant? (Y/N) | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 0.659 | ACT-0034 Ball Kicking and Throwing Play | Motor | 18-24 months | yes |  |  |
| 2 | 0.631 | ACT-0025 Reaching and Kicking at Toys | Motor | 3-6 months | yes |  |  |
| 3 | 0.594 | ACT-0024 Balancing While Holding Hands | Motor | 12-18 months | yes |  |  |
| 4 | 0.588 | ACT-0027 Reach-and-Roll Toy Retrieval | Motor | 6-12 months | yes |  |  |
| 5 | 0.563 | ACT-0001 Tummy Time | Motor | 0-3 months | yes |  |  |

### Cognitive delay

*10 months, not looking for dropped objects (expected by 9 months).* Expected: **Cognitive**; profile top domain: **Cognitive**

> Query: Activities for a 10-month-old baby to support thinking and problem-solving: exploring objects, cause and effect, hiding and finding, sorting and puzzles. Still working on: Looks for objects when dropped out of sight.

| # | Similarity | Activity | Domain | Age range | Expected domain? | Relevant? (Y/N) | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 0.624 | ACT-0028 Object Permanence Hide and Seek | Cognitive | 6-12 months | yes |  |  |
| 2 | 0.598 | ACT-0020 Outdoor Nature Walk and Observation | Sensory | 24-36 months | no |  |  |
| 3 | 0.571 | ACT-0038 Simple Puzzle and Sorting Play | Cognitive | 24-36 months | yes |  |  |
| 4 | 0.569 | ACT-0012 Mirror Play | Cognitive | 3-6 months | yes |  |  |
| 5 | 0.564 | ACT-0006 Texture Exploration | Sensory | 6-12 months | no |  |  |

### Socio-emotional delay

*10 months, not looking when name is called (expected by 9 months).* Expected: **Socio-Emotional**; profile top domain: **Socio-Emotional**

> Query: Activities for a 10-month-old baby to support social and emotional development: bonding, feelings, smiling, copying and playing with others. Still working on: Looks when you call their name.

| # | Similarity | Activity | Domain | Age range | Expected domain? | Relevant? (Y/N) | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 0.631 | ACT-0048 Cheering On Baby's Efforts | Socio-Emotional | 6-12 months | yes |  |  |
| 2 | 0.585 | ACT-0012 Mirror Play | Cognitive | 3-6 months | no |  |  |
| 3 | 0.559 | ACT-0016 Naming Feelings During Daily Routines | Socio-Emotional | 12-18 months | yes |  |  |
| 4 | 0.528 | ACT-0034 Ball Kicking and Throwing Play | Motor | 18-24 months | no |  |  |
| 5 | 0.510 | ACT-0030 Turn-Taking Sound Games | Language | 6-12 months | no |  |  |

### Sensory concern

*8 months, caregiver concerned about sensory development.* Expected: **Sensory**; profile top domain: **Sensory**

> Query: Activities for a 8-month-old baby to support the senses: touch and textures, sounds and music, sights, and calming sensory play. Enjoys water play, textures.

| # | Similarity | Activity | Domain | Age range | Expected domain? | Relevant? (Y/N) | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 0.655 | ACT-0006 Texture Exploration | Sensory | 6-12 months | yes |  |  |
| 2 | 0.604 | ACT-0020 Outdoor Nature Walk and Observation | Sensory | 24-36 months | yes |  |  |
| 3 | 0.586 | ACT-0013 Sound-Making Exploration | Sensory | 3-6 months | yes |  |  |
| 4 | 0.562 | ACT-0017 Water Play with Containers | Sensory | 12-18 months | yes |  |  |
| 5 | 0.556 | ACT-0046 Gentle Tickle and Touch Play | Socio-Emotional | 3-6 months | no |  |  |

### Language and motor delay

*19 months, not yet saying 3+ words or walking alone.* Expected: **Language + Motor**; profile top domain: **Language**

> Query: Activities for a 19-month-old toddler to support language and communication: talking, babbling, first words, listening, singing and reading together; and movement and physical skills: tummy time, rolling, crawling, walking, balance, and using hands and fingers. Still working on: Tries to say three or more words besides "mama" or "dada"; Walks without holding on to anyone or anything.

| # | Similarity | Activity | Domain | Age range | Expected domain? | Relevant? (Y/N) | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 0.604 | ACT-0053 Eye Contact and Mother-Tongue Talk | Language | 0-3 months | yes |  |  |
| 2 | 0.577 | ACT-0034 Ball Kicking and Throwing Play | Motor | 18-24 months | yes |  |  |
| 3 | 0.571 | ACT-0030 Turn-Taking Sound Games | Language | 6-12 months | yes |  |  |
| 4 | 0.556 | ACT-0025 Reaching and Kicking at Toys | Motor | 3-6 months | yes |  |  |
| 5 | 0.540 | ACT-0020 Outdoor Nature Walk and Observation | Sensory | 24-36 months | no |  |  |

### Expecting parent

*Due in about 3 months, Sensory concern (prenatal activities only).* Expected: **Sensory**; profile top domain: **Sensory**

> Query: Activities for an expecting parent during pregnancy to support the senses: touch and textures, sounds and music, sights, and calming sensory play.

| # | Similarity | Activity | Domain | Age range | Expected domain? | Relevant? (Y/N) | Notes |
|---|---|---|---|---|---|---|---|
| 1 | 0.623 | ACT-0002 Talking and Singing to the Baby During Pregnancy | Language | Prenatal | no |  |  |
| 2 | 0.587 | ACT-0009 Belly Massage and Gentle Touch | Sensory | Prenatal | yes |  |  |
| 3 | 0.534 | ACT-0041 Family Voices for the Baby | Language | Prenatal | no |  |  |
| 4 | 0.513 | ACT-0043 Daily Rest and Relaxing Routine | Socio-Emotional | Prenatal | no |  |  |
| 5 | 0.493 | ACT-0040 Soft Songs and Humming Time | Sensory | Prenatal | yes |  |  |
