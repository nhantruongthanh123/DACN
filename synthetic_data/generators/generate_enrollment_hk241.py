import hashlib

import numpy as np
import pandas as pd
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
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
from curriculum_rules import additional_courses, course_catalog, curriculum_courses


SEMESTER = "HK241"

students = load_student_profiles()
course_names, course_credits, difficulties = course_catalog()
history = load_history(("hk231", "hk232"))
prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
course_k23 = curriculum_courses("HK3")
course_k23_extra = [
    code for code in additional_courses("HK3") if code not in course_k23
]
course_k24 = curriculum_courses("HK1")
eligibility, failed = calculate_eligibility_for_schedule(
    students,
    history,
    course_credits,
    prerequisites,
    {"231": course_k23, "241": course_k24},
    {"231": course_k23_extra},
    semester_code=SEMESTER,
)
classes = pd.read_csv(ROOT_DIR / "generated" / "classes" / "class_hk241.csv")
assessment = pd.read_csv(ROOT_DIR / "data" / "catalog" / "assessment.csv")

components = {}
for row in assessment.itertuples(index=False):
    weights = []
    for name in ("quiz", "lab", "btl", "giua_ky", "cuoi_ky"):
        weight = getattr(row, name, 0)
        if pd.notna(weight) and float(weight) > 0:
            weights.append((name, float(weight) / 100))
    components[row.course_id] = weights or [("cuoi_ky", 1.0)]

# `load_history()` đã ghép sẵn enrollment với class và cung cấp
# `course_code`, nên không merge lại để tránh tạo course_code_x/course_code_y.
students_by_id = students.set_index("student_id")
records = []
enrollment_id = 1

course_order = list(dict.fromkeys(
    course_k23 + course_k23_extra + course_k24
    + [code for selected in eligibility.values() for code in selected]
))
students_by_course = students_by_course_from_eligibility(eligibility)
for course_code, student_ids in students_by_course.items():
    seed = int(hashlib.sha256(course_code.encode()).hexdigest()[:8], 16)
    students_by_course[course_code] = np.random.default_rng(seed).permutation(
        student_ids
    ).tolist()
course_rosters = allocate_course_rosters(students_by_course, classes)

for course_code in course_order:
    for class_id, student_chunk in course_rosters.get(course_code, []):
        for student_id in student_chunk:
            student = students_by_id.loc[student_id]
            retake = course_code in failed.get(student_id, set())
            difficulty = difficulties.get(course_code, 0.0)
            row = {
                "enrollment_id": enrollment_id,
                "student_id": student_id,
                "class_id": class_id,
                "course_id": course_code,
                "semester": semester_index("HK241"),
                "retaken": retake,
            }
            rng = np.random.default_rng(
                int(hashlib.sha256(
                    f"{student_id}:{course_code}".encode()
                ).hexdigest()[:8], 16)
            )
            component_scores, final_score, letter, gpa = score_course_components(
                student,
                course_code,
                components.get(course_code, [("cuoi_ky", 1.0)]),
                difficulty,
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
components_in_result = [c for c in result.columns if c not in base + end]
result = result[base + components_in_result + end]
output = ROOT_DIR / "generated" / "enrollments" / "enrollment_hk241.csv"
result.to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(result)} enrollment records")
