"""Section 3: sync Chapters 1-4 with the build.

3a data model, 3b API, 3c permissions (probed), 3d admin site, 3e
management commands, 3f mobile map, 3g request flow, 3h deviations,
3i changes since sprint6-explanations-v1.

Read-only. The permission probe sends real requests through DRF's test
client; every request runs in its own savepoint inside one transaction that
is rolled back, and the in-process throttle cache is cleared between them.
"""

import json
import re
from collections import defaultdict

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
)

COMMAND = (
    "backend\\venv\\Scripts\\python.exe scripts\\report_evidence\\sync_chapters.py"
)
PROJECT_APPS = ("profiles", "activities", "recommendations", "feedback", "insights")


# ---------------------------------------------------------------- 3a
def data_model():
    from django.apps import apps
    from django.db import models

    fields_rows, model_rows, er, classes = [], [], [], []
    for model in apps.get_models():
        if model._meta.app_label not in PROJECT_APPS:
            continue
        name = model.__name__
        meta = model._meta
        attrs = []
        for f in meta.get_fields():
            if f.auto_created and not f.concrete:
                continue
            if not getattr(f, "concrete", False) and not f.many_to_many:
                continue
            default = f.default if f.has_default() else ""
            if callable(default):
                default = getattr(default, "__name__", "callable")
            rel = ""
            on_delete = ""
            if f.is_relation and f.related_model:
                rel = f.related_model.__name__
                on_delete = getattr(
                    getattr(f.remote_field, "on_delete", None), "__name__", ""
                )
                kind = "1:1" if f.one_to_one else ("M:N" if f.many_to_many else "N:1")
                er.append(
                    f'    {rel} ||--o{{ {name} : "{f.name} ({kind}, {on_delete or "m2m"})"'
                )
            fields_rows.append(
                {
                    "model": f"{meta.app_label}.{name}",
                    "field": f.name,
                    "type": f.get_internal_type(),
                    "null": getattr(f, "null", ""),
                    "blank": getattr(f, "blank", ""),
                    "default": str(default)[:60],
                    "choices": "; ".join(str(c[0]) for c in (f.choices or []))[:120],
                    "unique": getattr(f, "unique", ""),
                    "db_index": getattr(f, "db_index", ""),
                    "max_length": getattr(f, "max_length", "") or "",
                    "foreign_key_to": rel,
                    "on_delete": on_delete,
                }
            )
            attrs.append(f"        {f.get_internal_type()} {f.name}")
        constraints = "; ".join(
            f"{c.name}: {type(c).__name__}" for c in meta.constraints
        )
        indexes = "; ".join(f"{i.name}: {', '.join(i.fields)}" for i in meta.indexes)
        unique_together = "; ".join(", ".join(u) for u in meta.unique_together)
        model_rows.append(
            {
                "model": f"{meta.app_label}.{name}",
                "table": meta.db_table,
                "constraints": constraints,
                "indexes": indexes,
                "unique_together": unique_together,
            }
        )
        methods = [
            m
            for m in vars(model)
            if callable(vars(model)[m])
            and not m.startswith("_")
            and m not in {"DoesNotExist", "MultipleObjectsReturned"}
        ]
        classes.append(
            f"    class {name} {{\n"
            + "\n".join(attrs)
            + (
                "\n" + "\n".join(f"        +{m}()" for m in methods[:8])
                if methods
                else ""
            )
            + "\n    }"
        )
    migrations = run(
        [
            str(BACKEND / "venv" / "Scripts" / "python.exe"),
            "manage.py",
            "makemigrations",
            "--check",
            "--dry-run",
        ],
        cwd=BACKEND,
    )
    return fields_rows, model_rows, sorted(set(er)), classes, migrations.strip()


