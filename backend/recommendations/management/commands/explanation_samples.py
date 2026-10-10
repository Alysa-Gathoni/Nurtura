"""Print sample explanations for held-out children, e.g. for the reader test (#71).

Usage (from backend/):
    python manage.py explanation_samples [--children H02 H03 ...] [--markdown]

For each child, the top recommendation at the configured alpha and its
explanation, exactly as POST would store it. The children are created in a
transaction that is rolled back, and no recommendations are stored.

The child is described only by what a caregiver enters in the app (age,
recorded milestones, support requests, interests), never by the held-out
profile text, which states when most children reach a milestone and would
give the explanation away in a reader test.

No held-out child has two milestone groups or a WHO milestone, so two
constructed profiles (C1, C2) cover those wordings. They are built from real
catalogue milestones the same way, and are labelled as constructed wherever
they're reported.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from profiles.models import ReferenceMilestone
from recommendations import heldout
from recommendations.explanations import EXPLANATION_VERSION, SUPPORT, explain, quote
from recommendations.ranking import rank

CONSTRUCTED = {
    # Two milestone groups: one not yet (due by 12 months) and one coming next
    # (due by 18 months), both Language.
    "C1": heldout.HeldOutChild(
        "C1",
        "constructed",
        "Language",
        16,
        "Constructed: 16 months; waving bye-bye not yet, saying three or more "
        "words not yet (coming next).",
        not_yet=("CDC-12M-LA-01", "CDC-18M-LA-01"),
    ),
    # A WHO milestone ("almost all children ... by about N months").
    "C2": heldout.HeldOutChild(
        "C2",
        "constructed",
        "Motor",
        13,
        "Constructed: 13 months; standing with assistance not yet (WHO).",
        not_yet=("WHO-MO-02",),
    ),
}
PROFILES = {**heldout.HELDOUT_BY_ID, **CONSTRUCTED}

# Covers: prenatal (H02), CDC milestones (H03, H04, H14, H15), interests
# (H07, H17; H17 also slightly younger), no requests (H10), two groups (C1)
# and WHO wording (C2).
DEFAULT_CHILDREN = [
    "H02",
    "H03",
    "H04",
    "H07",
    "H10",
    "H14",
    "H15",
    "H17",
    "C1",
    "C2",
]


def _age(months):
    whole = int(abs(months))
    text = f"{whole}½" if abs(months) % 1 >= 0.5 else str(whole)
    if months < 0:
        return f"You're expecting: your baby is due in about {text} months."
    return f"Your child is {text} months old."


def scenario(definition):
    """What the caregiver entered in the app, and nothing more."""
    lines = [_age(definition.age_months)]
    recorded = [(k, "Not yet") for k in definition.not_yet] + [
        (k, "Achieved") for k in definition.achieved
    ]
    if recorded:
        items = [
            f"{quote(ReferenceMilestone.objects.get(milestone_key=key).description)}"
            f": {status}"
            for key, status in recorded
        ]
        lines.append("Milestones you recorded: " + "; ".join(items) + ".")
    if definition.concerns:
        areas = ", ".join(SUPPORT[c] for c in definition.concerns)
        lines.append(f"You asked for support with: {areas}.")
    if definition.interests:
        lines.append(f"Your child enjoys: {', '.join(definition.interests)}.")
    return " ".join(lines)


class Command(BaseCommand):
    help = "Print the top recommendation and its explanation for held-out children."

    def add_arguments(self, parser):
        parser.add_argument("--children", nargs="+", default=DEFAULT_CHILDREN)
        parser.add_argument("--markdown", action="store_true")

    def handle(self, *args, **options):
        unknown = [c for c in options["children"] if c not in PROFILES]
        if unknown:
            raise CommandError(f"Unknown child(ren): {', '.join(unknown)}")
        with transaction.atomic():
            user = get_user_model().objects.create_user(
                username="explanation-samples@nurtura.invalid"
            )
            rows = []
            for child_id in options["children"]:
                definition = PROFILES[child_id]
                child = heldout.create_child(definition, user)
                result = rank(child, limit=1)
                if not result.ranked:
                    raise CommandError(f"{child_id} has no eligible activity.")
                top = result.ranked[0]
                rows.append(
                    (
                        definition,
                        scenario(definition),
                        top.activity,
                        explain(child, result.evaluation, top),
                    )
                )
            transaction.set_rollback(True)

        for n, (definition, situation, activity, explanation) in enumerate(rows, 1):
            if options["markdown"]:
                # Blank line after each block, so each renders as its own paragraph.
                self.stdout.write(f"### {n}\n\n")
                self.stdout.write(f"**Your child:** {situation}\n\n")
                self.stdout.write(
                    f"**Suggested activity:** {activity.activity_name}\n\n"
                )
                self.stdout.write(f"> {explanation.text}\n\n")
            else:
                self.stdout.write(
                    f"{n}. {definition.child_id} | {activity.activity_id} "
                    f"{activity.activity_name}\n   {situation}\n   {explanation.text}"
                )
        self.stdout.write(f"\n(explanation version {EXPLANATION_VERSION})")
