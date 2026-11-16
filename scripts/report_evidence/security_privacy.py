"""Section 4: security, privacy and deployment.

4a negative tests through DRF's test client against the real URL
configuration and settings, with fictional users, inside one transaction
that is rolled back (each test in its own savepoint, throttle cache cleared
except where the test is about throttling). 4b-4e are read from code,
settings, git history and the file system.
"""

import json
import re
import subprocess

from _common import (
    APP,
    BACKEND,
    ROOT,
    django_setup,
    line_of,
    rolled_back,
    run,
    table,
    write_csv,
    write_json,
    write_md,
    write_text,
)

COMMAND = (
    "backend\\venv\\Scripts\\python.exe scripts\\report_evidence\\security_privacy.py"
)
PW = "Fictional-Passw0rd!"


def negative_tests():
    from django.contrib.auth import get_user_model
    from django.core.cache import cache
    from django.db import connection, transaction
    from rest_framework.test import APIClient

    from activities.models import DevelopmentalActivity
    from activities.tests import activity_fields
    from profiles import privacy
    from profiles.models import ChildProfile

    User = get_user_model()
    rows = []

    def record(test, request, expected, actual, ok):
        rows.append(
            {
                "test": test,
                "request": request,
                "expected": expected,
                "actual": actual,
                "result": "pass" if ok else "FAIL",
            }
        )

    def client(user=None):
        c = APIClient(HTTP_HOST="localhost")
        if user:
            c.force_authenticate(user)
        return c

    def isolated(fn):
        cache.clear()
        sid = transaction.savepoint()
        try:
            fn()
        finally:
            transaction.savepoint_rollback(sid)

    with rolled_back():
        a = User.objects.create_user(
            username="a@nurtura.invalid", email="a@nurtura.invalid", password=PW
        )
        b = User.objects.create_user(
            username="b@nurtura.invalid", email="b@nurtura.invalid", password=PW
        )
        admin = User.objects.create_user(
            username="admin@nurtura.invalid",
            email="admin@nurtura.invalid",
            password=PW,
            role=User.Role.ADMINISTRATOR,
        )
        for u in (a, b):
            privacy.record_consent(u)
            u.save()
        child = ChildProfile.objects.create(
            caregiver=a, name="Fictional Child", date_of_birth="2025-09-12"
        )
        draft = DevelopmentalActivity.objects.create(
            **activity_fields(
                activity_id="ACT-9999",
                activity_name="Fictional Draft Activity",
                content_status="draft",
            )
        )

        def weak():
            r = client().post(
                "/api/auth/register/",
                {
                    "username": "w@nurtura.invalid",
                    "email": "w@nurtura.invalid",
                    "password": "password",
                },
                format="json",
            )
            record(
                "Weak password",
                'POST /api/auth/register/ {"password": "password"}',
                400,
                r.status_code,
                r.status_code == 400,
            )

        def duplicate():
            r = client().post(
                "/api/auth/register/",
                {
                    "username": "a2@nurtura.invalid",
                    "email": "a@nurtura.invalid",
                    "password": PW,
                },
                format="json",
            )
            record(
                "Duplicate email",
                'POST /api/auth/register/ {"email": <existing>}',
                400,
                r.status_code,
                r.status_code == 400,
            )

        def wrong_logins():
            codes = [
                client()
                .post(
                    "/api/auth/login/",
                    {"username": "a@nurtura.invalid", "password": "wrong-password"},
                    format="json",
                )
                .status_code
                for _ in range(6)
            ]
            record(
                "Six wrong logins in a minute",
                'POST /api/auth/login/ x6 {"password": <wrong>}',
                "400 x5, then 429",
                " ".join(map(str, codes)),
                codes[-1] == 429 and all(c != 200 for c in codes),
            )

        def no_token():
            r = client().get("/api/children/")
            record(
                "No token",
                "GET /api/children/ (no Authorization)",
                401,
                r.status_code,
                r.status_code == 401,
            )
            c = APIClient(HTTP_HOST="localhost")
            c.credentials(
                HTTP_AUTHORIZATION="Token 0000000000000000000000000000000000000000"
            )
            r = c.get("/api/children/")
            record(
                "Bad token",
                "GET /api/children/ (Authorization: Token <invalid>)",
                401,
                r.status_code,
                r.status_code == 401,
            )

        def other_child():
            for method, body in (
                ("get", None),
                ("patch", {"name": "Changed"}),
                ("delete", None),
            ):
                r = getattr(client(b), method)(
                    f"/api/children/{child.pk}/", body, format="json"
                )
                record(
                    f"Another caregiver's child ({method.upper()})",
                    f"{method.upper()} /api/children/<other's id>/",
                    404,
                    r.status_code,
                    r.status_code == 404,
                )
            exists = ChildProfile.objects.filter(
                pk=child.pk, name="Fictional Child"
            ).exists()
            record(
                "Child unchanged after those attempts",
                "SELECT the child",
                "still there, name unchanged",
                "unchanged" if exists else "CHANGED",
                exists,
            )

        def admin_on_child_api():
            r = client(admin).get("/api/children/")
            record(
                "Administrator on the child API",
                "GET /api/children/ as administrator",
                403,
                r.status_code,
                r.status_code == 403,
            )

        def caregiver_on_admin_site():
            c = APIClient(HTTP_HOST="localhost")
            c.force_login(a)
            r = c.get("/admin/")
            record(
                "Caregiver on the admin site",
                "GET /admin/ logged in as a caregiver",
                "302 to the admin login (not 200)",
                f"{r.status_code} -> {r.get('Location', '')}",
                r.status_code == 302,
            )

        def role_in_body():
            r = client().post(
                "/api/auth/register/",
                {
                    "username": "r@nurtura.invalid",
                    "email": "r@nurtura.invalid",
                    "password": PW,
                    "role": "administrator",
                },
                format="json",
            )
            role = (
                User.objects.filter(username="r@nurtura.invalid")
                .values_list("role", flat=True)
                .first()
            )
            record(
                "Role in the registration body",
                'POST /api/auth/register/ {"role": "administrator"}',
                "201, role stays caregiver",
                f"{r.status_code}, role {role}",
                r.status_code == 201 and role == "caregiver",
            )

        def bad_json():
            r = client(a).generic(
                "POST", "/api/children/", "{not json", content_type="application/json"
            )
            record(
                "Invalid JSON",
                "POST /api/children/ body `{not json`",
                400,
                r.status_code,
                r.status_code == 400,
            )

        def big_json():
            from django.conf import settings

            size = settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 1024
            payload = json.dumps({"name": "x" * size, "date_of_birth": "2025-09-12"})
            try:
                r = client(a).generic(
                    "POST", "/api/children/", payload, content_type="application/json"
                )
                code = r.status_code
            except Exception as exc:  # noqa: BLE001
                code = f"error {type(exc).__name__}"
            record(
                "Oversized JSON",
                f"POST /api/children/ with a {size // 1024} KB body (limit {settings.DATA_UPLOAD_MAX_MEMORY_SIZE // 1024} KB)",
                "400 or 413, nothing saved",
                code,
                code in (400, 413)
                and not ChildProfile.objects.filter(name__startswith="xxxx").exists(),
            )

        def sql_text():
            text = "Robert'); DROP TABLE profiles_childprofile;--"
            r = client(a).post(
                "/api/children/",
                {"name": text, "date_of_birth": "2025-09-12"},
                format="json",
            )
            stored = ChildProfile.objects.filter(name=text).exists()
            with connection.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM profiles_childprofile")
                cur.fetchone()
            record(
                "SQL-like text in a field",
                f'POST /api/children/ {{"name": "{text}"}}',
                "201, stored as plain text, table intact",
                f"{r.status_code}, stored literally: {stored}",
                r.status_code == 201 and stored,
            )

        def unpublished():
            r = client(a).post(
                f"/api/children/{child.pk}/activities/{draft.activity_id}/try/",
                {},
                format="json",
            )
            record(
                "Unpublished activity",
                "POST /api/children/<id>/activities/<Draft id>/try/",
                404,
                r.status_code,
                r.status_code == 404,
            )
            r = client(a).put(
                f"/api/children/{child.pk}/saved/{draft.activity_id}/",
                {},
                format="json",
            )
            record(
                "Save an unpublished activity",
                "PUT /api/children/<id>/saved/<Draft id>/",
                404,
                r.status_code,
                r.status_code == 404,
            )

        def publish():
            r = client(a).post(
                f"/api/admin/activities/{draft.pk}/status/",
                {"status": "published"},
                format="json",
            )
            record(
                "Unauthorised publish (caregiver)",
                'POST /api/admin/activities/<id>/status/ {"status": "published"}',
                403,
                r.status_code,
                r.status_code == 403,
            )
            r = client(admin).post(
                f"/api/admin/activities/{draft.pk}/status/",
                {"status": "published"},
                format="json",
            )
            record(
                "Publish skipping review (administrator)",
                "Draft -> Published directly",
                400,
                r.status_code,
                r.status_code == 400,
            )
            still = DevelopmentalActivity.objects.get(pk=draft.pk).content_status
            record(
                "Draft still Draft",
                "SELECT content_status",
                "draft",
                still,
                still == "draft",
            )

        for fn in (
            weak,
            duplicate,
            wrong_logins,
            no_token,
            other_child,
            admin_on_child_api,
            caregiver_on_admin_site,
            role_in_body,
            bad_json,
            big_json,
            sql_text,
            unpublished,
            publish,
        ):
            isolated(fn)
    return rows


