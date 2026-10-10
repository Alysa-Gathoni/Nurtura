"""Score the explanation reader test from the Google Forms exports (#80).

Usage (from the repository root):
    python scripts/score_reader_test.py responses_A.csv responses_B.csv

Reads the CSVs exported from "Nurtura wording check (A)" and "(B)" (or a
hand-built form with the same question titles), and prints, for you to
review:

- respondents: how many, and who is excluded (anyone who answered "Yes" to
  "Had you seen or heard about this project before today?");
- per card: the main reason from the answer key in
  docs/explanation_reader_test.md, every valid respondent's own-words answer
  with an automatic mark, how many were marked understood, and whether the
  card passes;
- every "worried or confused" answer, quoted separately;
- the overall result.

The automatic mark is a keyword check, not a judgement: an answer counts as
understood if it mentions the child's need, age or stated interest for that
card (the keywords are listed in CARD_KEYWORDS below, next to each card's
reason). Read every answer and correct the marks yourself before reporting.
This script only prints; it never edits the CSVs or any other file.

Pass rule (form version): a card passes if at least 80% of valid
respondents' answers are understood; the test passes if at least 8 of 10
cards pass and there are at least 10 valid respondents.
"""

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ANSWER_KEY_DOC = REPO / "docs" / "explanation_reader_test.md"

CARE_QUESTION = "Do you look after a child under 5 (as a parent, relative or carer)?"
SEEN_QUESTION = "Had you seen or heard about this project before today?"
WORRIED = "Yes (tell us below)"
COLUMN = re.compile(r"^C(\d{2}) Q([123]):")

CARD_PASS_SHARE = 0.8
CARDS_TO_PASS = 8
MIN_VALID = 10

# Words that show an answer gives the card's reason: the child's need, the
# child's age, or a stated interest (from the answer key's "Main reason").
AGE = (
    r"\bmonths?\b|\bmths?\b|\bmo\b|\bage\b|\baged\b|\bold\b|\bolder\b|"
    r"\byounger\b|\bage group\b|\bweeks?\b"
)
PREGNANCY = r"pregnan|expecting|\bdue\b|before (the )?birth|unborn|not (yet )?born"
CARD_KEYWORDS = {
    1: {
        "need": r"emotion|feeling|wellbeing|well-being|support|bond|social|stress|worr|anxi|mental",
        "age": PREGNANCY,
    },
    2: {"need": r"head|neck|tummy|lift"},
    3: {"need": r"smil"},
    4: {"need": r"sens", "interest": r"music|rattle"},
    5: {
        "need": r"general|nothing (in )?particular|no particular|didn.?t ask|did not ask|"
        r"no specific|any area|all.?round|on track|no concern|hasn.?t asked|not asked"
    },
    6: {"need": r"walk|step"},
    7: {"need": r"toy|play|push|car\b"},
    8: {"need": r"sens", "interest": r"textur|touch|feel"},
    9: {"need": r"wav|bye|word|talk|speak|say|language|communicat"},
    10: {"need": r"stand"},
}


@dataclass
class Respondent:
    source: str
    row: int
    timestamp: str
    cares: str
    seen: str
    answers: dict = field(default_factory=dict)  # card -> {1: text, 2: text, 3: text}

    @property
    def label(self):
        return f"{self.source} row {self.row}" + (
            f" ({self.timestamp})" if self.timestamp else ""
        )


def load_answer_key(path=ANSWER_KEY_DOC):
    """{card: main reason} from the answer key table in the reader-test doc."""
    text = Path(path).read_text(encoding="utf-8")
    section = text.split("## Answer key", 1)[1].split("\n## ", 1)[0]
    key = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0].isdigit():
            key[int(cells[0])] = cells[-1]
    if sorted(key) != list(range(1, 11)):
        raise ValueError(f"answer key should have cards 1-10, found {sorted(key)}")
    return key


def load_responses(paths):
    respondents = []
    for path in paths:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []
            for needed in (CARE_QUESTION, SEEN_QUESTION):
                if needed not in columns:
                    raise ValueError(f"{path}: missing column {needed!r}")
            for n, row in enumerate(reader, start=2):
                r = Respondent(
                    source=Path(path).name,
                    row=n,
                    timestamp=(row.get("Timestamp") or "").strip(),
                    cares=(row.get(CARE_QUESTION) or "").strip(),
                    seen=(row.get(SEEN_QUESTION) or "").strip(),
                )
                for column, value in row.items():
                    match = COLUMN.match(column or "")
                    if match:
                        card, question = int(match.group(1)), int(match.group(2))
                        r.answers.setdefault(card, {})[question] = (value or "").strip()
                respondents.append(r)
    return respondents


