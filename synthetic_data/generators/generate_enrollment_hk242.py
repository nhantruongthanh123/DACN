import hashlib

import numpy as np
import pandas as pd
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "rules"))

from academic_rules import (
    MAX_CREDITS,
    calculate_eligibility_for_schedule,
    load_history,
)
from curriculum_rules import (
    additional_courses,
    course_catalog,
    curriculum_courses,
    management_elective_courses,
    free_elective_courses,
)


SEMESTER = "HK242"
K23_COURSES = curriculum_courses("HK4")
K23_EXTRA_COURSES = [
    code for code in additional_courses("HK4") if code not in K23_COURSES
]
K24_COURSES = curriculum_courses("HK2")
K24_EXTRA_COURSES = [
    code for code in additional_courses("HK2") if code not in K24_COURSES
]
COURSE_ORDER = list(dict.fromkeys(
    K23_COURSES
    + K23_EXTRA_COURSES
    + management_elective_courses("HK4")
    + free_elective_courses("HK4")
    + K24_COURSES
    + K24_EXTRA_COURSES
))

students = pd.read_csv(ROOT_DIR / "data" / "people" / "student_base_score.csv", dtype={"student_id": str})
classes = pd.read_csv(ROOT_DIR / "generated" / "classes" / "class_hk242.csv")
prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
assessment = pd.read_csv(ROOT_DIR / "data" / "catalog" / "assessment.csv")
history = load_history(("hk231", "hk232", "hk241"))
course_names, course_credits, difficulties = course_catalog()

missing = [code for code in COURSE_ORDER if code not in course_names]
if missing:
    raise ValueError("Courses missing from course.csv: " + ", ".join(missing))

eligibility, failed = calculate_eligibility_for_schedule(
    students,
    history,
    course_credits,
    prerequisites,
    {"231": K23_COURSES, "241": K24_COURSES},
    {"231": K23_EXTRA_COURSES, "241": K24_EXTRA_COURSES},
    {"231": {"MANAGEMENT": management_elective_courses("HK4")}},
    {"231": {"FREE": free_elective_courses("HK4")}},
)

components = {}
for item in assessment.itertuples(index=False):
    weights = []
    for name in ("quiz", "lab", "btl", "giua_ky", "cuoi_ky"):
        weight = getattr(item, name, 0)
        if pd.notna(weight) and float(weight) > 0:
            weights.append((name, float(weight) / 100))
    components[item.course_id] = weights or [("cuoi_ky", 1.0)]

students_by_id = students.set_index("student_id")
records = []
enrollment_id = 1

for course_code in classes["course_code"].drop_duplicates():
    student_ids = [
        student_id
        for student_id, selected_courses in eligibility.items()
        if course_code in selected_courses
    ]
    class_ids = classes.loc[
        classes["course_code"] == course_code, "class_id"
    ].tolist()
    if not student_ids or not class_ids:
        continue

    seed = int(hashlib.sha256(f"{SEMESTER}:{course_code}".encode()).hexdigest()[:8], 16)
    shuffled = np.random.default_rng(seed).permutation(student_ids)
    chunks = np.array_split(shuffled, len(class_ids))

    for class_id, student_chunk in zip(class_ids, chunks):
        for student_id in student_chunk:
            student = students_by_id.loc[student_id]
            retake = course_code in failed.get(student_id, set())
            score_seed = int(hashlib.sha256(
                f"{SEMESTER}:{student_id}:{course_code}".encode()
            ).hexdigest()[:8], 16)
            rng = np.random.default_rng(score_seed)
            effort_boost = rng.uniform(1.0, 1.8) if retake else 0.0
            record = {
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
                    + effort_boost
                    + rng.normal(0, 1.2),
                    0,
                    10,
                )
                record[component] = round(float(score), 1)
                final_score += record[component] * weight
            record["final_score"] = round(final_score, 1)
            record["status"] = "Pass" if record["final_score"] >= 5 else "Fail"
            records.append(record)
            enrollment_id += 1

result = pd.DataFrame(records)
base_columns = ["enrollment_id", "student_id", "class_id"]
end_columns = ["final_score", "status"]
component_columns = [
    column for column in result.columns
    if column not in base_columns + end_columns
]
result = result[base_columns + component_columns + end_columns]

output = ROOT_DIR / "generated" / "enrollments" / "enrollment_hk242.csv"
result.to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(result)} enrollment records")
print(f"Maximum credits per student: {MAX_CREDITS}")