# ---------------------------------------------------------------- 3b/3c
def api_patterns():
    from django.urls import get_resolver
    from django.urls.resolvers import URLPattern, URLResolver

    out = []

    def walk(patterns, prefix=""):
        for p in patterns:
            if isinstance(p, URLResolver):
                walk(p.url_patterns, prefix + str(p.pattern))
            elif isinstance(p, URLPattern):
                route = prefix + str(p.pattern)
                if "format" in route or not route.startswith("api/"):
                    continue
                out.append((route, p))

    walk(get_resolver().url_patterns)
    return out


def clean_route(route):
    route = route.replace("^", "").replace("$", "")
    route = re.sub(r"\(\?P<(\w+)>[^)]*\)", r"<\1>", route)
    return "/" + route


def view_info(pattern):
    from django.conf import settings

    cb = pattern.callback
    cls = getattr(cb, "cls", None) or getattr(cb, "view_class", None)
    actions = getattr(cb, "actions", None)
    if actions:
        methods = sorted(m.upper() for m in actions)
    elif cls:
        methods = sorted(
            m.upper()
            for m in ("get", "post", "put", "patch", "delete")
            if hasattr(cls, m)
        )
    else:
        methods = []
    perms = [p.__name__ for p in getattr(cls, "permission_classes", [])] if cls else []
    auth = (
        [a.__name__ for a in getattr(cls, "authentication_classes", [])] if cls else []
    )
    throttles = (
        [t.__name__ for t in getattr(cls, "throttle_classes", [])] if cls else []
    )
    scope = getattr(cls, "throttle_scope", "") if cls else ""
    serializer = (
        getattr(getattr(cls, "serializer_class", None), "__name__", "") if cls else ""
    )
    src = ""
    if cls:
        import inspect

        try:
            src = f"{inspect.getsourcefile(cls).replace(chr(92), '/').split('/backend/')[-1]}:{inspect.getsourcelines(cls)[1]}"
        except (TypeError, OSError):
            src = ""
    return {
        "view": cls.__name__ if cls else getattr(cb, "__name__", "?"),
        "methods": methods,
        "authentication": ", ".join(auth) or "default",
        "permissions": ", ".join(perms) or "default",
        "throttle": ", ".join(throttles) + (f" (scope {scope})" if scope else ""),
        "serializer": serializer,
        "source": "backend/" + src if src else "",
    }


def probe(patterns):
    """Status codes per role for every endpoint and method (rolled back)."""
    from django.contrib.auth import get_user_model
    from django.core.cache import cache
    from django.db import transaction
    from rest_framework.test import APIClient

    from activities.models import DevelopmentalActivity
    from profiles.models import ReferenceMilestone
    from recommendations import generation, heldout

    User = get_user_model()
    results = []
    with rolled_back():
        owner = User.objects.create_user(
            username="owner@nurtura.invalid",
            email="owner@nurtura.invalid",
            password="Fictional-Passw0rd!",
        )
        other = User.objects.create_user(
            username="other@nurtura.invalid",
            email="other@nurtura.invalid",
            password="Fictional-Passw0rd!",
        )
        admin = User.objects.create_user(
            username="admin@nurtura.invalid",
            email="admin@nurtura.invalid",
            password="Fictional-Passw0rd!",
            role=User.Role.ADMINISTRATOR,
        )
        from profiles import privacy

        for u in (owner, other):  # normal caregivers have agreed to the notice
            privacy.record_consent(u)
            u.save()
        child = heldout.create_child(heldout.HELDOUT_CHILDREN[0], owner)
        rec = generation.generate(child.pk, owner).recommendations[0]
        activity = (
            DevelopmentalActivity.objects.filter(content_status="published")
            .order_by("pk")
            .first()
        )
        values = {
            "pk": child.pk,
            "child_id": child.pk,
            "recommendation_id": rec.pk,
            "activity_id": activity.activity_id,
        }
        ref_pk = ReferenceMilestone.objects.order_by("pk").first().pk
        roles = {
            "anonymous": None,
            "owner caregiver": owner,
            "other caregiver": other,
            "administrator": admin,
        }
        for route, pattern in patterns:
            info = view_info(pattern)
            path = clean_route(route)
            if (
                "/admin/activities/<int:pk>" in path
                or "reference-milestones/<pk>" in path
            ):
                path_filled = path.replace("<int:pk>", str(activity.pk)).replace(
                    "<pk>", str(ref_pk)
                )
            else:
                path_filled = re.sub(
                    r"<(?:\w+:)?(\w+)>", lambda m: str(values.get(m.group(1), 1)), path
                )
            for method in info["methods"]:
                row = {"endpoint": path, "method": method}
                for role, user in roles.items():
                    cache.clear()
                    client = APIClient(HTTP_HOST="localhost")
                    if user:
                        client.force_authenticate(user)
                    sid = transaction.savepoint()
                    try:
                        response = getattr(client, method.lower())(
                            path_filled, {}, format="json"
                        )
                        row[role] = response.status_code
                    except Exception as exc:  # noqa: BLE001 - recorded, not hidden
                        row[role] = f"error {type(exc).__name__}"
                    transaction.savepoint_rollback(sid)
                results.append(row)
    return results


