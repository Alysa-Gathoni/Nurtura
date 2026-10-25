"""Score the caregiver questionnaire from the Google Forms export (#132).

Usage (from the repository root):
    python scripts/score_caregiver_questionnaire.py responses.csv
    python scripts/score_caregiver_questionnaire.py responses.csv --participants P01 P02 P03

Reads the CSV exported from "Nurtura app questionnaire" (built by
scripts/caregiver_questionnaire_form.gs), finding the columns by their
SUSnn / Sn / On prefixes, and prints:

- each response's SUS score (Brooke, 1996): odd items score the response
  minus 1, even items 5 minus the response; the sum times 2.5 gives 0-100.
  A response with a blank or out-of-range item is reported as incomplete and
  left out of the mean;
- the mean, lowest and highest SUS score over complete responses;
- each satisfaction item's median and how many chose each answer;
- every open answer, quoted as given;
- warnings: a participant number given more than once, and, with
  --participants, any number not in the list or any listed number with no
  response. Decide yourself which response to keep.

Small numbers: report counts and ranges, not significance tests.
This script only prints; it never edits the CSV or any other file.
"""

import argparse
import csv
import re
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

PARTICIPANT_PREFIX = "Participant number"
SUS = re.compile(r"^SUS(\d{2}):")
SATISFACTION = re.compile(r"^S(\d):")
OPEN = re.compile(r"^O(\d):")
SUS_ITEMS = 10
SATISFACTION_ITEMS = 6
SCALE = range(1, 6)


@dataclass
class Response:
    row: int
    participant: str
    sus: list = field(default_factory=list)  # 10 values, None if blank or invalid
    satisfaction: dict = field(default_factory=dict)  # "S1" -> int or None
    open: dict = field(default_factory=dict)  # "O1" -> text


def _scale_value(raw):
    try:
        value = int((raw or "").strip())
    except ValueError:
        return None
    return value if value in SCALE else None


def _columns(fieldnames):
    participant = [c for c in fieldnames if c.startswith(PARTICIPANT_PREFIX)]
    sus = sorted((int(m.group(1)), c) for c in fieldnames if (m := SUS.match(c)))
    sat = sorted(
        (int(m.group(1)), c) for c in fieldnames if (m := SATISFACTION.match(c))
    )
    opens = sorted((int(m.group(1)), c) for c in fieldnames if (m := OPEN.match(c)))
    if len(participant) != 1:
        raise ValueError(
            f"expected one {PARTICIPANT_PREFIX!r} column, found {len(participant)}"
        )
    if [n for n, _ in sus] != list(range(1, SUS_ITEMS + 1)):
        raise ValueError(f"expected SUS01-SUS10 columns, found {[c for _, c in sus]}")
    if [n for n, _ in sat] != list(range(1, SATISFACTION_ITEMS + 1)):
        raise ValueError(f"expected S1-S6 columns, found {[c for _, c in sat]}")
    return (
        participant[0],
        [c for _, c in sus],
        [c for _, c in sat],
        [c for _, c in opens],
    )


def load_responses(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        participant, sus, sat, opens = _columns(reader.fieldnames or [])
        responses = []
        for n, row in enumerate(reader, start=2):
            responses.append(
                Response(
                    row=n,
                    participant=(row.get(participant) or "").strip().upper(),
                    sus=[_scale_value(row.get(c)) for c in sus],
                    satisfaction={
                        c.split(":")[0]: _scale_value(row.get(c)) for c in sat
                    },
                    open={c.split(":")[0]: (row.get(c) or "").strip() for c in opens},
                )
            )
    return responses


def sus_score(values):
    """The 0-100 SUS score for 10 responses (1-5), or None if any is missing."""
    if len(values) != SUS_ITEMS or any(v is None for v in values):
        return None
    total = sum(v - 1 if i % 2 == 0 else 5 - v for i, v in enumerate(values))
    return total * 2.5


def score(responses, expected=None):
    scored = [(r, sus_score(r.sus)) for r in responses]
    complete = [s for _, s in scored if s is not None]
    counts = Counter(r.participant for r in responses)
    satisfaction = {}
    for k in range(1, SATISFACTION_ITEMS + 1):
        item = f"S{k}"
        values = [
            r.satisfaction[item] for r in responses if r.satisfaction[item] is not None
        ]
        satisfaction[item] = {
            "n": len(values),
            "median": statistics.median(values) if values else None,
            "counts": {v: values.count(v) for v in SCALE},
        }
    given = set(counts)
    expected = {p.strip().upper() for p in expected or []}
    return {
        "responses": scored,
        "sus_mean": statistics.mean(complete) if complete else None,
        "sus_min": min(complete) if complete else None,
        "sus_max": max(complete) if complete else None,
        "complete": len(complete),
        "satisfaction": satisfaction,
        "duplicates": sorted(p for p, c in counts.items() if c > 1),
        "unexpected": sorted(given - expected) if expected else [],
        "missing": sorted(expected - given),
    }


def report(result, out=sys.stdout):
    w = lambda s="": print(s, file=out)  # noqa: E731
    responses = result["responses"]
    w("CAREGIVER QUESTIONNAIRE (nothing is saved)")
    w()
    w(f"Responses: {len(responses)}; complete SUS: {result['complete']}")
    for p in result["duplicates"]:
        w(f"  WARNING: {p} appears more than once; decide which response to keep")
    for p in result["unexpected"]:
        w(f"  WARNING: {p} is not in --participants")
    for p in result["missing"]:
        w(f"  WARNING: {p} has no response")
    w()
    w("=== SUS (0-100; not a percentage)")
    for r, s in responses:
        w(
            f"  {r.participant or '(no number)'} (row {r.row}): "
            + (f"{s:g}" if s is not None else "incomplete, left out of the mean")
        )
    if result["sus_mean"] is not None:
        w(
            f"  Mean {result['sus_mean']:.1f}; lowest {result['sus_min']:g}; "
            f"highest {result['sus_max']:g} (n = {result['complete']})"
        )
    w()
    w("=== Satisfaction (1 = strongly disagree ... 5 = strongly agree)")
    for item, s in result["satisfaction"].items():
        counts = ", ".join(f"{v}: {c}" for v, c in s["counts"].items())
        median = f"{s['median']:g}" if s["median"] is not None else "-"
        w(f"  {item}: median {median} (n = {s['n']}); counts {counts}")
    w()
    w("=== Open answers (quoted as given)")
    any_answer = False
    for r, _ in responses:
        for item, text in r.open.items():
            if text:
                any_answer = True
                w(f"  {item}, {r.participant or '(no number)'}: {text}")
    if not any_answer:
        w("  none")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", type=Path, help="exported responses")
    parser.add_argument(
        "--participants",
        nargs="*",
        default=[],
        help="participant numbers from the session sheets",
    )
    args = parser.parse_args(argv)
    report(score(load_responses(args.csv), args.participants))
    return 0


if __name__ == "__main__":
    sys.exit(main())
