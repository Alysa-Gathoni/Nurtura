"""Tests for loading the model at server start (#58)."""

import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from . import embeddings, warmup
from .test_embeddings import FakeEncoder

BACKEND = Path(settings.BASE_DIR)
MISSING_MODEL = str(BACKEND / "no-such-model-dir")


def _env(**overrides):
    env = dict(os.environ)
    env.update(overrides)
    return env


class WarmUpTests(SimpleTestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.model_dir = Path(tmp.name)
        self.addCleanup(embeddings.set_encoder, None)
        quiet = mock.patch.object(warmup, "_say")
        quiet.start()
        self.addCleanup(quiet.stop)

    def test_loads_the_encoder_once_and_encodes(self):
        encoder = FakeEncoder()
        with override_settings(SBERT_MODEL_PATH=self.model_dir), mock.patch.object(
            embeddings, "get_encoder", return_value=encoder
        ) as get_encoder, mock.patch.dict(os.environ, {warmup.ENV_FLAG: "1"}):
            self.assertIsNotNone(warmup.warm_up())
        get_encoder.assert_called_once_with()
        self.assertEqual(encoder.calls, [["warm-up"]])

    def test_env_flag_disables_it(self):
        for value in ("0", "false", "No", " off "):
            with self.subTest(value=value), mock.patch.dict(
                os.environ, {warmup.ENV_FLAG: value}
            ), mock.patch.object(embeddings, "get_encoder") as get_encoder:
                self.assertIsNone(warmup.warm_up())
                get_encoder.assert_not_called()

    def test_missing_model_is_skipped_not_fatal(self):
        with override_settings(SBERT_MODEL_PATH=Path(MISSING_MODEL)), mock.patch.object(
            embeddings, "get_encoder"
        ) as get_encoder:
            self.assertIsNone(warmup.warm_up())
            get_encoder.assert_not_called()

    def test_the_test_runner_never_imports_the_server_entry_points(self):
        self.assertNotIn("nurtura_backend.wsgi", sys.modules)
        self.assertNotIn("nurtura_backend.asgi", sys.modules)


class EntryPointTests(SimpleTestCase):
    """Run real processes; the model path is missing so nothing heavy loads."""

    env = _env(NURTURA_MODEL_WARMUP="1", SBERT_MODEL_PATH=MISSING_MODEL)

    def run_python(self, *args):
        return subprocess.run(
            [sys.executable, *args],
            cwd=BACKEND,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_management_commands_do_not_warm_up(self):
        for command in (["check"], ["showmigrations", "--help"], ["help"]):
            with self.subTest(command=command):
                result = self.run_python("manage.py", *command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("[warm-up]", result.stdout + result.stderr)

    def test_wsgi_and_asgi_warm_up_on_import(self):
        for module in ("nurtura_backend.wsgi", "nurtura_backend.asgi"):
            with self.subTest(module=module):
                result = self.run_python("-c", f"import {module}")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr.count("[warm-up]"), 1, result.stderr)
                self.assertIn("skipped (no model at", result.stderr)

    def test_runserver_warms_up_once_with_and_without_the_reloader(self):
        for extra in ([], ["--noreload"]):
            with self.subTest(reloader=not extra):
                output = self.runserver(extra)
                self.assertEqual(output.count("[warm-up]"), 1, output)
                self.assertIn("Quit the server", output)

    def runserver(self, extra):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(
            [
                sys.executable,
                "manage.py",
                "runserver",
                f"127.0.0.1:{port}",
                "--skip-checks",
                *extra,
            ],
            cwd=BACKEND,
            env=_env(**self.env, PYTHONUNBUFFERED="1"),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        lines = []
        try:
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                line = proc.stdout.readline()
                if not line:
                    break
                lines.append(line)
                if "Quit the server" in line:
                    time.sleep(1)  # let a second (wrong) warm-up show up
                    break
        finally:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                    capture_output=True,
                )
            else:
                os.killpg(proc.pid, signal.SIGTERM)
            rest, _ = proc.communicate(timeout=30)
            lines.append(rest or "")
        return "".join(lines)
