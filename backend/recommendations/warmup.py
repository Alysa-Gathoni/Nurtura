"""Load the SBERT model when the web server starts (#58).

Without this, the first recommendation request after a start pays for
importing PyTorch and loading the model (13-16 s on the development machine,
#57). warm_up() is called from wsgi.py and asgi.py only, which are imported
by the serving process and by nothing else:

- runserver imports the WSGI application in the process that serves
  requests, before it binds the port. Under the autoreloader that is the
  child process only (the parent just watches files), so the model loads
  once per serving process, including after each reload.
- migrate, test, check and other management commands never import wsgi.py
  or asgi.py, so they never load the model.

NURTURA_MODEL_WARMUP switches it: 1/true/yes/on enables it and 0/false/no/off
disables it. When the variable isn't set, it is **off in development**
(DEBUG=True), so code reloads stay quick, and **on otherwise**. A missing
model never stops the server: warm-up is skipped with a message, and the
first request reports the usual error.
"""

import os
import sys
import time

from django.conf import settings

from . import embeddings

ENV_FLAG = "NURTURA_MODEL_WARMUP"
DISABLED_VALUES = {"0", "false", "no", "off"}


def enabled():
    """The env flag if set; otherwise off in development (DEBUG), on elsewhere."""
    value = os.getenv(ENV_FLAG)
    if value is None or not value.strip():
        return not settings.DEBUG
    return value.strip().lower() not in DISABLED_VALUES


def _say(message):
    sys.stderr.write(f"[warm-up] {message}\n")
    sys.stderr.flush()


def warm_up():
    """Load the encoder and run one encode, so the first request is warm.

    Returns the seconds it took, or None if skipped.
    """
    if not enabled():
        _say(f"skipped ({ENV_FLAG} is off, or unset in development)")
        return None
    if not settings.SBERT_MODEL_PATH.exists():
        _say(f"skipped (no model at {settings.SBERT_MODEL_PATH})")
        return None
    started = time.perf_counter()
    encoder = embeddings.get_encoder()
    encoder.encode(["warm-up"])  # first encode initialises the model's kernels
    elapsed = time.perf_counter() - started
    _say(f"loaded {encoder.name} in {elapsed:.1f} s (pid {os.getpid()})")
    return elapsed
