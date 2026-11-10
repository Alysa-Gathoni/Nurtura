"""The weekly "Nurtura observation" (#192).

A few plain sentences about the child's last WEEK_DAYS days, built from the
caregiver's own records:

- activities tried (marked done or partly done) and how many went well;
- the area whose ideas have gone best, if feedback shows one;
- milestones noted this week, as achieved or starting;
- what to focus on next: a milestone that is not yet secure, from the
  highest-priority area that has one (Not yet before Emerging, never one
  already mentioned).

Like the Progress tab (non-comparative, a SOFIA addition) it never compares the child with other
children, and like the referral (#161) it never diagnoses. It is generated
from templates, so every sentence can be traced to a record.
"""

import datetime

from django.utils import timezone

from activities.choices import Domain

from .models import DevelopmentalMilestone
from .rules import build_profile

WEEK_DAYS = 7
Status = DevelopmentalMilestone.Status

AREA_WORDS = {
    Domain.COGNITIVE: "thinking",
    Domain.LANGUAGE: "talking",
    Domain.MOTOR: "moving",
    Domain.SENSORY: "senses",
    Domain.SOCIO_EMOTIONAL: "feelings",
}
FOCUS_RULES = ("due-milestone-not-yet", "due-milestone-emerging")


def _quote_list(items, limit=2):
    shown = [f"“{i}”" for i in items[:limit]]
    more = len(items) - limit
    text = " and ".join(shown)
    return text + (f" and {more} more" if more > 0 else "")


def _focus(evaluation, mentioned):
    """A not-yet-secure milestone to work on next: from the highest-priority
    area that has one, Not yet before Emerging, never one already mentioned."""
    candidates = [
        f
        for f in evaluation.firings
        if f.rule.name in FOCUS_RULES and f.fact.description not in mentioned
    ]
    for domain in evaluation.ranked_domains():
        in_area = [f for f in candidates if f.fact.domain == domain]
        if in_area:
            in_area.sort(key=lambda f: FOCUS_RULES.index(f.rule.name))
            return in_area[0].fact
    return None


def observation(child, on_date=None):
    """{"sentences": [...], "text": str, "focus_domain": str or None}."""
    from feedback.models import CompletedActivity, Feedback  # feedback imports us

    on_date = on_date or timezone.localdate()
    since = on_date - datetime.timedelta(days=WEEK_DAYS - 1)
    name = child.name
    sentences = []

    if child.date_of_birth > on_date:
        tried = CompletedActivity.objects.filter(
            recommendation__child=child, completion_date__gte=since
        ).count()
        sentences.append(
            f"You tried {tried} pregnancy {'idea' if tried == 1 else 'ideas'} "
            "this week."
            if tried
            else "Try one of today's pregnancy ideas this week; talking and "
            "singing to your bump is a lovely start."
        )
        return {
            "sentences": sentences,
            "text": " ".join(sentences),
            "focus_domain": None,
        }

    tried = CompletedActivity.objects.filter(
        recommendation__child=child, completion_date__gte=since
    ).count()
    feedback = list(
        Feedback.objects.filter(
            recommendation__child=child, date_submitted__date__gte=since
        ).select_related("recommendation__activity")
    )
    good = [
        f
        for f in feedback
        if f.outcome == Feedback.Outcome.WENT_WELL
        or f.interest in (Feedback.Interest.HAPPY, Feedback.Interest.LOVED_IT)
    ]
    if tried:
        line = f"This week {name} tried {tried} {'activity' if tried == 1 else 'activities'}"
        line += f", and {len(good)} went well." if good else "."
        sentences.append(line)
    else:
        sentences.append(
            f"No activities were marked done this week. One of today's ideas "
            f"is a good place to start with {name}."
        )

    if len(good) >= 2:
        counts = {}
        for f in good:
            domain = f.recommendation.activity.developmental_domain
            counts[domain] = counts.get(domain, 0) + 1
        best, n = max(counts.items(), key=lambda x: (x[1], x[0]))
        if n >= 2:
            sentences.append(
                f"{AREA_WORDS[best].capitalize()} ideas seem to suit {name} best "
                "right now."
            )

    noted = {}
    for m in child.milestones.filter(
        observation_date__gte=since, observation_date__lte=on_date
    ).order_by("observation_date", "created_at"):
        noted[m.reference_id or m.description] = m
    achieved = [m.description for m in noted.values() if m.status == Status.ACHIEVED]
    starting = [m.description for m in noted.values() if m.status == Status.EMERGING]
    if achieved:
        sentences.append(f"You noted {_quote_list(achieved)}: lovely progress.")
    if starting:
        verb = "is" if len(starting) == 1 else "are"
        sentences.append(f"{_quote_list(starting)} {verb} starting to show.")

    focus = _focus(build_profile(child, on_date=on_date), mentioned=set(starting))
    if focus is not None:
        sentences.append(
            f"Next, ideas for {AREA_WORDS[focus.domain]} could help with "
            f"“{focus.description}”."
        )
    elif not child.milestones.exists():
        sentences.append(
            f"Record a few milestones and Nurtura can tailor ideas for {name}."
        )

    return {
        "sentences": sentences,
        "text": " ".join(sentences),
        "focus_domain": focus.domain if focus is not None else None,
    }
