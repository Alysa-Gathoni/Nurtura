# Workflow transcript (fictional caregiver)

> Generated 2026-11-16T11:43:23+03:00 at commit `87b0f45` by `backend\venv\Scripts\python.exe scripts\report_evidence\workflow_transcript.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

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
| 8 | Record "Waves bye-bye" as Not yet | `POST /api/children/1321/milestones/` | 201 |
| 9 | Generate recommendations | `POST /api/children/1321/recommendations/` | 201 |
| 10 | Read the stored batch | `GET /api/children/1321/recommendations/` | 200 |
| 11 | Mark the first idea done | `PUT /api/recommendations/1462/completion/` | 201 |
| 12 | Give feedback | `PUT /api/recommendations/1462/feedback/` | 201 |

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
  "id": 1462,
  "child": 1321,
  "activity": 1232,
  "batch": "ca9ad399-b6a1-4dd2-b5be-41e38754f082",
  "position": 1,
  "similarity_score": 0.5690974593162537,
  "ranking_score": 0.9543408355729415,
  "rule_priority": 1.0,
  "age_weight": 1.0,
  "alpha": 0.7,
  "profile_fingerprint": "a7b0de375ad1c0bd72722fb2256c6561fb6a6f1d8becbf316ebf092b1721eee1",
  "ranking_version": "da4d8bcfc4b96aa8275ddf6d450433ff66df8c6786952221e19cad800840de31",
  "pinned": false,
  "pin_note": "",
  "explanation_version": "2",
  "date_generated": "2026-11-16 08:43:23.033146+00:00",
  "activity_id": "ACT-0176",
  "explanation": "You recorded “Waves ‘bye-bye’” as not yet; most children do this by 12 months. You said you'd like support with language and communication. It's designed for children aged 12–18 months, your child's age group. Its aim is to help your child learn new words by building on the ones they say."
}
```
