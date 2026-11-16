"""2f workflow transcript for one fictional caregiver, through the REST API.

Every request goes through Django REST framework's test client inside one
transaction that is rolled back, so nothing is saved. Emails go to the
console backend and are captured, never sent. Tokens, codes, challenges and
email addresses are redacted in the saved transcript. The rows created are
read back before the rollback.
"""

import contextlib
import datetime
import io
import json
import re

from _common import django_setup, redact, rolled_back, table, write_json, write_md

COMMAND = "backend\\venv\\Scripts\\python.exe scripts\\report_evidence\\workflow_transcript.py"
EMAIL = "fictional.caregiver@nurtura.invalid"
PASSWORD = "Fictional-Passw0rd!"
DEVICE = "evidence-device-0123456789abcdef"
SECRET_KEYS = {"token", "challenge", "code", "device_id", "password"}


def scrub(value):
    if isinstance(value, dict):
        return {
            k: ("<redacted>" if k in SECRET_KEYS else scrub(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, str):
        return redact(value).replace(EMAIL, "<redacted>")
    return value


def main():
    django_setup()
    from django.forms.models import model_to_dict
    from rest_framework.test import APIClient

    from feedback.models import CompletedActivity, Feedback
    from profiles.models import ChildProfile, DevelopmentalMilestone, ReferenceMilestone
    from recommendations.models import Recommendation

    steps = []

    def call(client, method, path, body=None, note=""):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            response = getattr(client, method)(path, body, format="json")
        try:
            data = response.json()
        except (ValueError, TypeError):
            data = None
        steps.append(
            {
                "step": note,
                "request": f"{method.upper()} {path}",
                "body": scrub(body),
                "status": response.status_code,
                "response": scrub(data),
            }
        )
        return response, data, out.getvalue()

    def code_from(mail):
        m = re.search(r"code is (\d{6})", mail)
        return m.group(1) if m else None

    rows = {}
    with rolled_back():
        client = APIClient(HTTP_HOST="localhost")
        _, reg, mail = call(
            client,
            "post",
            "/api/auth/register/",
            {
                "username": EMAIL,
                "email": EMAIL,
                "password": PASSWORD,
                "device_id": DEVICE,
            },
            "Register",
        )
        _, verified, _ = call(
            client,
            "post",
            "/api/auth/login/verify/",
            {
                "challenge": reg.get("challenge"),
                "code": code_from(mail),
                "device_id": DEVICE,
            },
            "Verify the emailed code (register)",
        )
        token = (verified or {}).get("token")
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        call(client, "post", "/api/auth/logout/", None, "Log out")
        client.credentials()
        _, login, mail = call(
            client,
            "post",
            "/api/auth/login/",
            {"username": EMAIL, "password": PASSWORD, "device_id": DEVICE},
            "Log in",
        )
        if login and login.get("challenge"):
            _, verified, _ = call(
                client,
                "post",
                "/api/auth/login/verify/",
                {
                    "challenge": login["challenge"],
                    "code": code_from(mail),
                    "device_id": DEVICE,
                },
                "Verify the emailed code (login)",
            )
            token = verified.get("token")
        else:
            token = (login or {}).get("token")
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        _, notice, _ = call(
            client, "get", "/api/privacy-notice/", None, "Read the privacy notice"
        )
        call(
            client,
            "post",
            "/api/auth/privacy-consent/",
            {"version": (notice or {}).get("version")},
            "Agree to the privacy notice",
        )
        born = (datetime.date.today() - datetime.timedelta(days=396)).isoformat()
        _, child, _ = call(
            client,
            "post",
            "/api/children/",
            {
                "name": "Fictional Child",
                "date_of_birth": born,
                "interests": ["water"],
                "concerns": ["Language"],
            },
            "Create a child (about 13 months)",
        )
        cid = child["id"]
        ref = ReferenceMilestone.objects.get(milestone_key="CDC-12M-LA-01")
        call(
            client,
            "post",
            f"/api/children/{cid}/milestones/",
            {"reference": ref.pk, "status": "not_yet"},
            'Record "Waves bye-bye" as Not yet',
        )
        _, batch, _ = call(
            client,
            "post",
            f"/api/children/{cid}/recommendations/",
            {},
            "Generate recommendations",
        )
        call(
            client,
            "get",
            f"/api/children/{cid}/recommendations/",
            None,
            "Read the stored batch",
        )
        rid = batch["recommendations"][0]["id"]
        call(
            client,
            "put",
            f"/api/recommendations/{rid}/completion/",
            {"status": "completed"},
            "Mark the first idea done",
        )
        call(
            client,
            "put",
            f"/api/recommendations/{rid}/feedback/",
            {
                "outcome": "went_well",
                "interest": "loved_it",
                "rating": 5,
                "comment": "Fictional note",
            },
            "Give feedback",
        )

        c = ChildProfile.objects.get(pk=cid)
        rows = {
            "child_profile": model_to_dict(c, exclude=["caregiver"]),
            "developmental_milestones": [
                model_to_dict(m) for m in DevelopmentalMilestone.objects.filter(child=c)
            ],
            "recommendations": [
                {
                    **model_to_dict(r, exclude=["explanation"]),
                    "activity_id": r.activity.activity_id,
                    "explanation": r.explanation,
                }
                for r in Recommendation.objects.filter(child=c).order_by(
                    "batch", "position"
                )
            ],
            "completed_activities": [
                model_to_dict(x)
                for x in CompletedActivity.objects.filter(recommendation__child=c)
            ],
            "feedback": [
                model_to_dict(x, exclude=["caregiver"])
                for x in Feedback.objects.filter(recommendation__child=c)
            ],
        }

    rows = scrub(rows)
    write_json("workflow_transcript.json", steps)
    write_json("workflow_rows.json", rows)
    body = f"""One fictional caregiver through the REST API, in one transaction that was rolled back (nothing saved). Emails were captured from the console backend; tokens, codes, challenges, device IDs and email addresses are `<redacted>`. Raw: `raw/workflow_transcript.json` (every request and response), `raw/workflow_rows.json` (rows read back before the rollback).

{table(['#', 'Step', 'Request', 'Status'], [[i, s['step'], f"`{s['request']}`", s['status']] for i, s in enumerate(steps, 1)])}

## Rows created

{table(['Table', 'Rows'], [[k, len(v) if isinstance(v, list) else 1] for k, v in rows.items()])}

First stored recommendation (fields as saved):

```json
{json.dumps(rows['recommendations'][0] if rows['recommendations'] else {}, indent=2, ensure_ascii=False, default=str)}
```
"""
    write_md(
        "07_workflow_transcript.md",
        body,
        "Workflow transcript (fictional caregiver)",
        COMMAND,
    )
    print([(s["step"], s["status"]) for s in steps])


if __name__ == "__main__":
    main()
