"""Latency of the recommendations endpoint (docs/performance_recommendations.md, #61).

Run from backend/ with the real model and the dev database:
    python scripts/measure_recommendation_latency.py
Windows-only as written (taskkill and CREATE_NEW_PROCESS_GROUP).

A. End to end over HTTP: `manage.py runserver` (autoreloader, warm-up on),
   token auth, 20 held-out children x 5 repeats of POST and of GET.
B. In process: Django test client inside a rolled-back transaction, same
   20 x 5, to separate handler time from HTTP and dev-server overhead.
C. Cold start: 3 server starts with warm-up off and 3 with it on; startup
   time and the first POST (a child with no batch yet).

Temporary caregivers, tokens and children are created in the dev database for
A and C and deleted at the end (cascading to their recommendations).
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import django
import numpy as np

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.environ["DJANGO_SETTINGS_MODULE"] = "nurtura_backend.settings"
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402
from django.urls import reverse  # noqa: E402
from rest_framework.authtoken.models import Token  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from recommendations import heldout  # noqa: E402

User = get_user_model()
REPEATS = 5
created_users = []


def stats(ms):
    a = np.array(ms)
    return {
        "n": len(ms),
        "p50_ms": round(float(np.percentile(a, 50)), 1),
        "p95_ms": round(float(np.percentile(a, 95)), 1),
        "min_ms": round(float(a.min()), 1),
        "max_ms": round(float(a.max()), 1),
    }


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(warmup):
    port = free_port()
    env = dict(os.environ, NURTURA_MODEL_WARMUP="1" if warmup else "0")
    started = time.perf_counter()
    proc = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"127.0.0.1:{port}"],
        cwd=BACKEND,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    while True:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.05)
            if time.perf_counter() - started > 180:
                raise RuntimeError("server did not start")
    return proc, port, time.perf_counter() - started


def stop_server(proc):
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    proc.wait(timeout=30)


def http(port, token, child_pk, method):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/children/{child_pk}/recommendations/",
        method=method,
        headers={"Authorization": f"Token {token}"},
    )
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as r:
        r.read()
        status = r.status
    return (time.perf_counter() - t) * 1000, status


def temp_caregiver(name):
    user = User.objects.create_user(username=f"{name}@nurtura.invalid")
    created_users.append(user)
    return user, Token.objects.create(user=user).key


results = {}
try:
    # A. HTTP, warm server.
    user, token = temp_caregiver("perf-http")
    children = [heldout.create_child(c, user) for c in heldout.HELDOUT_CHILDREN]
    proc, port, _ = start_server(warmup=True)
    try:
        post_first, post_repeat, get_ms, codes = [], [], [], {}
        for rep in range(REPEATS):
            for child in children:
                ms, status = http(port, token, child.pk, "POST")
                (post_first if rep == 0 else post_repeat).append(ms)
                codes[status] = codes.get(status, 0) + 1
                ms, _ = http(port, token, child.pk, "GET")
                get_ms.append(ms)
    finally:
        stop_server(proc)
    results["A_http"] = {
        "post_new_batch": stats(post_first),
        "post_repeat": stats(post_repeat),
        "post_all": stats(post_first + post_repeat),
        "get": stats(get_ms),
        "post_status_counts": codes,
    }

    # B. In process, rolled back.
    setup_test_environment()
    with transaction.atomic():
        u = User.objects.create_user(username="perf-inproc@nurtura.invalid")
        kids = [heldout.create_child(c, u) for c in heldout.HELDOUT_CHILDREN]
        client = APIClient()
        client.force_authenticate(u)
        client.post(reverse("child-recommendations", args=[kids[0].pk]))  # load model
        first, repeat, gets = [], [], []
        for rep in range(REPEATS):
            for k in kids:
                url = reverse("child-recommendations", args=[k.pk])
                t = time.perf_counter()
                client.post(url)
                (first if rep == 0 else repeat).append((time.perf_counter() - t) * 1000)
                t = time.perf_counter()
                client.get(url)
                gets.append((time.perf_counter() - t) * 1000)
        transaction.set_rollback(True)
    results["B_in_process"] = {
        "post_new_batch": stats(first),
        "post_repeat": stats(repeat),
        "post_all": stats(first + repeat),
        "get": stats(gets),
    }

    # C. Cold start.
    cold = {}
    for warmup in (False, True):
        runs = []
        for i in range(3):
            user, token = temp_caregiver(f"perf-cold-{int(warmup)}-{i}")
            child = heldout.create_child(heldout.HELDOUT_BY_ID["H08"], user)
            proc, port, startup = start_server(warmup)
            try:
                ms, status = http(port, token, child.pk, "POST")
            finally:
                stop_server(proc)
            runs.append(
                {
                    "startup_s": round(startup, 2),
                    "first_post_s": round(ms / 1000, 2),
                    "status": status,
                }
            )
        cold["warmup_on" if warmup else "warmup_off"] = runs
    results["C_cold"] = cold
finally:
    for user in created_users:
        user.delete()
    results["temporary_users_removed"] = not User.objects.filter(
        pk__in=[u.pk for u in created_users]
    ).exists()

print(json.dumps(results, indent=1))
