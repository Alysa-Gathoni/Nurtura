"""Validate and clean raw developmental-activity CSV batches.

Usage:
    python clean_activities.py <input_csv> [<input_csv> ...] <output_csv>

Input paths may contain wildcards (e.g. ../raw/activities_batch*.csv); they are
expanded here so the same command works in PowerShell. Rows from every input
are validated together (duplicates are detected across batches) and the valid
rows are written to <output_csv>. Each row is checked independently; invalid
rows are reported and skipped.

Exit code: 0 if every row is valid, 1 if any row was rejected, 2 on usage or
file errors.
"""

import csv
import glob
import re
import sys
from urllib.parse import urlparse

REQUIRED_COLUMNS = [
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
# Optional in the raw batches; always written to the output.
OPTIONAL_COLUMNS = {
    "content_status": "Draft",
    "source_url": "",
}
OUTPUT_COLUMNS = REQUIRED_COLUMNS + list(OPTIONAL_COLUMNS)

ACTIVITY_ID_PATTERN = re.compile(r"^ACT-\d{4}$")

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
CONTENT_STATUSES = ["Draft", "Under Review", "Published"]

# Columns restricted to a controlled vocabulary.
VOCABULARIES = {
    "developmental_domain": DOMAINS,
    "recommended_age_range": AGE_RANGES,
    "difficulty_level": DIFFICULTIES,
    "source": SOURCES,
    "content_status": CONTENT_STATUSES,
}


def normalize_whitespace(value):
    """Strip ends and collapse internal runs of whitespace to one space."""
    return re.sub(r"\s+", " ", value or "").strip()


def match_vocabulary(value, allowed):
    """Return the canonical spelling of value (case-insensitive), or None."""
    lookup = {v.lower(): v for v in allowed}
    return lookup.get(value.lower())


def is_valid_url(value):
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def validate_row(raw_row, header_length):
    """Return (cleaned_row, errors) for one csv.DictReader row."""
    errors = []

    # DictReader puts extra fields under the None key and fills missing ones with None.
    if None in raw_row:
        errors.append(
            f"too many fields ({header_length + len(raw_row[None])}, expected "
            f"{header_length}) - check for an unquoted comma"
        )
    if any(raw_row.get(col) is None for col in raw_row if col is not None):
        errors.append(f"too few fields (expected {header_length})")

    row = {col: normalize_whitespace(raw_row.get(col)) for col in REQUIRED_COLUMNS}
    for col, default in OPTIONAL_COLUMNS.items():
        row[col] = normalize_whitespace(raw_row.get(col)) or default

    missing = [col for col in REQUIRED_COLUMNS if not row[col]]
    if missing:
        errors.append(f"missing required field(s): {', '.join(missing)}")

    if row["activity_id"] and not ACTIVITY_ID_PATTERN.match(row["activity_id"]):
        errors.append(
            f"invalid activity_id '{row['activity_id']}' (expected format ACT-0000)"
        )

    for col, allowed in VOCABULARIES.items():
        if not row[col]:
            continue  # already reported as missing
        canonical = match_vocabulary(row[col], allowed)
        if canonical is None:
            errors.append(f"invalid {col} '{row[col]}' (allowed: {', '.join(allowed)})")
        else:
            row[col] = canonical

    if row["source_url"] and not is_valid_url(row["source_url"]):
        errors.append(
            f"invalid source_url '{row['source_url']}' (must start with http:// or https://)"
        )

    return row, errors


def expand_inputs(patterns):
    """Expand wildcard patterns; keep plain paths as given so missing files are reported."""
    paths = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern)) if glob.has_magic(pattern) else [pattern]
        if not matches:
            print(f"[ERROR] No files match '{pattern}'")
            return None
        paths.extend(m for m in matches if m not in paths)
    return paths


def clean(input_paths, output_path):
    valid_rows = []
    rejected = 0
    total = 0
    seen_ids = {}  # activity_id -> "file:line"
    seen_names = {}  # (activity_name, domain) -> "file:line"

    for input_path in input_paths:
        try:
            infile = open(input_path, newline="", encoding="utf-8-sig")
        except OSError as exc:
            print(f"[ERROR] Cannot open input file: {exc}")
            return 2

        with infile:
            reader = csv.DictReader(infile)
            header = [normalize_whitespace(h) for h in (reader.fieldnames or [])]
            missing_cols = [c for c in REQUIRED_COLUMNS if c not in header]
            if missing_cols:
                print(
                    f"[ERROR] {input_path} is missing column(s): {', '.join(missing_cols)}"
                )
                return 2
            unknown_cols = [c for c in header if c not in OUTPUT_COLUMNS]
            if unknown_cols:
                print(
                    f"[WARN] {input_path}: ignoring unknown column(s): {', '.join(unknown_cols)}"
                )
            reader.fieldnames = header
            print(f"--- {input_path} ---")

            for raw_row in reader:
                total += 1
                where = f"{input_path}:{reader.line_num}"
                row, errors = validate_row(raw_row, len(header))

                if row["activity_id"]:
                    key = row["activity_id"].lower()
                    if key in seen_ids:
                        errors.append(
                            f"duplicate activity_id '{row['activity_id']}' "
                            f"(first seen at {seen_ids[key]})"
                        )
                    else:
                        seen_ids[key] = where

                if row["activity_name"] and row["developmental_domain"]:
                    key = (
                        row["activity_name"].lower(),
                        row["developmental_domain"].lower(),
                    )
                    if key in seen_names:
                        errors.append(
                            f"duplicate activity '{row['activity_name']}' in domain "
                            f"'{row['developmental_domain']}' (first seen at {seen_names[key]})"
                        )
                    else:
                        seen_names[key] = where

                label = row["activity_id"] or "<no id>"
                if errors:
                    rejected += 1
                    print(f"[REJECTED] line {reader.line_num} ({label}):")
                    for err in errors:
                        print(f"    - {err}")
                else:
                    valid_rows.append(row)
                    print(
                        f"[OK] line {reader.line_num} ({label}) {row['activity_name']}"
                    )

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            writer.writerows(valid_rows)
    except OSError as exc:
        print(f"[ERROR] Cannot write output file: {exc}")
        return 2

    print()
    print(
        f"Summary: {len(valid_rows)}/{total} rows valid, {rejected} rejected "
        f"({len(input_paths)} file{'s' if len(input_paths) != 1 else ''})."
    )
    print(f"Wrote {len(valid_rows)} rows to {output_path}")
    return 0 if rejected == 0 else 1


def main(argv):
    if len(argv) < 3:
        print(
            "Usage: python clean_activities.py <input_csv> [<input_csv> ...] <output_csv>"
        )
        return 2
    input_paths = expand_inputs(argv[1:-1])
    if input_paths is None:
        return 2
    return clean(input_paths, argv[-1])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
