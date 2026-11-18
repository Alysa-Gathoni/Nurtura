"""Delete the end-to-end test account before a run (#230).

Usage (backend venv): python reset_test_account.py EMAIL

The test registers EMAIL, and the prebuilt test app has it built in, so the
account from the previous device must go first. Only the scratch database
(nurtura_loadtest) is touched; anything else is refused.
"""

import os
import sys

os.environ["DB_NAME"] = "nurtura_loadtest"
os.environ["EMAIL_HOST"] = ""
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend")
)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nurtura_backend.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

if settings.DATABASES["default"]["NAME"] != "nurtura_loadtest":
    sys.exit("Refusing: not the scratch database.")
email = sys.argv[1]
if not email.endswith("@nurtura.invalid"):
    sys.exit("Refusing: only @nurtura.invalid test accounts are deleted.")
deleted, _ = get_user_model().objects.filter(email__iexact=email).delete()
print(f"deleted {deleted} rows for {email}")