def implementation_summary():
    from django.conf import settings

    s = "backend/nurtura_backend/settings.py"

    def where(pattern, path=s):
        n = line_of(path, pattern)
        return f"{path}:{n}" if n else f"{path} (not set: Django default)"

    rf = settings.REST_FRAMEWORK
    return [
        [
            "Authentication",
            ", ".join(
                c.split(".")[-1] for c in rf.get("DEFAULT_AUTHENTICATION_CLASSES", [])
            ),
            where("DEFAULT_AUTHENTICATION_CLASSES"),
        ],
        [
            "Token lifecycle",
            f"expires after {settings.TOKEN_LIFETIME}; two-step email code at login",
            f"{where('^TOKEN_LIFETIME')}; backend/profiles/authentication.py:{line_of('backend/profiles/authentication.py', 'class ExpiringTokenAuthentication')}; backend/profiles/two_factor.py",
        ],
        [
            "Default permission",
            ", ".join(
                c.split(".")[-1] for c in rf.get("DEFAULT_PERMISSION_CLASSES", [])
            ),
            where("DEFAULT_PERMISSION_CLASSES"),
        ],
        [
            "Roles",
            "IsCaregiver, IsAdministrator, HasPrivacyConsent",
            f"backend/profiles/permissions.py:{line_of('backend/profiles/permissions.py', 'class IsCaregiver')}",
        ],
        [
            "Throttling",
            str(rf.get("DEFAULT_THROTTLE_RATES")),
            where("DEFAULT_THROTTLE_RATES"),
        ],
        [
            "Password validators",
            ", ".join(
                v["NAME"].split(".")[-1] for v in settings.AUTH_PASSWORD_VALIDATORS
            ),
            where("AUTH_PASSWORD_VALIDATORS"),
        ],
        [
            "Admin restriction",
            "is_staff follows the Administrator role; admin site needs an active staff user",
            f"backend/profiles/models.py:{line_of('backend/profiles/models.py', 'def save')}",
        ],
        [
            "Deletion rules",
            "account deletion confirms with password (or email for Google accounts); child data cascades",
            f"backend/profiles/views.py:{line_of('backend/profiles/views.py', 'def delete') or 'UNKNOWN'}; see 4d",
        ],
        [
            "DEBUG",
            f"default False unless DEBUG env is 1/true/yes (this run: {settings.DEBUG})",
            where("^DEBUG"),
        ],
        [
            "ALLOWED_HOSTS",
            f"from env, default localhost,127.0.0.1 (this run: {settings.ALLOWED_HOSTS})",
            where("^ALLOWED_HOSTS"),
        ],
        [
            "SESSION_COOKIE_SECURE",
            str(settings.SESSION_COOKIE_SECURE),
            where("SESSION_COOKIE_SECURE"),
        ],
        [
            "CSRF_COOKIE_SECURE",
            str(settings.CSRF_COOKIE_SECURE),
            where("CSRF_COOKIE_SECURE"),
        ],
        [
            "SECURE_SSL_REDIRECT",
            str(settings.SECURE_SSL_REDIRECT),
            where("SECURE_SSL_REDIRECT"),
        ],
        [
            "SECURE_HSTS_SECONDS",
            str(settings.SECURE_HSTS_SECONDS),
            where("SECURE_HSTS_SECONDS"),
        ],
        [
            "DATA_UPLOAD_MAX_MEMORY_SIZE",
            str(settings.DATA_UPLOAD_MAX_MEMORY_SIZE),
            where("DATA_UPLOAD_MAX_MEMORY_SIZE"),
        ],
    ]


