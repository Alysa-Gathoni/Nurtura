"""Links between catalogue milestones (#289).

The CDC and WHO checklists sometimes describe the same skill, and the WHO
gross-motor milestones follow an order. Without these links the feedback
sheet offered a 14-month-old who walks with help both "Sits without
support" and "Sitting without support", and "Standing with assistance";
ticking that one recorded it as only just starting.

TWINS: the same skill in both checklists. The first key is the one shown;
an observation of either counts for both.

WALKING_SEQUENCE: the WHO Multicentre Growth Reference Study order of the
gross-motor milestones (WHO Acta Paediatrica 2006, Suppl 450), with the
matching CDC milestones placed in it. Achieving a step implies the earlier
steps. Hands-and-knees crawling is left out: WHO notes that some children
never crawl. Fine-motor and other skills aren't implied by walking.

Only what is offered or listed changes. Recorded observations are never
altered, and the rule engine, ranking and referral are unchanged.
"""

TWINS = (
    ("CDC-09M-MO-04", "WHO-MO-01"),  # Sits without support
    # WHO's walking with assistance is stepping while holding onto furniture.
    ("CDC-12M-MO-02", "WHO-MO-04"),  # Walks, holding on to furniture
    ("CDC-18M-MO-01", "WHO-MO-06"),  # Walks without holding on / alone
)

WALKING_SEQUENCE = (
    ("CDC-09M-MO-04", "WHO-MO-01"),  # sitting without support
    ("WHO-MO-02", "CDC-12M-MO-01"),  # standing with assistance; pulls up
    ("CDC-12M-MO-02", "WHO-MO-04"),  # walking with assistance (cruising)
    ("WHO-MO-05",),  # standing alone
    ("CDC-15M-MO-01",),  # takes a few steps on their own
    ("CDC-18M-MO-01", "WHO-MO-06"),  # walking alone
)

_TWIN = {a: b for a, b in TWINS} | {b: a for a, b in TWINS}
_HIDDEN_TWINS = {b for _, b in TWINS}


def is_hidden_twin(key):
    """True for the twin that isn't shown (the WHO wording of a CDC skill)."""
    return key in _HIDDEN_TWINS


def implied_keys(achieved):
    """Keys settled by the Achieved keys: their twins, and the earlier steps
    of the walking sequence."""
    given = set(achieved)
    implied = {_TWIN[k] for k in given if k in _TWIN}
    reached = given | implied
    for position, step in enumerate(WALKING_SEQUENCE):
        if reached & set(step):
            for earlier in WALKING_SEQUENCE[:position]:
                implied |= set(earlier)
    return implied - given
