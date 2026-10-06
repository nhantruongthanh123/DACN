import hashlib
import math
import os
import random
import tempfile
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
STUDENT_FILE = ROOT_DIR / "data" / "people" / "student.csv"
START_YEAR = 2013
END_YEAR = 2026
RANDOM_SEED = 20261006
SUFFIX_SPACE = 100_000


def allocate_cohort_counts(student_count):
    """Allocate a fixed population by rising 8.0%, 8.5%, ... relative weights."""
    if student_count < 0:
        raise ValueError("Student count cannot be negative")
    years = list(range(START_YEAR, END_YEAR + 1))
    weights = [16 + index for index in range(len(years))]
    weight_total = sum(weights)
    quotas = [student_count * weight / weight_total for weight in weights]
    counts = [math.floor(quota) for quota in quotas]
    remainder = student_count - sum(counts)
    by_fraction = sorted(
        range(len(years)),
        key=lambda index: (quotas[index] - counts[index], -index),
        reverse=True,
    )
    for index in by_fraction[:remainder]:
        counts[index] += 1
    return dict(zip(years, counts))


def generate_student_ids(year, count, seed=RANDOM_SEED):
    """Create unique YY + five-digit IDs with a full-period modulo sequence."""
    if not isinstance(year, int) or year < 0:
        raise ValueError("Year must be a non-negative integer")
    if not 0 <= count <= SUFFIX_SPACE:
        raise ValueError(f"Cohort size must be between 0 and {SUFFIX_SPACE}")
    if count == 0:
        return []

    digest = hashlib.sha256(f"{seed}:{year}".encode("ascii")).digest()
    start = int.from_bytes(digest[:8], "big") % SUFFIX_SPACE
    step = int.from_bytes(digest[8:16], "big") % SUFFIX_SPACE
    while math.gcd(step, SUFFIX_SPACE) != 1:
        step = (step + 1) % SUFFIX_SPACE

    year_prefix = f"{year % 100:02d}"
    return [
        f"{year_prefix}{(start + index * step) % SUFFIX_SPACE:05d}"
        for index in range(count)
    ]


def reassign_student_cohorts(students, seed=RANDOM_SEED):
    """Keep all student attributes except ID, email, and cohort."""
    required_columns = {"student_id", "email", "cohort"}
    missing = required_columns - set(students.columns)
    if missing:
        raise ValueError(f"Student CSV is missing columns: {', '.join(sorted(missing))}")

    result = students.copy()
    counts = allocate_cohort_counts(len(result))
    row_indexes = list(range(len(result)))
    random.Random(seed).shuffle(row_indexes)

    new_ids = [None] * len(result)
    new_cohorts = [None] * len(result)
    offset = 0
    for year, count in counts.items():
        assigned_rows = row_indexes[offset:offset + count]
        cohort_ids = generate_student_ids(year, count, seed)
        for row_index, new_id in zip(assigned_rows, cohort_ids):
            new_ids[row_index] = new_id
            new_cohorts[row_index] = f"K{year % 100:02d}"
        offset += count

    new_emails = []
    for old_id, old_email, new_id in zip(
        result["student_id"].astype(str),
        result["email"].astype(str),
        new_ids,
    ):
        local, separator, domain = old_email.partition("@")
        old_suffix = f".{old_id}"
        if not separator or not local.endswith(old_suffix):
            raise ValueError(
                f"Email must end with the current student ID: {old_email}"
            )
        new_emails.append(f"{local[:-len(old_id)]}{new_id}@{domain}")

    result["student_id"] = new_ids
    result["email"] = new_emails
    result["cohort"] = new_cohorts
    return result, counts


def write_csv_atomically(frame, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            frame.to_csv(temp_file, index=False)
        os.replace(temp_path, output_path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def main():
    students = pd.read_csv(STUDENT_FILE, dtype={"student_id": str})
    result, counts = reassign_student_cohorts(students)
    write_csv_atomically(result, STUDENT_FILE)
    print(f"Updated {STUDENT_FILE}")
    print(f"Students retained: {len(result)}")
    print("Students by cohort:")
    for year, count in counts.items():
        print(f"K{year % 100:02d}: {count}")


if __name__ == "__main__":
    main()
