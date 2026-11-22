"""Reading an explanation back from its text alone (#69, #270).

Used by the explanation tests and by evaluate_v3_full to check that every
milestone, concern and interest an explanation names is in the child's stored
profile, and that no explanation shows a score.
"""

import re

from .explanations import SUPPORT

SUPPORT_TO_DOMAIN = {phrase: domain for domain, phrase in SUPPORT.items()}

# A decimal number, a percentage or the word "score" would expose a score.
SCORE_PATTERN = re.compile(r"\d+\.\d+|\d+\s*%|\bscore", re.IGNORECASE)

# Sentences end with a full stop; quoted milestones never contain one followed
# by a space and a capital letter.
SENTENCE_END = re.compile(r"(?<=\.)\s+(?=[A-Z“])")


def named_in(text):
    """(milestones, concerns, interests) an explanation names, from its text."""
    milestones = [
        m.replace("‘", '"').replace("’", '"') for m in re.findall(r"“(.*?)”", text)
    ]
    concerns = [
        SUPPORT_TO_DOMAIN[m]
        for m in re.findall(r"like support with (.+?)(?: and that|\.|,)", text)
    ]
    interests = []
    for phrase in re.findall(
        r"(?:enjoys|activity uses|It uses) (.+?)(?:, which|;|\.|,)", text
    ):
        interests.extend(p.strip() for p in phrase.split(" and "))
    return milestones, concerns, interests


def sentences(text):
    return [s for s in SENTENCE_END.split(text.strip()) if s]


def check(child, texts):
    """Counts for one child's explanations against their stored profile."""
    stored_milestones = set(child.milestones.values_list("description", flat=True))
    stored_interests = {" ".join(str(i).lower().split()) for i in child.interests}
    stored_concerns = set(child.concerns)
    result = {
        "explanations": 0,
        "max_sentences": 0,
        "named": 0,
        "not_in_profile": 0,
        "showing_a_score": 0,
        "examples_not_in_profile": [],
    }
    for text in texts:
        milestones, concerns, interests = named_in(text)
        missing = (
            [m for m in milestones if m not in stored_milestones]
            + [c for c in concerns if c not in stored_concerns]
            + [i for i in interests if i not in stored_interests]
        )
        result["explanations"] += 1
        result["max_sentences"] = max(result["max_sentences"], len(sentences(text)))
        result["named"] += len(milestones) + len(concerns) + len(interests)
        result["not_in_profile"] += len(missing)
        result["showing_a_score"] += bool(SCORE_PATTERN.search(text))
        result["examples_not_in_profile"] += missing
    return result