def mark(card, answer):
    """The keyword groups an own-words answer mentions (empty = not understood)."""
    patterns = {"age": AGE} | CARD_KEYWORDS[card]
    if card == 1:
        patterns["age"] = AGE + "|" + PREGNANCY
    return sorted(g for g, p in patterns.items() if re.search(p, answer, re.I))


def score(respondents, key):
    valid = [r for r in respondents if r.seen.lower() != "yes"]
    excluded = [r for r in respondents if r.seen.lower() == "yes"]
    cards = {}
    for card in range(1, 11):
        rows = []
        for r in valid:
            answer = r.answers.get(card, {}).get(1, "")
            groups = mark(card, answer) if answer else []
            rows.append((r, answer, groups))
        understood = sum(1 for _, _, g in rows if g)
        share = understood / len(valid) if valid else 0.0
        cards[card] = {
            "reason": key[card],
            "rows": rows,
            "understood": understood,
            "share": share,
            "passes": bool(valid) and share >= CARD_PASS_SHARE,
            "concerns": [
                (
                    r,
                    r.answers.get(card, {}).get(2, ""),
                    r.answers.get(card, {}).get(3, ""),
                )
                for r in valid
                if r.answers.get(card, {}).get(2, "") == WORRIED
                or r.answers.get(card, {}).get(3, "")
            ],
        }
    passing = sum(c["passes"] for c in cards.values())
    return {
        "valid": valid,
        "excluded": excluded,
        "cards": cards,
        "cards_passing": passing,
        "test_passes": passing >= CARDS_TO_PASS and len(valid) >= MIN_VALID,
    }


def report(result, out=sys.stdout):
    w = lambda s="": print(s, file=out)  # noqa: E731
    valid, excluded = result["valid"], result["excluded"]
    w("EXPLANATION READER TEST: AUTOMATIC MARKS FOR REVIEW (nothing is saved)")
    w()
    w(
        f"Respondents: {len(valid) + len(excluded)}; valid: {len(valid)}; "
        f"excluded (had seen the project): {len(excluded)}"
    )
    for r in excluded:
        w(f"  excluded: {r.label}")
    cares = sum(r.cares.lower() == "yes" for r in valid)
    w(f"Valid respondents who look after a child under 5: {cares} of {len(valid)}")
    for card, c in result["cards"].items():
        w()
        w(
            f"=== Card {card}: {c['understood']}/{len(valid)} understood "
            f"({c['share']:.0%}) -> {'PASS' if c['passes'] else 'not passing'} (auto)"
        )
        w(f"    Main reason (answer key): {c['reason']}")
        for r, answer, groups in c["rows"]:
            flag = f"understood: {', '.join(groups)}" if groups else "NOT understood"
            w(f"    [{flag}] {r.label}: {answer or '(no answer)'}")
    w()
    w("=== Worried or confused (quoted as given)")
    any_concern = False
    for card, c in result["cards"].items():
        for r, q2, q3 in c["concerns"]:
            any_concern = True
            w(
                f"  Card {card}, {r.label}: Q2 = {q2 or '(blank)'}; Q3 = {q3 or '(blank)'}"
            )
    if not any_concern:
        w("  none")
    w()
    w(
        f"Cards passing (auto): {result['cards_passing']} of 10 (needs {CARDS_TO_PASS}); "
        f"valid respondents: {len(valid)} (needs {MIN_VALID})"
    )
    w(
        f"TEST {'PASSES' if result['test_passes'] else 'DOES NOT PASS'} on the automatic "
        "marks. Review every answer above and correct the marks before reporting."
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "csv", nargs="+", type=Path, help="exported responses (A and B)"
    )
    parser.add_argument("--answer-key", type=Path, default=ANSWER_KEY_DOC)
    args = parser.parse_args(argv)
    result = score(load_responses(args.csv), load_answer_key(args.answer_key))
    report(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
