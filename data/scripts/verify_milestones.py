"""Compare the catalogue's CDC milestones with the CDC 2022 checklists (#235).

Usage (from the repository root):
    python data/scripts/verify_milestones.py

Reads data/reference/developmental_milestones.csv and the checklist text in
data/reference/cdc_2022_checklists.json, matches every CDC entry to a
checklist item of the same age (by wording, then checks the domain), and
writes data/review/milestone_verification.csv: the catalogue wording, CDC's
wording, the page, how they differ, and a verdict. It only reads and writes
those files; marking entries verified in the database is a separate step
(the admin's "Mark selected milestones as verified").

How the wording may differ and still count as the same milestone:
- pronouns: the catalogue says "they/them" where CDC alternates he and she;
- British spelling ("colour", "trousers") and punctuation;
- CDC's example left out ("…, like taking toys out of a container …").
Anything else, a different age or a different domain is marked for review.
"""

import csv
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "data" / "reference" / "developmental_milestones.csv"
SOURCE = ROOT / "data" / "reference" / "cdc_2022_checklists.json"
OUT = ROOT / "data" / "review" / "milestone_verification.csv"

SUBS = [
    (r"\bhimself\b|\bherself\b", "themselves"),
    (r"\bhis\b|\bher\b", "their"),
    (r"\bhim\b", "them"),
    (r"\bhe\b|\bshe\b", "they"),
    (r"\bself\b", "themselves"),
    (r"\bcolor\b", "colour"),
    (r"\bpants\b", "trousers"),
    (r"/", " or "),
]
STOP = {
    "the",
    "a",
    "an",
    "to",
    "or",
    "and",
    "when",
    "you",
    "they",
    "them",
    "their",
    "up",
    "of",
}


def norm(text):
    t = text.lower()
    for a, b in (("“", '"'), ("”", '"'), ("’", "'"), ("‘", "'")):
        t = t.replace(a, b)
    for pattern, repl in SUBS:
        t = re.sub(pattern, repl, t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def words(text):
    return {w for w in norm(text).split() if w not in STOP}


def difference(catalogue, cdc):
    a, b = norm(catalogue), norm(cdc)
    if a == b:
        return "same wording (pronouns, spelling or punctuation aside)"
    if words(catalogue) <= words(cdc):
        return "same milestone, shortened (CDC's example or extra words left out)"
    return "reworded"


def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    pages = source["_pages"]
    rows, used = [], set()
    for m in csv.DictReader(CATALOGUE.open(encoding="utf-8")):
        if m["source"] != "CDC":
            continue
        age = str(int(float(m["expected_age_months"])))
        items = [(d, s) for d, ss in source.get(age, {}).items() for s in ss]
        domain, text = max(
            items,
            key=lambda i: SequenceMatcher(
                None, norm(m["description"]), norm(i[1])
            ).ratio(),
            default=("", ""),
        )
        ratio = SequenceMatcher(None, norm(m["description"]), norm(text)).ratio()
        diff = difference(m["description"], text)
        duplicate = (age, text) in used
        used.add((age, text))
        ok = (
            text
            and domain == m["domain"]
            and not duplicate
            and (diff != "reworded" or ratio >= 0.85)
        )
        rows.append(
            {
                "milestone_key": m["milestone_key"],
                "expected_age_months": m["expected_age_months"],
                "domain": m["domain"],
                "cdc_domain": domain,
                "catalogue_description": m["description"],
                "cdc_text": text,
                "cdc_page": pages.get(age, ""),
                "similarity": f"{ratio:.3f}",
                "difference": diff,
                "verdict": "matches source" if ok else "REVIEW",
            }
        )
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    total = sum(
        len(v) for k, d in source.items() if not k.startswith("_") for v in d.values()
    )
    review = [r["milestone_key"] for r in rows if r["verdict"] != "matches source"]
    print(
        f"{len(rows)} CDC entries; {total} checklist items; {len(used)} items matched"
    )
    print(f"matches source: {len(rows) - len(review)}; to review: {review or 'none'}")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
