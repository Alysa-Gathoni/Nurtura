"""1b machine, versions and imports; phone model and Android version."""

import json
import os
import platform
import shutil
from importlib import metadata

from _common import (
    ROOT,
    django_setup,
    grep,
    run,
    table,
    write_json,
    write_md,
)

COMMAND = "backend\\venv\\Scripts\\python.exe scripts\\report_evidence\\environment.py"

# distribution name -> import name searched for in the backend code
LIBRARIES = [
    ("Django", "django"),
    ("djangorestframework", "rest_framework"),
    ("psycopg2-binary", "psycopg2"),
    ("psycopg", "psycopg"),
    ("torch", "torch"),
    ("sentence-transformers", "sentence_transformers"),
    ("numpy", "numpy"),
    ("scikit-learn", "sklearn"),
    ("pandas", "pandas"),
    ("scipy", "scipy"),
]


def powershell(command):
    return run(["powershell", "-NoProfile", "-Command", command]).strip()


def version(dist):
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return "not installed"


def imports(module):
    hits = grep(rf"^\s*(import {module}\b|from {module}(\.|\s))", ["backend"])
    hits = [
        h
        for h in hits
        if h[0].endswith(".py")
        and "/venv/" not in h[0]
        and "backend/models/" not in h[0]
    ]
    app_hits = [h for h in hits if "/test" not in h[0]]
    return hits, app_hits


def main():
    machine = {
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "cpu": powershell(
            "(Get-CimInstance Win32_Processor | Select-Object -First 1).Name"
        )
        or platform.processor(),
        "cores_logical": os.cpu_count(),
        "ram_gb": round(
            int(
                powershell("(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory")
                or 0
            )
            / 1024**3,
            1,
        ),
        "disk_c_total_gb": round(shutil.disk_usage("C:\\").total / 1024**3, 1),
        "disk_c_free_gb": round(shutil.disk_usage("C:\\").free / 1024**3, 1),
        "python": platform.python_version(),
    }

    django_setup()
    from django.db import connection

    with connection.cursor() as c:
        c.execute("SELECT version()")
        machine["postgresql"] = c.fetchone()[0]
    from django.conf import settings

    engine = settings.DATABASES["default"]["ENGINE"]

    libs = []
    for dist, module in LIBRARIES:
        hits, app_hits = imports(module)
        where = ", ".join(f"{f}:{n}" for f, n, _ in app_hits[:3])
        note = ""
        if module == "torch" and not hits:
            note = "not imported directly; loaded by sentence-transformers"
        if module == "psycopg2":
            note = (
                f"used through Django's database ENGINE `{engine}` (no direct import)"
                if not hits
                else ""
            )
        libs.append(
            {
                "library": dist,
                "version": version(dist),
                "imported_by_app_code": (
                    "yes" if app_hits else ("tests only" if hits else "no")
                ),
                "example_files": where or note or "—",
            }
        )

    flutter = run(["flutter.bat", "--version", "--machine"])
    try:
        fv = json.loads(flutter[flutter.index("{") :])
        machine["flutter"] = fv.get("frameworkVersion")
        machine["dart"] = fv.get("dartSdkVersion")
    except ValueError:
        machine["flutter"] = machine["dart"] = "UNKNOWN"

    adb = os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe")
    phone = {"model": "UNKNOWN", "android": "UNKNOWN", "sdk": "UNKNOWN"}
    if os.path.exists(adb) and "device" in run([adb, "devices"]).split("\n", 1)[-1]:
        phone = {
            "model": run([adb, "shell", "getprop", "ro.product.model"]).strip()
            or "UNKNOWN",
            "android": run(
                [adb, "shell", "getprop", "ro.build.version.release"]
            ).strip()
            or "UNKNOWN",
            "sdk": run([adb, "shell", "getprop", "ro.build.version.sdk"]).strip()
            or "UNKNOWN",
        }

    write_json(
        "environment.json", {"machine": machine, "libraries": libs, "phone": phone}
    )
    body = f"""## 1b. Machine

{table(['Item', 'Value', 'How'], [
    ['OS', machine['os'], '`platform`'],
    ['CPU', machine['cpu'], '`Get-CimInstance Win32_Processor`'],
    ['Logical cores', machine['cores_logical'], '`os.cpu_count()`'],
    ['RAM', f"{machine['ram_gb']} GB", '`Get-CimInstance Win32_ComputerSystem`'],
    ['Disk C:', f"{machine['disk_c_total_gb']} GB total, {machine['disk_c_free_gb']} GB free", '`shutil.disk_usage`'],
    ['Python', machine['python'], 'backend venv'],
    ['PostgreSQL', machine['postgresql'], '`SELECT version()`'],
    ['Flutter', machine['flutter'], '`flutter --version --machine`'],
    ['Dart', machine['dart'], '`flutter --version --machine`'],
    ['Phone', f"{phone['model']}, Android {phone['android']} (SDK {phone['sdk']})", '`adb shell getprop`'],
])}

## Libraries

Versions from the backend venv (`importlib.metadata`). "Imported by app code" searches `backend/` for `import <module>` / `from <module>` outside test files.

{table(['Library', 'Version', 'Imported by app code', 'Where (first files)'], [[l['library'], l['version'], l['imported_by_app_code'], l['example_files']] for l in libs])}

Raw: `raw/environment.json`.
"""
    write_md("02_environment.md", body, "Environment and versions", COMMAND)
    print("ok")


if __name__ == "__main__":
    main()
