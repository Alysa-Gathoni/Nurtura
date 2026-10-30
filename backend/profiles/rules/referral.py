"""A gentle clinic-visit suggestion when due milestones are "Not yet" (#161).

CDC "Learn the Signs. Act Early." (every milestone checklist page, 2022):
"If your child is not meeting one or more milestones, has lost skills he or
she once had, or you have other concerns, act early. Talk with your child's
doctor." The threshold therefore follows CDC: one due guideline milestone
marked Not yet is enough.

This is not a rule: it is kept out of GUIDELINE_RULES, so it never changes
priorities, retrieval, ranking or the evaluation. It only adds a message.
"""

from dataclasses import dataclass

from django.utils import timezone

from ..models import DevelopmentalMilestone
from .facts import milestone_facts
from .guidelines import _is_due

# CDC: "one or more milestones".
REFERRAL_MIN_NOT_YET = 1

SOURCE = "CDC Learn the Signs. Act Early. (2022)"


@dataclass(frozen=True)
class Referral:
    message: str
    milestones: tuple  # due milestones marked Not yet, earliest expected first

    def to_dict(self):
        return {
            "message": self.message,
            "source": SOURCE,
            "milestones": [
                {
                    "description": f.description,
                    "domain": f.domain,
                    "expected_age_months": f.expected_age_months,
                    "source": f.source,
                }
                for f in self.milestones
            ],
        }


def message_for(name, count):
    things = "something" if count == 1 else "a few things"
    return (
        f"You've marked {things} as “Not yet” that most children "
        f"do by {name}'s age. Every child grows at their own pace, and this "
        "doesn't mean something is wrong. It's worth mentioning at your next "
        "clinic visit, so a health worker can look at it with you."
    )


def referral_for(child, on_date=None):
    """The child's Referral, or None when no due milestone is Not yet.

    Uses the latest observation of each guideline milestone, as the rule
    engine does. Only milestones linked to the CDC/WHO catalogue have an
    expected age, so free-text ones never count; WHO crawling is not a delay
    signal and does not count either.
    """
    on_date = on_date or timezone.localdate()
    due = sorted(
        (
            f
            for f in milestone_facts(child, on_date)
            if _is_due(f) and f.status == DevelopmentalMilestone.Status.NOT_YET
        ),
        key=lambda f: (f.expected_age_months, f.description),
    )
    if len(due) < REFERRAL_MIN_NOT_YET:
        return None
    return Referral(message=message_for(child.name, len(due)), milestones=tuple(due))