# ---------------------------------------------------------------- 3d
def admin_site():
    from django.contrib import admin

    rows = []
    for model, ma in admin.site._registry.items():
        rows.append(
            {
                "model": f"{model._meta.app_label}.{model.__name__}",
                "admin_class": type(ma).__name__,
                "list_display": ", ".join(map(str, ma.list_display)),
                "list_filter": ", ".join(
                    str(f if isinstance(f, str) else getattr(f, "__name__", f))
                    for f in ma.list_filter
                ),
                "search_fields": ", ".join(ma.search_fields),
                "actions": ", ".join(
                    str(getattr(a, "__name__", a)) for a in (ma.actions or [])
                ),
                "readonly_fields": ", ".join(map(str, ma.readonly_fields)),
            }
        )
    return sorted(rows, key=lambda r: r["model"])


# ---------------------------------------------------------------- 3e
WRITE_HINTS = re.compile(
    r"\.(save|create|bulk_create|update_or_create|get_or_create|delete|update)\(|write_text|open\([^)]*['\"]w"
)


def commands():
    from django.core.management import get_commands, load_command_class

    rows = []
    for name, app in sorted(get_commands().items()):
        if app not in PROJECT_APPS:
            continue
        cmd = load_command_class(app, name)
        parser = cmd.create_parser("manage.py", name)
        opts = [
            "/".join(a.option_strings)
            + (
                f" (default {a.default})"
                if a.default not in (None, False, "==SUPPRESS==")
                else ""
            )
            for a in parser._actions
            if a.option_strings
            and a.dest
            not in {
                "help",
                "version",
                "verbosity",
                "settings",
                "pythonpath",
                "traceback",
                "no_color",
                "force_color",
                "skip_checks",
            }
        ]
        path = BACKEND / app / "management" / "commands" / f"{name}.py"
        src = path.read_text(encoding="utf-8")
        writes_db = bool(
            re.search(
                r"\.(save|create|bulk_create|update_or_create|get_or_create|delete)\(|\.update\(",
                src,
            )
        )
        writes_files = bool(
            re.search(r"write_text|open\([^)]*['\"]w|csv\.writer|DictWriter", src)
        )
        rows.append(
            {
                "command": name,
                "app": app,
                "purpose": (cmd.help or "").strip().split("\n")[0],
                "options": "; ".join(opts),
                "writes_database": "yes" if writes_db else "no",
                "writes_files": "yes" if writes_files else "no",
                "dry_run_option": "yes" if "--dry-run" in " ".join(opts) else "no",
                "file": path.relative_to(ROOT).as_posix(),
            }
        )
    return rows


