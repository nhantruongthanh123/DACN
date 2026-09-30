import hashlib

import numpy as np
import pandas as pd
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "rules"))

from academic_rules import (
    calculate_eligibility_for_schedule,
    load_history,
)
from curriculum_rules import additional_courses, course_catalog, curriculum_courses


students = pd.read_csv(ROOT_DIR / "data" / "people" / "student_base_score.csv", dtype={"student_id": str})
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
for course_code in course_order:
    course_students = [
        student_id
        for student_id, courses in eligibility.items()
        if course_code in courses
    ]
    if not course_students:
        continue
    course_classes = classes[classes["course_code"] == course_code]["class_id"].tolist()
    seed = int(hashlib.sha256(course_code.encode()).hexdigest()[:8], 16)
    shuffled = np.random.default_rng(seed).permutation(course_students)
    index_chunks = np.array_split(shuffled, len(course_classes))

    for class_id, student_chunk in zip(course_classes, index_chunks):
        for student_id in student_chunk:
            student = students_by_id.loc[student_id]
            retake = course_code in failed.get(student_id, set())
            boost = np.random.default_rng(
                int(hashlib.sha256(f"{student_id}:{course_code}".encode()).hexdigest()[:8], 16)
            ).uniform(1.0, 1.8) if retake else 0.0
            difficulty = difficulties.get(course_code, 0.0)
            row = {
                "enrollment_id": enrollment_id,
                "student_id": student_id,
                "class_id": class_id,
            }
            final_score = 0.0
            for component, weight in components.get(course_code, [("cuoi_ky", 1.0)]):
                rng = np.random.default_rng(
                    int(hashlib.sha256(f"{student_id}:{course_code}:{component}".encode()).hexdigest()[:8], 16)
                )
                dynamic_difficulty = difficulty + rng.uniform(0, 0.3)
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
components_in_result = [c for c in result.columns if c not in base + end]
result = result[base + components_in_result + end]
output = ROOT_DIR / "generated" / "enrollments" / "enrollment_hk241.csv"
result.to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(result)} enrollment records")