SECRET_PATTERNS = {
    "private key block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "AWS access key": r"AKIA[0-9A-Z]{16}",
    "Google API key": r"AIza[0-9A-Za-z_\-]{35}",
    "GitHub token": r"gh[pousr]_[0-9A-Za-z]{36}",
    "Slack token": r"xox[baprs]-[0-9A-Za-z-]{10,}",
    "password/secret assignment with a literal": r"(?i)(password|secret|api_key|token)\s*[=:]\s*['\"][^'\"\s]{12,}['\"]",
    "Django SECRET_KEY literal": r"SECRET_KEY\s*=\s*['\"][^'\"]{20,}['\"]",
}


def secret_scan():
    """Counts and paths only, over every commit's added lines."""
    log = subprocess.run(
        ["git", "log", "--all", "-p", "--no-color", "--unified=0"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout
    results = {
        name: {"added_lines": 0, "paths": set(), "dev_placeholder_only": True}
        for name in SECRET_PATTERNS
    }
    path = None
    for line in log.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            for name, pat in SECRET_PATTERNS.items():
                if re.search(pat, line):
                    results[name]["added_lines"] += 1
                    results[name]["paths"].add(path)
                    if "django-insecure-" not in line:
                        results[name]["dev_placeholder_only"] = False
    env_files = sorted(
        {
            p
            for p in run(
                ["git", "log", "--all", "--name-only", "--format="]
            ).splitlines()
            if re.search(r"(^|/)\.env$", p)
        }
    )
    return {
        k: {
            "added_lines": v["added_lines"],
            "paths": sorted(v["paths"]),
            "dev_placeholder_only": v["dev_placeholder_only"] and v["added_lines"] > 0,
        }
        for k, v in results.items()
    }, env_files


def data_protection():
    from django.apps import apps

    child_models = []
    for model in apps.get_models():
        for f in model._meta.get_fields():
            if (
                f.is_relation
                and f.many_to_one
                and f.related_model
                and f.related_model.__name__
                in {"ChildProfile", "User", "Recommendation"}
                and model._meta.app_label in {"profiles", "recommendations", "feedback"}
            ):
                child_models.append(
                    f"{model.__name__}.{f.name} -> {f.related_model.__name__} ({f.remote_field.on_delete.__name__})"
                )
    soft = [
        f"{f}:{n}"
        for f, n, t in __import__("_common").grep(
            r"is_deleted|deleted_at|soft.?delet", ["backend"], re.I
        )
        if f.endswith(".py") and "/venv/" not in f
    ]
    export = [
        f"{f}:{n}"
        for f, n, t in __import__("_common").grep(
            r"export",
            [
                "backend/profiles",
                "backend/recommendations/views.py",
                "backend/feedback",
            ],
            re.I,
        )
        if f.endswith(".py") and "test" not in f and "management" not in f
    ]
    return [
        [
            "Consent record",
            "Implemented",
            f"`privacy_notice_version`, `privacy_agreed_at` on the user (backend/profiles/models.py:{line_of('backend/profiles/models.py', 'privacy_notice_version')}); `POST /api/auth/privacy-consent/`; notice text in backend/profiles/privacy.py; tests backend/profiles/test_privacy.py",
        ],
        [
            "Consent enforced",
            "Implemented",
            f"writes refused until agreed (backend/profiles/permissions.py:{line_of('backend/profiles/permissions.py', 'class HasPrivacyConsent')})",
        ],
        [
            "Data export (caregiver downloads their data)",
            "Not built" if not export else "Partial",
            (
                "no export endpoint or view found (searched `export` in profiles, recommendations views, feedback)"
                if not export
                else "; ".join(export)
            ),
        ],
        [
            "Cascading deletion",
            "Implemented",
            "; ".join(child_models)
            + "; account deletion `DELETE /api/auth/me/` (tests backend/profiles/test_account_deletion.py)",
        ],
        [
            "No soft delete for child data",
            "Implemented" if not soft else "Partial",
            (
                "no `is_deleted`/`deleted_at`/soft-delete fields in backend code: rows are deleted"
                if not soft
                else "; ".join(soft)
            ),
        ],
    ]


def deployment():
    # File names only: documents such as docs/deployment_requirements.md don't count.
    files = [
        l
        for l in run(["git", "ls-files"]).splitlines()
        if re.fullmatch(
            r"(?i)(dockerfile.*|docker-compose.*\.ya?ml|compose\.ya?ml|procfile|render\.ya?ml|fly\.toml|app\.ya?ml|nginx.*\.conf|.*\.service|deploy.*\.(sh|ps1|ya?ml))",
            l.split("/")[-1],
        )
    ]

    def size_mb(path, skip=()):
        total = 0
        for p in path.rglob("*"):
            if p.is_file() and not any(s in p.parts for s in skip):
                total += p.stat().st_size
        return round(total / 1e6, 1)

    from django.db import connection

    with connection.cursor() as c:
        c.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        db_size = c.fetchone()[0]
    latency = (
        json.loads(
            (ROOT / "docs/report_evidence/raw/latency_summary.json").read_text(
                encoding="utf-8"
            )
        )
        if (ROOT / "docs/report_evidence/raw/latency_summary.json").exists()
        else {}
    )
    apks = (
        sorted((APP / "build" / "app" / "outputs" / "flutter-apk").glob("*.apk"))
        if (APP / "build").exists()
        else []
    )
    gradle = "mobile/nurtura_app/android/app/build.gradle.kts"
    return {
        "deploy_files": files,
        "hosted": f"No deployment files in the repository; docs/known_limitations.md:{line_of('docs/known_limitations.md', 'Not hosted yet')} says the backend is not hosted. URL, provider, region, instance, database, HTTPS and cost: UNKNOWN (nothing hosted).",
        "peak_ram_mb": latency.get("peak_working_set_mb_end", "UNKNOWN"),
        "startup_s": latency.get("startup_s", "UNKNOWN"),
        "disk": {
            "backend code + model (no venv)": f"{size_mb(BACKEND, skip=('venv', '__pycache__'))} MB",
            "SBERT model folder": f"{size_mb(BACKEND / 'models' / 'all-MiniLM-L6-v2')} MB",
            "backend venv": f"{size_mb(BACKEND / 'venv')} MB",
            "database (pg_database_size)": db_size,
            "debug APKs built locally": ", ".join(
                f"{p.name} {round(p.stat().st_size / 1e6, 1)} MB" for p in apks
            )
            or "none",
        },
        "apk": [
            [
                "Build (debug, development)",
                "`flutter build apk --debug --dart-define=API_BASE_URL=http://127.0.0.1:8000`",
                "mobile/nurtura_app/README.md",
            ],
            [
                "Build (release)",
                "`flutter build apk --release --dart-define=API_BASE_URL=https://…`",
                f"docs/deployment_requirements.md:{line_of('docs/deployment_requirements.md', 'flutter build apk --release')}",
            ],
            [
                "Signing",
                "the release build type is signed with the **debug** key",
                f"{gradle}:{line_of(gradle, 'signingConfigs.getByName')}",
            ],
            [
                "Install",
                "`adb install -r <apk>` or `flutter run -d <device>`; the phone reaches the laptop with `adb reverse tcp:8000 tcp:8000`",
                "mobile/nurtura_app/README.md",
            ],
        ],
    }


def main():
    django_setup()
    neg = negative_tests()
    write_csv("security_negative_tests.csv", neg)
    impl = implementation_summary()
    write_csv(
        "security_implementation.csv",
        [dict(zip(["item", "value", "where"], r)) for r in impl],
    )

    import importlib.util

    audit = (
        "UNKNOWN: neither pip-audit nor safety is installed in the backend venv."
        if not (
            importlib.util.find_spec("pip_audit") or importlib.util.find_spec("safety")
        )
        else "installed; see raw/pip_audit.txt"
    )
    pub = subprocess.run(
        "flutter.bat pub outdated --json",
        cwd=APP,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    ).stdout
    write_text("flutter_pub_outdated.json", pub)
    try:
        packages = json.loads(pub[pub.index("{") :])["packages"]
        behind = [
            p
            for p in packages
            if p.get("current")
            and p.get("latest")
            and p["current"].get("version") != p["latest"].get("version")
        ]
        pub_summary = f"{len(behind)} packages have a newer version available (`flutter pub outdated` lists only those; direct and transitive). `raw/flutter_pub_outdated.json`."
    except (ValueError, KeyError):
        pub_summary = "UNKNOWN: `flutter pub outdated --json` gave no parsable output."
    secrets, env_files = secret_scan()
    write_json(
        "secret_scan.json", {"patterns": secrets, "env_files_ever_committed": env_files}
    )
    dp = data_protection()
    dep = deployment()
    write_json("deployment.json", dep)

    body = f"""## 4a. Negative tests

{len(neg)} checks through DRF's test client against the real URL configuration and settings, with fictional users, inside one transaction that was rolled back. `raw/security_negative_tests.csv`. Passed: {sum(r['result'] == 'pass' for r in neg)} of {len(neg)}.

{table(['Test', 'Request (redacted)', 'Expected', 'Actual', 'Result'], [[r['test'], f"`{r['request']}`", r['expected'], r['actual'], r['result']] for r in neg])}

## 4b. Implementation summary

{table(['Item', 'Value', 'Where'], impl)}

## 4c. Dependency audit and secret scan

- **Python dependency audit:** {audit}
- **Flutter:** {pub_summary}
- **Git history secret scan** (every added line in every commit on every branch, `git log --all -p`; counts and paths only, no values):

{table(['Pattern', 'Added lines', 'Paths', 'Note'], [[k, v['added_lines'], ', '.join(v['paths']) or '—', 'only the `django-insecure-` development fallback, used when DEBUG is on; production reads SECRET_KEY from the environment (backend/nurtura_backend/settings.py:' + str(line_of('backend/nurtura_backend/settings.py', 'SECRET_KEY must be set')) + ')' if v['dev_placeholder_only'] else ('test files only: fictional test passwords' if v['paths'] and all('/test' in x for x in v['paths']) else '')] for k, v in secrets.items()])}

`.env` files ever committed: {', '.join(env_files) or 'none'}. Matches of the generic "password/secret assignment" pattern are candidates to review, not confirmed secrets; `raw/secret_scan.json`.

## 4d. Data protection

{table(['Item', 'Status', 'Evidence'], dp)}

## 4e. Deployment

- **Deployment files in the repository:** {', '.join(dep['deploy_files']) or 'none'}.
- **Hosting:** {dep['hosted']}
- **Measured** (one development laptop, `05_latency.md`): peak working set {dep['peak_ram_mb']} MB; start-up {dep['startup_s']} s.

{table(['Disk', 'Size'], [[k, v] for k, v in dep['disk'].items()])}

APK:

{table(['Step', 'How', 'Where'], dep['apk'])}
"""
    write_md(
        "11_security_privacy_deployment.md",
        body,
        "Security, privacy and deployment",
        COMMAND,
    )
    print(
        sum(r["result"] == "pass" for r in neg), "of", len(neg), "negative tests pass"
    )


if __name__ == "__main__":
    main()
