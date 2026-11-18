"""Type the emailed sign-in code into an emulator (#230).

Usage: python type_code.py SERVER_LOG SERIAL [TIMEOUT_SECONDS] [REQUEST_LOG]

The end-to-end test waits for a person to type the code that registration
emails. With EMAIL_HOST empty the backend prints each email to its console
("Subject: Your Nurtura code: 123456"), here redirected to SERVER_LOG. This
watches the part of the log written after it starts, and when a code
appears, types it on the emulator with `adb shell input text`; the code
screen submits on its own at six digits.

Typing can land before the code screen has focus, and then nothing happens.
So with REQUEST_LOG (runserver's request log, its stderr), it checks for a
successful "POST /api/auth/login/verify/ ... 200" after each try, and
otherwise clears the field and types again, up to ATTEMPTS times. Exits 0
once typed (and, with REQUEST_LOG, verified), 1 otherwise.
"""

import os
import re
import subprocess
import sys
import time
from pathlib import Path

CODE = re.compile(r"Your Nurtura code: (\d{6})")
VERIFIED = re.compile(r'"POST /api/auth/login/verify/ HTTP/1\.1" 200')
ADB = (
    Path(os.environ["LOCALAPPDATA"]) / "Android" / "Sdk" / "platform-tools" / "adb.exe"
)
ATTEMPTS = 4


def read_from(path, start):
    if not path.exists():
        return ""
    with open(path, "rb") as f:
        f.seek(start)
        return f.read().decode("utf-8", errors="replace")


def size(path):
    return path.stat().st_size if path and path.exists() else 0


def adb(serial, *args):
    subprocess.run([str(ADB), "-s", serial, "shell", *args], check=True)


def main():
    log, serial = Path(sys.argv[1]), sys.argv[2]
    timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 600
    requests = Path(sys.argv[4]) if len(sys.argv) > 4 else None
    start = size(log)
    end = time.time() + timeout
    code = None
    while time.time() < end and code is None:
        time.sleep(1)
        match = CODE.search(read_from(log, start))
        code = match.group(1) if match else None
    if code is None:
        sys.exit(f"no code seen in {timeout:.0f} s")

    for attempt in range(1, ATTEMPTS + 1):
        before = size(requests)
        time.sleep(3)  # let the code screen take focus
        adb(serial, "input", "keyevent", *["67"] * 8)  # clear any partial code
        adb(serial, "input", "text", code)
        print(f"typed the code on {serial} (attempt {attempt})")
        if requests is None:
            return
        for _ in range(10):
            time.sleep(1)
            if VERIFIED.search(read_from(requests, before)):
                print("verified")
                return
    sys.exit("typed, but no successful verification")


if __name__ == "__main__":
    main()
