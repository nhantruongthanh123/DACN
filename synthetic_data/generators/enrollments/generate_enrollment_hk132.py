import hashlib

import numpy as np
import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT_DIR / "rules"))

from academic_rules import (
    add_gpa_summaries,
    allocate_course_rosters,
    calculate_eligibility_for_schedule,
    load_history,
    load_student_profiles,
    score_course_components,
    students_by_course_from_eligibility,
    semester_index,
)
from curriculum_rules import (
    MAX_CREDITS,
    additional_courses,
    course_catalog,
    curriculum_courses,
)


SEMESTER = "HK132"
students = load_student_profiles()
classes = pd.read_csv(ROOT_DIR / "generated" / "classes" / "class_hk132.csv")
assessment = pd.read_csv(ROOT_DIR / "data" / "catalog" / "assessment.csv")
course_names, course_credits, difficulties = course_catalog()
standard_courses = curriculum_courses("HK2")
extra_courses = [
    code for code in additional_courses("HK2") if code not in standard_courses
]

history = load_history(("hk131",))
prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
eligibility, failed = calculate_eligibility_for_schedule(
    students,
    history,
    course_credits,
    prerequisites,
    {"13": standard_courses},
    {"13": extra_courses},
    semester_code=SEMESTER,
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
students_by_course = students_by_course_from_eligibility(eligibility)
for course_code, student_ids in students_by_course.items():
    seed = int(hashlib.sha256(course_code.encode()).hexdigest()[:8], 16)
    students_by_course[course_code] = np.random.default_rng(seed).permutation(
        student_ids
    ).tolist()
course_rosters = allocate_course_rosters(students_by_course, classes)

for course_code in course_codes:
    for class_id, chunk in course_rosters.get(course_code, []):
        for student_id in chunk:
            student = students_by_id.loc[student_id]
            retake = course_code in failed.get(student_id, set())
            rng = np.random.default_rng(
                int(hashlib.sha256(
                    f"{student_id}:{course_code}".encode()
                ).hexdigest()[:8], 16)
            )
            row = {
                "enrollment_id": enrollment_id,
                "student_id": student_id,
                "class_id": class_id,
                "course_id": course_code,
                "semester": semester_index(SEMESTER),
                "retaken": retake,
            }
            component_scores, final_score, letter, gpa = score_course_components(
                student,
                course_code,
                components.get(course_code, [("cuoi_ky", 1.0)]),
                difficulties.get(course_code, 0.0),
                rng,
                retaken=retake,
                student_id=student_id,
            )
            row.update(component_scores)
            row["final_score"] = final_score
            row["letter_grade"] = letter
            row["gpa_4"] = gpa
            row["passed"] = letter != "F"
            row["status"] = "Pass" if row["passed"] else "Fail"
            records.append(row)
            enrollment_id += 1

result = pd.DataFrame(records)
result = add_gpa_summaries(result, history, course_credits)
base = ["enrollment_id", "student_id", "class_id", "course_id", "semester", "retaken"]
end = [
    "final_score",
    "letter_grade",
    "gpa_4",
    "passed",
    "semester_gpa_4",
    "final_gpa_4",
    "status",
]
component_columns = [column for column in result.columns if column not in base + end]
result = result[base + component_columns + end]
output = ROOT_DIR / "generated" / "enrollments" / "enrollment_hk132.csv"
result.to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(result)} enrollment records")