# ---------------------------------------------------------------- 3f
def mobile_map():
    services = {}
    for path in (APP / "lib" / "services").glob("*.dart"):
        text = path.read_text(encoding="utf-8")
        for cls in re.findall(r"^class (\w+)", text, re.M):
            services[cls] = sorted(
                set(
                    re.findall(r"_api\.(get|post|put|patch|delete)\(\s*'([^']+)'", text)
                )
            )
    screens, edges = [], []
    files = sorted((APP / "lib" / "screens").rglob("*.dart")) + sorted(
        (APP / "lib" / "widgets").glob("*sheet*.dart")
    )
    for path in files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        classes = re.findall(
            r"^class (\w+) extends (?:StatelessWidget|StatefulWidget)", text, re.M
        )
        used = sorted({s for s in services if re.search(rf"\b{s}\b", text)})
        # methods called on services through state objects are not visible here;
        # record the service classes named in the file
        calls = sorted({f"{m.upper()} {u}" for s in used for m, u in services[s]})
        for target in re.findall(
            r"MaterialPageRoute(?:<\w+>)?\(\s*(?:fullscreenDialog:\s*\w+,\s*)?builder:\s*\([^)]*\)\s*=>\s*(?:const\s+)?(\w+)\(",
            text,
        ):
            edges.append((classes[0] if classes else path.stem, target))
        for target in re.findall(
            r"show(?:Modal)?BottomSheet[\s\S]{0,200}?=>\s*(?:const\s+)?(\w+)\(", text
        ):
            edges.append((classes[0] if classes else path.stem, target))
        screens.append(
            {
                "file": rel,
                "screens": " ".join(classes[:3]),
                "purpose": (
                    re.search(r"^/// (.+)$", text, re.M).group(1)[:110]
                    if re.search(r"^/// (.+)$", text, re.M)
                    else ""
                ),
                "services_named": " ".join(used),
                "loading": (
                    "yes"
                    if re.search(
                        r"CircularProgressIndicator|_loading|isLoading|Loading", text
                    )
                    else "no"
                ),
                "empty_state": (
                    "yes"
                    if re.search(r"[Nn]o \w+ yet|empty|Key\('no\w+'\)", text)
                    else "no"
                ),
                "error_state": (
                    "yes"
                    if re.search(r"MessageBanner\.error|_error|errorText", text)
                    else "no"
                ),
            }
        )
    tabs = re.findall(
        r"key: Key\('(tab_\w+)'\)",
        (APP / "lib" / "screens" / "home_shell.dart").read_text(encoding="utf-8"),
    )
    return screens, sorted(set(edges)), services, tabs


# ---------------------------------------------------------------- 3g
def request_flow():
    steps = [
        (
            "App sends POST /api/children/<id>/recommendations/",
            "mobile/nurtura_app/lib/services/recommendation_service.dart",
            r"recommendations/",
        ),
        (
            "View checks the caregiver and calls generate()",
            "backend/recommendations/views.py",
            r"result = generation.generate\(child_id",
        ),
        (
            "Lock the child row so concurrent requests store one batch",
            "backend/recommendations/generation.py",
            r"select_for_update",
        ),
        (
            "Rank: rule engine + retrieval + scoring",
            "backend/recommendations/generation.py",
            r"result = rank\(child\)",
        ),
        (
            "Build the developmental profile from milestones, concerns and interests",
            "backend/profiles/rules/__init__.py",
            r"def build_profile",
        ),
        (
            "Rule engine: baseline + rule adjustments, normalised to 0-1",
            "backend/profiles/rules/engine.py",
            r"def evaluate",
        ),
        (
            "Write the plain-language query",
            "backend/recommendations/retrieval.py",
            r"def profile_query",
        ),
        (
            "Encode the query with SBERT; dot product with stored vectors",
            "backend/recommendations/retrieval.py",
            r"matrix @ query_vector",
        ),
        (
            "Score every eligible activity: age weight x ((1-alpha) sim + alpha priority)",
            "backend/recommendations/ranking.py",
            r"score = weight",
        ),
        (
            "Personalise from feedback (boost liked, demote not working)",
            "backend/recommendations/generation.py",
            r"personal = personalise",
        ),
        (
            "Leave out completed activities; keep pinned ones first",
            "backend/recommendations/generation.py",
            r"skip = completed",
        ),
        (
            "Take the top 5",
            "backend/recommendations/generation.py",
            r"RECOMMENDATIONS_PER_BATCH - len\(notes\)",
        ),
        (
            "Explain each one",
            "backend/recommendations/generation.py",
            r"explain\(child, result.evaluation, r\)",
        ),
        (
            "Store a new batch, or return the identical newest one",
            "backend/recommendations/generation.py",
            r"if newest and \(",
        ),
        (
            "Response: cards + clinic-visit referral (201 new, 200 same)",
            "backend/recommendations/views.py",
            r"HTTP_201_CREATED if result.created",
        ),
    ]
    return [
        {"step": i, "what": what, "where": f"{f}:{line_of(f, pat) or 'UNKNOWN'}"}
        for i, (what, f, pat) in enumerate(steps, 1)
    ]


