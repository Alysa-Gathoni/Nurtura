# Workflow transcript (fictional caregiver)

> Generated 2026-11-21T00:49:23+03:00 at commit `82ba4a5` by `backend\venv\Scripts\python.exe scripts\report_evidence\workflow_transcript.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

One fictional caregiver through the REST API, in one transaction that was rolled back (nothing saved). Emails were captured from the console backend; tokens, codes, challenges, device IDs and email addresses are `<redacted>`. Raw: `raw/workflow_transcript.json` (every request and response), `raw/workflow_rows.json` (rows read back before the rollback).

| # | Step | Request | Status |
|---|---|---|---|
| 1 | Register | `POST /api/auth/register/` | 201 |
| 2 | Verify the emailed code (register) | `POST /api/auth/login/verify/` | 200 |
| 3 | Log out | `POST /api/auth/logout/` | 204 |
| 4 | Log in | `POST /api/auth/login/` | 200 |
| 5 | Read the privacy notice | `GET /api/privacy-notice/` | 200 |
| 6 | Agree to the privacy notice | `POST /api/auth/privacy-consent/` | 200 |
| 7 | Create a child (about 13 months) | `POST /api/children/` | 201 |
| 8 | Record "Waves bye-bye" as Not yet | `POST /api/children/1599/milestones/` | 201 |
| 9 | Generate recommendations | `POST /api/children/1599/recommendations/` | 201 |
| 10 | Read the stored batch | `GET /api/children/1599/recommendations/` | 200 |
| 11 | Mark the first idea done | `PUT /api/recommendations/1747/completion/` | 201 |
| 12 | Give feedback | `PUT /api/recommendations/1747/feedback/` | 201 |

## Rows created

| Table | Rows |
|---|---|
| child_profile | 1 |
| developmental_milestones | 1 |
| recommendations | 5 |
| completed_activities | 1 |
| feedback | 1 |

First stored recommendation (fields as saved):

```json
{
  "id": 1747,
  "child": 1599,
  "activity": 1235,
  "batch": "7f9f0566-8e2e-4144-bdc8-b353c39afdb7",
  "position": 1,
  "similarity_score": 0.2193284521815665,
  "ranking_score": 0.8635903336953925,
  "rule_priority": 1.0,
  "age_weight": 1.0,
  "alpha": 0.7,
  "profile_fingerprint": "ae0113e1fec2825d58efbe7393059d9a68428eb4147ba18683adc99ac8e02d61",
  "ranking_version": "1bebb5441fd039526e63ec57f62d5d513a017a4bd839773fdfe00ff8b5d928c4",
  "pinned": false,
  "pin_note": "",
  "explanation_version": "2",
  "date_generated": "2026-11-20 21:49:23.069220+00:00",
  "plan_start": "2026-11-16",
  "activity_id": "ACT-0179",
  "explanation": "You recorded “Waves ‘bye-bye’” as not yet; most children do this by 12 months. You said you'd like support with language and communication. It's designed for children aged 12–18 months, your child's age group. Its aim is to help your child learn words for the things you do every day."
}
```
