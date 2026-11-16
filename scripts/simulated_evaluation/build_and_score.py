"""Build form-export CSVs from the simulated sessions and score them (#222).

Usage (from the repository root):
    python scripts/simulated_evaluation/build_and_score.py

Reads docs/simulated_evaluation/sessions_SIMULATED.json and
personas_SIMULATED.json, writes CSVs in the same format as the Google Forms
exports (so the real scorers read them unchanged), runs
scripts/score_caregiver_questionnaire.py and scripts/score_reader_test.py,
and saves their output next to the CSVs, with a summary of tasks B1-B5, the
relevance ratings (C1) and the explanation answers (C2).

Everything here is SIMULATED: see docs/simulated_evaluation.md.
"""

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "docs" / "simulated_evaluation"
sys.path.insert(0, str(ROOT / "scripts"))

from score_reader_test import CARE_QUESTION, SEEN_QUESTION  # noqa: E402

SUS_TITLES = [
    "SUS01: I think that I would like to use this app frequently.",
    "SUS02: I found the app unnecessarily complex.",
    "SUS03: I thought the app was easy to use.",
    "SUS04: I think that I would need the support of a technical person to be able to use this app.",
    "SUS05: I found the various functions in this app were well integrated.",
    "SUS06: I thought there was too much inconsistency in this app.",
    "SUS07: I would imagine that most people would learn to use this app very quickly.",
    "SUS08: I found the app very awkward to use.",
    "SUS09: I felt very confident using the app.",
    "SUS10: I needed to learn a lot of things before I could get going with this app.",
]
S_TITLES = [
    "S1: I trust the activities the app suggested for my child.",
    "S2: The suggested activities would be useful for my child.",
    'S3: The "Why this?" explanations helped me understand why each activity was suggested.',
    "S4: I could do the suggested activities at home with things I already have.",
    "S5: I would keep using this app with my child.",
    "S6: I would recommend this app to another parent or carer.",
]
O_TITLES = ["O1: What did you like most about the app?", "O2: What would you change?"]
PARTICIPANT = "Participant number (the researcher will tell you, for example P03)"
STAMP = "2026/11/16 12:00:00 PM EAT"


def write(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def run(cmd):
    out = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    return (out.stdout + out.stderr).strip()


def main():
    data = json.loads((DIR / "sessions_SIMULATED.json").read_text(encoding="utf-8"))
    personas = json.loads((DIR / "personas_SIMULATED.json").read_text(encoding="utf-8"))
    banner = "SIMULATED PARTICIPANTS: NOT REAL DATA (docs/simulated_evaluation.md)\n\n"

    # Questionnaire, in the caregiver form's export format.
    q = DIR / "questionnaire_SIMULATED.csv"
    write(
        q,
        ["Timestamp", PARTICIPANT, *SUS_TITLES, *S_TITLES, *O_TITLES],
        [
            [STAMP, r["participant"], *r["sus"], *r["s"], r["o1"], r["o2"]]
            for r in data["questionnaire"]
        ],
    )
    ids = [r["participant"] for r in data["questionnaire"]]
    scored = run(
        [
            sys.executable,
            "scripts/score_caregiver_questionnaire.py",
            str(q),
            "--participants",
            *ids,
        ]
    )
    (DIR / "questionnaire_scores_SIMULATED.txt").write_text(
        banner + scored + "\n", encoding="utf-8"
    )

    # Reader test, in the two wording-check forms' export format.
    header = [
        "Timestamp",
        CARE_QUESTION,
        SEEN_QUESTION,
        *[
            f"C{k:02d} Q{n}: {t}"
            for k in range(1, 11)
            for n, t in (
                (
                    1,
                    "In your own words, why was this activity suggested for this child?",
                ),
                (2, "Did any sentence worry or confuse you?"),
                (3, "If yes, which sentence, and why?"),
            )
        ],
    ]
    paths = []
    for form in ("A", "B"):
        rows = []
        for reader in personas["readers"]:
            if reader["form"] != form:
                continue
            answers = data["readers"][reader["id"]]
            cells = []
            for k in range(1, 11):
                concern = answers["worried"].get(str(k))
                cells += [
                    answers["q1"][k - 1],
                    "Yes (tell us below)" if concern else "No",
                    concern or "",
                ]
            rows.append([STAMP, reader["cares_for_under_5"], "No", *cells])
        path = DIR / f"reader_test_{form}_SIMULATED.csv"
        write(path, header, rows)
        paths.append(str(path))
    scored = run([sys.executable, "scripts/score_reader_test.py", *paths])
    (DIR / "reader_test_scores_SIMULATED.txt").write_text(
        banner + scored + "\n", encoding="utf-8"
    )

    # Reviewed reader marks (the scorer's marks are keyword checks to correct).
    review = data["reader_review"]["not_understood"]
    readers = [r["id"] for r in personas["readers"]]
    per_card = {
        k: sum(1 for r in readers if k not in review.get(r, [])) for k in range(1, 11)
    }
    passing = [k for k, n in per_card.items() if n / len(readers) >= 0.8]

    # Session summary.
    sessions = data["sessions"]
    tasks = {
        t: Counter(s["tasks"][t]["result"] for s in sessions)
        for t in ("B1", "B2", "B3", "B4", "B5")
    }
    grades = [g for s in sessions for g in s["c1"]]
    summary = {
        "notice": data["notice"],
        "tasks": {
            t: {
                **dict(c),
                "median_minutes": median(
                    m for s in sessions if (m := s["tasks"][t]["minutes"]) is not None
                ),
            }
            for t, c in tasks.items()
        },
        "c1_ratings": dict(Counter(grades)),
        "c1_share_at_least_1": sum(g >= 1 for g in grades) / len(grades),
        "c1_share_2": sum(g == 2 for g in grades) / len(grades),
        "c1_by_position_mean": [
            sum(s["c1"][i] for s in sessions) / len(sessions) for i in range(5)
        ],
        "c2_understood": sum(s["c2_understood"] for s in sessions),
        "c2_answered": len(sessions),
        "reader_cards_understood_reviewed": per_card,
        "reader_cards_passing_reviewed": len(passing),
    }
    (DIR / "summary_SIMULATED.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
