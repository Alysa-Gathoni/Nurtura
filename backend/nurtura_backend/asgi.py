"""
ASGI config for nurtura_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nurtura_backend.settings")

application = get_asgi_application()

# Load the SBERT model now, in the serving process only (#58); see
# recommendations/warmup.py. NURTURA_MODEL_WARMUP=0 disables it.
from recommendations.warmup import warm_up  # noqa: E402

warm_up()