# ---------------------------------------------------------------- 3h
def deviations():
    text = (
        (ROOT / "docs" / "requirements_traceability.md")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    rows = []
    in_req = False
    for i, line in enumerate(text, 1):
        if line.startswith("## Functional requirements"):
            in_req = True
        if line.startswith("## Built beyond"):
            in_req = False
        m = re.match(r"^\| ((?:FR|NFR|DR|IR)-\d+) \| ([^|]+) \|", line)
        if in_req and m and re.search(r"with a deviation|Partly met", line):
            note = re.search(
                r"\*\*(?:Met, with a deviation|Partly met)[:.]?\*\*\s*(.*?)\s*\|?\s*$",
                line,
            )
            rows.append(
                {
                    "what": f"{m.group(1)} {m.group(2).strip()}",
                    "difference": (note.group(1) if note else "")[:300],
                    "evidence": f"docs/requirements_traceability.md:{i}",
                }
            )
    start = next(i for i, l in enumerate(text) if l.startswith("## Wording to update"))
    for i, line in enumerate(text[start:], start + 1):
        m = re.match(r"^- \*\*(.+?):\*\* (.+)$", line)
        if m:
            rows.append(
                {
                    "what": f"Report wording: {m.group(1)}",
                    "difference": m.group(2),
                    "evidence": f"docs/requirements_traceability.md:{i}",
                }
            )
    for f, n, t in [
        (f, n, t)
        for f, n, t in __import__("_common").grep(
            r"deviat", ["docs/known_limitations.md", "docs/PROJECT_OVERVIEW.md"], re.I
        )
    ]:
        rows.append(
            {"what": "Stated in docs", "difference": t[:300], "evidence": f"{f}:{n}"}
        )
    return rows


# ---------------------------------------------------------------- 3i
def since_tag(tag="sprint6-explanations-v1"):
    tag_date = run(["git", "log", "-1", "--format=%cI", tag]).strip()
    prs = json.loads(
        run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "merged",
                "--limit",
                "1000",
                "--json",
                "number,title,mergedAt,body",
            ]
        )
        or "[]"
    )
    rows = []
    for p in sorted(prs, key=lambda p: p["mergedAt"]):
        if p["mergedAt"] > tag_date:
            body = p.get("body") or ""
            first = next(
                (
                    l.strip("-* ").strip()
                    for l in body.splitlines()
                    if l.strip() and not l.startswith("#")
                ),
                "",
            )
            rows.append(
                {
                    "pr": p["number"],
                    "merged": p["mergedAt"][:10],
                    "title": p["title"],
                    "summary": re.sub(r"\s+", " ", first)[:220],
                }
            )
    return tag_date, rows


