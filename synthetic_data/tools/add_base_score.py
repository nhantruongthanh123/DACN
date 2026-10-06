from pathlib import Path
import json
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "rules"))

from academic_rules import (
    GENERATOR_CONFIG,
    PROFILE_OUTPUT_DIR,
    PROFILE_OUTPUT_FILE,
    filter_students_from_2013,
    generate_student_profile,
)


students = pd.read_csv(
    ROOT_DIR / "data" / "people" / "student.csv",
    dtype={"student_id": str},
)
students = filter_students_from_2013(students)
profiles = [
    generate_student_profile(student_id, GENERATOR_CONFIG)
    for student_id in students["student_id"]
]

result = students[["student_id", "name"]].copy()
profile_fields = profiles[0].keys() if profiles else ()
for field in profile_fields:
    values = [profile[field] for profile in profiles]
    if values and isinstance(values[0], (list, dict)):
        values = [json.dumps(value, separators=(",", ":")) for value in values]
    result[field] = values
result["base_score"] = [
    GENERATOR_CONFIG["academic"]["base_scores"][profile["academic_level"] - 1]
    for profile in profiles
]

PROFILE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
result.to_csv(PROFILE_OUTPUT_FILE, index=False, encoding="utf-8-sig")

print(f"Generated student profiles: {PROFILE_OUTPUT_FILE}")
print(f"Eligible real students: {len(result)} (cohort prefix >= 13)")
print("academic_level distribution:")
if "academic_level" in result:
    print(result["academic_level"].value_counts(normalize=True).sort_index().round(3))
else:
    print("No eligible students in the source data.")
