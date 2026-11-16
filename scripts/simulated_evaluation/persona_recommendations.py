"""The system's real top 5 for each simulated caregiver persona (#222).

Usage (from the repository root):
    backend/venv/Scripts/python.exe scripts/simulated_evaluation/persona_recommendations.py

Creates each persona's child (docs/simulated_evaluation/personas_SIMULATED.json)
with its B2 milestone, generates recommendations with the app's own
generate(), and records the top 5, each "Why this?" text and any clinic-visit
message. Everything is created inside a transaction that is rolled back, so
the database is unchanged. The personas are fictional; the recommendations
and explanations are the system's real output for them.
"""

import datetime
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nurtura_backend.settings")
os.environ["EMAIL_HOST"] = ""

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from profiles.models import ChildProfile, ReferenceMilestone  # noqa: E402
from profiles.rules.referral import referral_for  # noqa: E402
from recommendations.generation import generate  # noqa: E402
from recommendations.heldout import AVERAGE_DAYS_PER_MONTH  # noqa: E402
from recommendations.models import Recommendation  # noqa: E402

PERSONAS = ROOT / "docs" / "simulated_evaluation" / "personas_SIMULATED.json"
OUT = ROOT / "docs" / "simulated_evaluation" / "persona_recommendations_SIMULATED.json"


class Rollback(Exception):
    pass


def main():
    personas = json.loads(PERSONAS.read_text(encoding="utf-8"))["caregivers"]
    today = timezone.localdate()
    results = []
    try:
        with transaction.atomic():
            caregiver = get_user_model().objects.create_user(
                username="simulated-personas@nurtura.invalid"
            )
            for p in personas:
                c = p["child"]
                days = round(c["age_months"] * AVERAGE_DAYS_PER_MONTH)
                profile = ChildProfile.objects.create(
                    caregiver=caregiver,
                    name=c["nickname"],
                    date_of_birth=today - datetime.timedelta(days=days + 1),
                    concerns=c["concerns"],
                    interests=c["interests"],
                )
                if p["b2"]:
                    profile.record_milestone(
                        reference=ReferenceMilestone.objects.get(
                            milestone_key=p["b2"]["milestone"]
                        ),
                        status=p["b2"]["status"],
                        observation_date=today,
                    )
                generate(profile.pk, caregiver)
                # A new child has exactly one batch.
                recs = Recommendation.objects.filter(child=profile).order_by(
                    "position"
                )[:5]
                referral = referral_for(profile)
                results.append(
                    {
                        "participant": p["id"],
                        "child_age_months": c["age_months"],
                        "b2": p["b2"],
                        "top5": [
                            {
                                "position": r.position,
                                "activity_id": r.activity.activity_id,
                                "name": r.activity.activity_name,
                                "area": r.activity.developmental_domain,
                                "age_range": r.activity.age_range,
                                "materials": r.activity.materials,
                                "why_this": r.explanation,
                            }
                            for r in recs
                        ],
                        "clinic_message": referral.to_dict() if referral else None,
                    }
                )
            raise Rollback
    except Rollback:
        pass
    OUT.write_text(
        json.dumps(
            {
                "notice": "SIMULATED personas; the recommendations and explanations are the system's real output for them.",
                "generated_on": today.isoformat(),
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    for r in results:
        print(r["participant"], [t["activity_id"] for t in r["top5"]])


if __name__ == "__main__":
    main()
