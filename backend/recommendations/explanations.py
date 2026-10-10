"""Caregiver-readable explanations for recommendations (FR-11, #69).

An explanation is built only from:
- the rules that fired for the activity's developmental area (milestones not
  yet reached, just starting or coming next; a caregiver's request for
  support; a sensory interest);
- the caregiver's stated interests, where the activity's text uses them;
- the activity's age fit (its age range against the child's);
- the activity's plain_aim, when one has been written and approved.

It never shows scores and never uses diagnostic language. CDC milestones say
"Most children do this by N months"; WHO milestones say "Almost all children
do this by about N months" (N rounded up), because WHO ages are the end of
the window in which almost all children reach the skill.

Each milestone group (not yet, just starting, coming next; at most two
groups) is one sentence: "You recorded “X” as not yet; most children do
this by N months."

At most four sentences. Above that, these are dropped in order: a
stand-alone "It uses X" sentence; the age sentence, but only its plain
"your child's age group" version (slightly younger, older or further
away is always kept); the support/interest sentence, but only when a
milestone group is already giving the reason. The first reason and the
aim sentence are never dropped.

With no reason for the activity's area, the fallback depends on the
child: no rule fired at all (nothing asked for) gives "You haven't asked
for help with a particular area, ..."; otherwise the activity is outside
the areas the child is working on, and gets "This one is a good fit for
your child's age and supports {area}."

Changing any wording here must bump EXPLANATION_VERSION, so the next request
stores a new batch instead of reusing explanations with the old wording.
"""

import math
import re
from dataclasses import dataclass, field

from activities.choices import AgeRange
from profiles.rules.facts import ConcernFact, InterestFact

from .ranking import FURTHER, ONE_OLDER, ONE_YOUNGER, SAME_BRACKET, TWO_AWAY

EXPLANATION_VERSION = "2"
MAX_SENTENCES = 4
MAX_NAMED_MILESTONES = 3
MAX_GROUPS = 2

# Plain words for each area, and for asking for support with it.
AREA = {
    "Cognitive": "thinking and problem-solving",
    "Language": "language and communication",
    "Motor": "movement",
    "Sensory": "the senses",
    "Socio-Emotional": "social and emotional development",
}
SUPPORT = dict(AREA, Sensory="sensory development")

NOT_YET = "due-milestone-not-yet"
EMERGING = "due-milestone-emerging"
UPCOMING = "upcoming-milestone"
MILESTONE_RULES = (NOT_YET, EMERGING, UPCOMING)  # in display order


@dataclass
class Explanation:
    """The text, and what it names (for checking against the child's profile)."""

    text: str
    sentences: list = field(default_factory=list)
    milestones: list = field(default_factory=list)
    concerns: list = field(default_factory=list)
    interests: list = field(default_factory=list)


def quote(text):
    """Curly quotes; quotes inside a milestone become single quotes."""
    inner = re.sub(r'"([^"]*)"', lambda m: "‘" + m.group(1) + "’", text)
    return f"“{inner}”"


