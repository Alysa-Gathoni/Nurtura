"""Create the load test's caregivers in the scratch database (#224).

Usage (from the repository root, with the backend venv):
    set DB_NAME=nurtura_loadtest
    backend\\venv\\Scripts\\python.exe scripts\\load_test\\setup_users.py OUT.json [N]

Creates N (default 100) fictional caregivers, loadtest-NNN@nurtura.invalid,
each with a token, the current privacy notice agreed, one child (a spread
of ages, areas and interests) and one recorded milestone. Writes their
tokens and child IDs to OUT.json for the locustfile; keep that file outside
the repository. Refuses to run unless DB_NAME is the scratch database.
"""

import datetime
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = "nurtura_loadtest"
if os.environ.get("DB_NAME") != SCRATCH:
    sys.exit(f"Set DB_NAME={SCRATCH}: this script only writes to the scratch database.")

sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nurtura_backend.settings")
os.environ["EMAIL_HOST"] = ""

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.utils import timezone  # noqa: E402
from rest_framework.authtoken.models import Token  # noqa: E402

from profiles import privacy  # noqa: E402
from profiles.models import ChildProfile, ReferenceMilestone  # noqa: E402

# (age in months, concerns, interests, milestone key, status)
CHILDREN = [
    (-3, ["Socio-Emotional"], [], None, None),
    (3, [], ["songs"], "CDC-02M-SE-04", "achieved"),
    (5, [], ["music"], "CDC-04M-MO-05", "not_yet"),
    (8, [], ["water"], "CDC-06M-MO-01", "achieved"),
    (10, ["Language"], ["peekaboo"], "CDC-09M-LA-01", "not_yet"),
    (14, ["Motor"], ["balls"], "CDC-12M-MO-02", "achieved"),
    (18, ["Sensory"], ["textures"], "CDC-15M-MO-01", "achieved"),
    (22, ["Language"], ["animals"], "CDC-18M-LA-01", "not_yet"),
    (27, [], ["books"], "CDC-24M-LA-02", "achieved"),
    (30, ["Cognitive"], ["drawing"], "CDC-30M-CO-04", "not_yet"),
]


def main():
    out = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    User = get_user_model()
    today = timezone.localdate()
    users = []
    for i in range(1, n + 1):
        email = f"loadtest-{i:03d}@nurtura.invalid"
        user, _ = User.objects.get_or_create(
            username=email, defaults={"email": email, "role": User.Role.CAREGIVER}
        )
        privacy.record_consent(user)
        token, _ = Token.objects.get_or_create(user=user)
        age, concerns, interests, key, status = CHILDREN[(i - 1) % len(CHILDREN)]
        child = ChildProfile.objects.create(
            caregiver=user,
            name=f"Child {i:03d}",
            date_of_birth=today - datetime.timedelta(days=round(age * 30.44) + 1),
            concerns=concerns,
            interests=interests,
        )
        if key:
            child.record_milestone(
                reference=ReferenceMilestone.objects.get(milestone_key=key),
                status=status,
                observation_date=today,
            )
        users.append({"token": token.key, "child": child.pk, "age_months": age})
    out.write_text(json.dumps(users), encoding="utf-8")
    print(f"{len(users)} caregivers ready in {SCRATCH}")


if __name__ == "__main__":
    main()
