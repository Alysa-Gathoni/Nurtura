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
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from profiles.models import ReferenceMilestone
from recommendations import heldout
from recommendations.explanations import EXPLANATION_VERSION, SUPPORT, explain
from recommendations.ranking import rank

DEFAULT_CHILDREN = [
    "H02",
    "H03",
    "H04",
    "H05",
    "H07",
    "H10",
    "H14",
    "H15",
    "H17",
    "H20",
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
            f"“{ReferenceMilestone.objects.get(milestone_key=key).description}"
            f"”: {status}"
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
        unknown = [c for c in options["children"] if c not in heldout.HELDOUT_BY_ID]
        if unknown:
            raise CommandError(f"Unknown held-out child(ren): {', '.join(unknown)}")
        with transaction.atomic():
            user = get_user_model().objects.create_user(
                username="explanation-samples@nurtura.invalid"
            )
            rows = []
            for child_id in options["children"]:
                definition = heldout.HELDOUT_BY_ID[child_id]
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