def _join(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _named(descriptions):
    shown = [quote(d) for d in descriptions[:MAX_NAMED_MILESTONES]]
    hidden = len(descriptions) - MAX_NAMED_MILESTONES
    if hidden > 0:
        shown.append(f"{hidden} more you recorded")
    return _join(shown)


def _by_when(fact):
    age = float(fact.expected_age_months)
    if fact.source == "WHO":
        return ("Almost all", f"about {math.ceil(age)} months")
    return ("Most", f"{age:g} months")


def _ages(facts):
    groups = {}
    for fact in facts:
        groups.setdefault(_by_when(fact), []).append(fact)
    if len(groups) == 1:
        (who, when), members = next(iter(groups.items()))
        pronoun = "this" if len(members) == 1 else "these"
        return f"{who.lower()} children do {pronoun} by {when}"
    clauses = []
    for i, ((who, when), members) in enumerate(groups.items()):
        subject = f"{who.lower()} children" if i == 0 else who.lower()
        names = _named([m.description for m in members])
        clauses.append(f"{subject} do {names} by {when}")
    return ", and ".join(clauses)


def _milestone_groups(firings):
    """[(sentence, facts)] per status, not yet > just starting > upcoming."""
    by_rule = {}
    for f in firings:
        if f.rule.name in MILESTONE_RULES:
            by_rule.setdefault(f.rule.name, []).append(f)
    groups = []
    for rule in MILESTONE_RULES:
        if rule not in by_rule:
            continue
        members = sorted(
            by_rule[rule],
            key=lambda f: (
                -max(f.adjustments.values()),
                float(f.fact.expected_age_months),
                f.fact.description,
            ),
        )
        facts = [f.fact for f in members]
        names = _named([fact.description for fact in facts])
        if rule == NOT_YET:
            lead = f"You recorded {names} as not yet"
        elif rule == EMERGING:
            lead = f"You recorded {names} as just starting"
        else:
            lead = f"{names} {'often comes' if len(facts) == 1 else 'often come'} next"
        # Only the milestones named in the lead get an age.
        sentence = f"{lead}; {_ages(facts[:MAX_NAMED_MILESTONES])}."
        groups.append((sentence, facts))
    return groups[:MAX_GROUPS]


def _stem(word):
    word = word.lower()
    return word[:-1] if word.endswith("s") and len(word) > 3 else word


def _clean(interest):
    return " ".join(str(interest).lower().split())


def used_interests(interests, activity):
    """The child's interests whose words all appear in the activity's text."""
    text = f"{activity.activity_name} {activity.description}"
    words = {_stem(w) for w in re.findall(r"[A-Za-z]+", text)}
    found = []
    for interest in interests:
        tokens = re.findall(r"[A-Za-z]+", str(interest))
        if tokens and all(_stem(t) in words for t in tokens):
            found.append(_clean(interest))
    return found


def _age_sentence(activity, weight):
    if activity.age_range == AgeRange.PRENATAL:
        return "It's an activity for parents during pregnancy."
    span = str(activity.age_range).replace("-", "–")
    if weight == SAME_BRACKET:
        return f"It's designed for children aged {span}, your child's age group."
    if weight == ONE_YOUNGER:
        return (
            f"It's written for slightly younger children ({span}), so your child "
            "may find it easy; adapt it to suit them."
        )
    if weight == ONE_OLDER:
        return (
            f"It's designed for slightly older children ({span}), so keep it "
            "playful and follow your child's lead."
        )
    if weight in (TWO_AWAY, FURTHER):
        return (
            f"It's designed for children aged {span}, so adapt it to your child's age."
        )
    raise ValueError(f"unexpected age weight {weight}")


def explain(child, evaluation, ranked):
    """The explanation for one ranked activity (a RankedActivity)."""
    activity = ranked.activity
    domain = str(activity.developmental_domain)
    firings = [f for f in evaluation.firings if domain in f.adjustments]

    groups = _milestone_groups(firings)
    concern = any(isinstance(f.fact, ConcernFact) for f in firings)
    rule_interests = []
    for f in firings:
        if isinstance(f.fact, InterestFact) and f.fact.interest not in rule_interests:
            rule_interests.append(f.fact.interest)
    used = used_interests(child.interests, activity)
    used_named = [i for i in used if i in rule_interests]
    used_alone = [i for i in used if i not in rule_interests]

    support = None
    if concern or rule_interests:
        if concern and rule_interests:
            support = (
                f"You said you'd like support with {SUPPORT[domain]} and that your "
                f"child enjoys {_join(rule_interests)}"
            )
        elif concern:
            support = f"You said you'd like support with {SUPPORT[domain]}"
        else:
            support = f"You said your child enjoys {_join(rule_interests)}"
        if rule_interests:
            support += f", which points us towards activities for {AREA[domain]}"
        if used_named:
            support += f"; this activity uses {_join(used_named)}"
        support += "."

    fallback = None
    if not groups and support is None:
        if not evaluation.firings:
            fallback = (
                "You haven't asked for help with a particular area, so this is a "
                "general activity for your child's age."
            )
        else:
            fallback = (
                "This one is a good fit for your child's age and supports "
                f"{AREA[domain]}."
            )
    uses = (
        f"It uses {_join(used_alone)}, which you said your child enjoys."
        if used_alone
        else None
    )
    age = _age_sentence(activity, ranked.age_weight)
    aim = f"Its aim is to {activity.plain_aim.strip()}." if activity.plain_aim else None

    parts = {
        "groups": [sentence for sentence, _ in groups],
        "support": [support] if support else [],
        "fallback": [fallback] if fallback else [],
        "uses": [uses] if uses else [],
        "age": [age],
        "aim": [aim] if aim else [],
    }
    plain_age = ranked.age_weight == SAME_BRACKET or (
        activity.age_range == AgeRange.PRENATAL
    )
    droppable = [
        ("uses", True),
        ("age", plain_age),
        ("support", bool(groups)),  # only when a milestone already explains it
    ]
    for key, allowed in droppable:
        if sum(len(v) for v in parts.values()) <= MAX_SENTENCES:
            break
        if allowed:
            parts[key] = []

    order = ("groups", "support", "fallback", "uses", "age", "aim")
    sentences = [s for key in order for s in parts[key]]
    milestones = [
        fact.description for _, facts in groups for fact in facts[:MAX_NAMED_MILESTONES]
    ]
    return Explanation(
        text=" ".join(sentences),
        sentences=sentences,
        milestones=milestones,
        concerns=[domain] if parts["support"] and concern else [],
        interests=(
            (rule_interests + used_named if parts["support"] else [])
            + (used_alone if parts["uses"] else [])
        ),
    )
