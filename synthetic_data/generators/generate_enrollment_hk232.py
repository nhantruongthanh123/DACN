import hashlib
import math

import numpy as np
import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT_DIR / "rules"))

from academic_rules import calculate_eligibility_for_schedule, load_history
from curriculum_rules import (
    DATA_DIR,
    MAX_CREDITS,
    additional_courses,
    course_catalog,
    curriculum_courses,
)


SEMESTER = "HK232"
students = pd.read_csv(ROOT_DIR / "data" / "people" / "student_base_score.csv", dtype={"student_id": str})
classes = pd.read_csv(ROOT_DIR / "generated" / "classes" / "class_hk232.csv")
assessment = pd.read_csv(ROOT_DIR / "data" / "catalog" / "assessment.csv")
course_names, course_credits, difficulties = course_catalog()
standard_courses = curriculum_courses("HK2")
extra_courses = [
    code for code in additional_courses("HK2") if code not in standard_courses
]

history = load_history(("hk231",))
prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
eligibility, failed = calculate_eligibility_for_schedule(
    students,
    history,
    course_credits,
    prerequisites,
    {"231": standard_courses},
    {"231": extra_courses},
)

components = {}
for row in assessment.itertuples(index=False):
    weights = []
    for name in ("quiz", "lab", "btl", "giua_ky", "cuoi_ky"):
        weight = getattr(row, name, 0)
        if pd.notna(weight) and float(weight) > 0:
            weights.append((name, float(weight) / 100))
    components[row.course_id] = weights or [("cuoi_ky", 1.0)]

students_by_id = students.set_index("student_id")
records = []
enrollment_id = 1
course_codes = classes["course_code"].drop_duplicates().tolist()

for course_code in course_codes:
    student_ids = [
        student_id for student_id, selected in eligibility.items()
        if course_code in selected
    ]
    class_ids = classes.loc[
        classes["course_code"] == course_code, "class_id"
    ].tolist()
    if not student_ids or not class_ids:
        continue

    seed = int(hashlib.sha256(course_code.encode()).hexdigest()[:8], 16)
    shuffled = np.random.default_rng(seed).permutation(student_ids)
    for class_id, chunk in zip(class_ids, np.array_split(shuffled, len(class_ids))):
        for student_id in chunk:
            student = students_by_id.loc[student_id]
            retake = course_code in failed.get(student_id, set())
            rng = np.random.default_rng(
                int(hashlib.sha256(
                    f"{student_id}:{course_code}".encode()
                ).hexdigest()[:8], 16)
            )
            boost = rng.uniform(1.0, 1.8) if retake else 0.0
            row = {
                "enrollment_id": enrollment_id,
                "student_id": student_id,
                "class_id": class_id,
            }
            final_score = 0.0
            for component, weight in components.get(course_code, [("cuoi_ky", 1.0)]):
                dynamic_difficulty = difficulties.get(course_code, 0.0) + rng.uniform(0, 0.3)
                score = np.clip(
                    float(student["base_score"])
                    + dynamic_difficulty
                    + boost
                    + rng.normal(0, 1.2),
                    0,
                    10,
                )
                row[component] = round(float(score), 1)
                final_score += row[component] * weight
            row["final_score"] = round(final_score, 1)
            row["status"] = "Pass" if row["final_score"] >= 5 else "Fail"
            records.append(row)
            enrollment_id += 1

result = pd.DataFrame(records)
base = ["enrollment_id", "student_id", "class_id"]
end = ["final_score", "status"]
component_columns = [column for column in result.columns if column not in base + end]
result = result[base + component_columns + end]
output = ROOT_DIR / "generated" / "enrollments" / "enrollment_hk232.csv"
result.to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(result)} enrollment records")