def main():
    django_setup()
    fields_rows, model_rows, er, classes, migrations = data_model()
    write_csv("model_fields.csv", fields_rows)
    write_csv("model_tables.csv", model_rows)
    mermaid_er = "erDiagram\n" + "\n".join(er)
    mermaid_class = "classDiagram\n" + "\n".join(classes)
    (ROOT / "docs" / "report_evidence" / "raw").mkdir(exist_ok=True)
    (ROOT / "docs" / "report_evidence" / "raw" / "er_diagram.mmd").write_text(
        mermaid_er + "\n", encoding="utf-8"
    )
    (ROOT / "docs" / "report_evidence" / "raw" / "class_diagram.mmd").write_text(
        mermaid_class + "\n", encoding="utf-8"
    )

    patterns = api_patterns()
    endpoints = []
    for route, p in patterns:
        info = view_info(p)
        endpoints.append(
            {
                "endpoint": clean_route(route),
                "name": p.name or "",
                **{
                    k: (", ".join(v) if isinstance(v, list) else v)
                    for k, v in info.items()
                },
            }
        )
    write_csv("api_endpoints.csv", endpoints)
    matrix = probe(patterns)
    write_csv("permission_probe.csv", matrix)
    transcript = (
        json.loads(
            (
                ROOT / "docs" / "report_evidence" / "raw" / "workflow_transcript.json"
            ).read_text(encoding="utf-8")
        )
        if (
            ROOT / "docs" / "report_evidence" / "raw" / "workflow_transcript.json"
        ).exists()
        else []
    )

    admin_rows = admin_site()
    write_csv("admin_site.csv", admin_rows)
    from django.contrib.admin import AdminSite

    cmd_rows = commands()
    write_csv("management_commands.csv", cmd_rows)
    screens, edges, services, tabs = mobile_map()
    write_csv("mobile_screens_map.csv", screens)
    write_json("mobile_services.json", services)
    nav = "flowchart LR\n" + "\n".join(f"    {a} --> {b}" for a, b in edges)
    (ROOT / "docs" / "report_evidence" / "raw" / "mobile_navigation.mmd").write_text(
        nav + "\n", encoding="utf-8"
    )
    flow = request_flow()
    write_csv("request_flow.csv", flow)
    devs = deviations()
    write_csv("deviations.csv", devs)
    tag_date, changes = since_tag()
    write_csv("changes_since_sprint6.csv", changes)

    def code(v):
        return {
            200: "200",
            201: "201",
            204: "204",
            400: "400 (allowed; bad body)",
            401: "401",
            403: "403",
            404: "404",
            405: "405",
        }.get(v, str(v))

    body = f"""## 3a. Data model

`makemigrations --check --dry-run`: "{migrations or 'no output'}" (the models match the migrations, so this describes the migrated schema). {len(model_rows)} models, {len(fields_rows)} fields. Every field with type, null, blank, default, choices, unique, index, foreign key and on_delete: `raw/model_fields.csv`. Constraints and indexes per table: `raw/model_tables.csv`. Mermaid: `raw/er_diagram.mmd`, `raw/class_diagram.mmd`.

{table(['Model', 'Table', 'Constraints', 'Indexes'], [[m['model'], m['table'], m['constraints'] or '—', m['indexes'] or '—'] for m in model_rows])}

Foreign keys (from the ER diagram):

```mermaid
{mermaid_er}
```

## 3b. API

Every endpoint under `/api/` from the URL resolver, with its view, methods, permission and throttle classes (`raw/api_endpoints.csv`). Authentication everywhere is the project default (`REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES` in `backend/nurtura_backend/settings.py:{line_of('backend/nurtura_backend/settings.py', 'DEFAULT_AUTHENTICATION_CLASSES')}`) unless a view sets its own. Fictional request and response examples for the main flow: `raw/workflow_transcript.json` ({len(transcript)} calls, see `07_workflow_transcript.md`).

{table(['Endpoint', 'Methods', 'View', 'Permissions', 'Throttle', 'Source'], [[f"`{e['endpoint']}`", e['methods'], e['view'], e['permissions'], e['throttle'] or '—', e['source']] for e in endpoints])}

## 3c. Permissions matrix (observed)

Each endpoint and method was called with an empty JSON body as four users: anonymous, the child's own caregiver, another caregiver and an administrator. Each call ran in its own savepoint and was rolled back. 400 means the request got past the permission check and was refused for its (empty) body. Raw: `raw/permission_probe.csv`. Both caregivers have agreed to the privacy notice: until a caregiver agrees, every write except DELETE is refused with 403 (`HasPrivacyConsent`, `backend/profiles/permissions.py:{line_of('backend/profiles/permissions.py', 'class HasPrivacyConsent')}`).

{table(['Endpoint', 'Method', 'Anonymous', 'Own caregiver', 'Other caregiver', 'Administrator'], [[f"`{r['endpoint']}`", r['method'], code(r['anonymous']), code(r['owner caregiver']), code(r['other caregiver']), code(r['administrator'])] for r in matrix])}

## 3d. Admin site (`/admin/`)

Who can enter: Django's `AdminSite.has_permission` requires an active staff user. `is_staff` is derived from the role, so only Administrators have it (`backend/profiles/models.py:{line_of('backend/profiles/models.py', 'def save')}`). The negative test is in `14_security_privacy_deployment.md`. `raw/admin_site.csv`.

{table(['Model', 'Columns', 'Filters', 'Search', 'Actions', 'Read-only'], [[a['model'], a['list_display'] or '—', a['list_filter'] or '—', a['search_fields'] or '—', a['actions'] or '—', a['readonly_fields'] or '—'] for a in admin_rows])}

## 3e. Management commands

"Writes" is read from each command's source (database calls such as `.save(`, `.create(`, `.update(`, `.delete(`; file writes such as `open(..., "w")`). `raw/management_commands.csv` has the options.

{table(['Command', 'Purpose', 'Writes DB', 'Writes files', '--dry-run'], [[f"`{c['command']}`", c['purpose'][:110], c['writes_database'], c['writes_files'], c['dry_run_option']] for c in cmd_rows])}

## 3f. Mobile app

The app has no named routes: screens are pushed with `MaterialPageRoute` or opened as bottom sheets. The home shell has the tabs {', '.join(tabs)}. Per file: screens, the service classes it names, and whether it has loading, empty and error handling (found by pattern in the source; `raw/mobile_screens_map.csv`). Service classes and their API calls: `raw/mobile_services.json`. Navigation edges: `raw/mobile_navigation.mmd`.

{table(['File', 'Screens', 'Services named', 'Loading', 'Empty', 'Error'], [[s['file'].split('/lib/')[-1], s['screens'], s['services_named'] or '—', s['loading'], s['empty_state'], s['error_state']] for s in screens])}

API calls by service class:

{table(['Service', 'Calls'], [[s, '<br>'.join(f'{m.upper()} `{u}`' for m, u in calls) or '—'] for s, calls in sorted(services.items())])}

```mermaid
{nav}
```

## 3g. The recommendation request, step by step

{table(['#', 'Step', 'Where'], [[f['step'], f['what'], f['where']] for f in flow])}

## 3h. Where the build differs from the requirement text or the report

From `docs/requirements_traceability.md` (rows that are met with a deviation or partly met, and its "Wording to update" list) and deviations stated in the docs. `raw/deviations.csv`. The proposal document isn't in the repository, so differences it alone records can't be checked here.

{table(['What', 'Difference', 'Evidence'], [[d['what'], d['difference'].replace('|', '/'), d['evidence']] for d in devs])}

## 3i. Merged since tag `sprint6-explanations-v1` ({tag_date[:10]})

{len(changes)} pull requests (`gh pr list --state merged`, merged after the tag's commit date). `raw/changes_since_sprint6.csv`.

{table(['PR', 'Merged', 'Title'], [[f"#{c['pr']}", c['merged'], c['title']] for c in changes])}
"""
    write_md(
        "10_chapters_1_to_4_sync.md", body, "Chapters 1-4 against the build", COMMAND
    )
    print(
        len(model_rows),
        "models;",
        len(endpoints),
        "endpoints;",
        len(matrix),
        "probe rows;",
        len(cmd_rows),
        "commands;",
        len(changes),
        "PRs since tag",
    )


if __name__ == "__main__":
    main()
