"""Validate and clean a raw developmental-activity CSV.

Usage:
    python clean_activities.py <input_csv> <output_csv>

Each row is checked independently; invalid rows are reported and skipped, valid
rows are written to <output_csv>. Exit code: 0 if every row is valid, 1 if any
row was rejected, 2 on usage or file errors.
"""

import csv
import re
import sys

COLUMNS = [
    "activity_id",
    "activity_name",
    "developmental_domain",
    "recommended_age_range",
    "developmental_goal",
    "required_materials",
    "difficulty_level",
    "activity_description",
    "cultural_relevance",
    "source",
]
REQUIRED = COLUMNS

DOMAINS = ["Cognitive", "Language", "Motor", "Sensory", "Socio-Emotional"]
AGE_RANGES = [
    "Prenatal",
    "0-3 months",
    "3-6 months",
    "6-12 months",
    "12-18 months",
    "18-24 months",
    "24-36 months",
]
DIFFICULTIES = ["Beginner", "Intermediate", "Advanced"]
SOURCES = ["WHO", "CDC", "UNICEF", "Montessori", "Pathways.org"]

# Columns restricted to a controlled vocabulary.
VOCABULARIES = {
    "developmental_domain": DOMAINS,
    "recommended_age_range": AGE_RANGES,
    "difficulty_level": DIFFICULTIES,
    "source": SOURCES,
}


def normalize_whitespace(value):
    """Strip ends and collapse internal runs of whitespace to one space."""
    return re.sub(r"\s+", " ", value or "").strip()


def match_vocabulary(value, allowed):
    """Return the canonical spelling of value (case-insensitive), or None."""
    lookup = {v.lower(): v for v in allowed}
    return lookup.get(value.lower())


def validate_row(raw_row):
    """Return (cleaned_row, errors) for one csv.DictReader row."""
    errors = []

    # DictReader puts extra fields under the None key and fills missing ones with None.
    if None in raw_row:
        errors.append(
            f"too many fields ({len(COLUMNS) + len(raw_row[None])}, expected "
            f"{len(COLUMNS)}) - check for an unquoted comma"
        )
    if any(raw_row.get(col) is None for col in COLUMNS):
        errors.append(f"too few fields (expected {len(COLUMNS)})")

    row = {col: normalize_whitespace(raw_row.get(col)) for col in COLUMNS}

    missing = [col for col in REQUIRED if not row[col]]
    if missing:
        errors.append(f"missing required field(s): {', '.join(missing)}")

    for col, allowed in VOCABULARIES.items():
        if not row[col]:
            continue  # already reported as missing
        canonical = match_vocabulary(row[col], allowed)
        if canonical is None:
            errors.append(f"invalid {col} '{row[col]}' (allowed: {', '.join(allowed)})")
        else:
            row[col] = canonical

    return row, errors


def clean(input_path, output_path):
    try:
        infile = open(input_path, newline="", encoding="utf-8-sig")
    except OSError as exc:
        print(f"[ERROR] Cannot open input file: {exc}")
        return 2

    with infile:
        reader = csv.DictReader(infile)
        header = [normalize_whitespace(h) for h in (reader.fieldnames or [])]
        missing_cols = [c for c in COLUMNS if c not in header]
        if missing_cols:
            print(f"[ERROR] Input is missing column(s): {', '.join(missing_cols)}")
            return 2
        reader.fieldnames = header

        valid_rows = []
        rejected = 0
        total = 0
        seen_ids = {}  # activity_id -> line number
        seen_names = {}  # (activity_name, domain) -> line number

        for raw_row in reader:
            total += 1
            line = reader.line_num
            row, errors = validate_row(raw_row)

            if row["activity_id"]:
                key = row["activity_id"].lower()
                if key in seen_ids:
                    errors.append(
                        f"duplicate activity_id '{row['activity_id']}' "
                        f"(first seen on line {seen_ids[key]})"
                    )
                else:
                    seen_ids[key] = line

            if row["activity_name"] and row["developmental_domain"]:
                key = (
                    row["activity_name"].lower(),
                    row["developmental_domain"].lower(),
                )
                if key in seen_names:
                    errors.append(
                        f"duplicate activity '{row['activity_name']}' in domain "
                        f"'{row['developmental_domain']}' (first seen on line {seen_names[key]})"
                    )
                else:
                    seen_names[key] = line

            label = row["activity_id"] or "<no id>"
            if errors:
                rejected += 1
                print(f"[REJECTED] line {line} ({label}):")
                for err in errors:
                    print(f"    - {err}")
            else:
                valid_rows.append(row)
                print(f"[OK] line {line} ({label}) {row['activity_name']}")

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(valid_rows)
    except OSError as exc:
        print(f"[ERROR] Cannot write output file: {exc}")
        return 2

    print()
    print(f"Summary: {len(valid_rows)}/{total} rows valid, {rejected} rejected.")
    print(f"Wrote {len(valid_rows)} rows to {output_path}")
    return 0 if rejected == 0 else 1


def main(argv):
    if len(argv) != 3:
        print("Usage: python clean_activities.py <input_csv> <output_csv>")
        return 2
    return clean(argv[1], argv[2])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
