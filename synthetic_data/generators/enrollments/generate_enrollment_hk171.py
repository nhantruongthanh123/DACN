import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "rules"))

from academic_rules import (
    MAX_CREDITS,
    add_gpa_summaries,
    allocate_course_rosters,
    calculate_eligibility_for_schedule,
    load_history,
    load_student_profiles,
    score_course_components,
    semester_index,
    students_by_course_from_eligibility,
)
from curriculum_rules import (
    additional_courses,
    course_catalog,
    curriculum_courses,
    free_elective_courses,
    group_c_elective_courses,
    management_elective_courses,
)


SEMESTER = "HK171"
# K13 (HK9): ungraduated students complete missing graduation requirements / retakes
K13_COURSES = ["CO4029", "CO4337", "SP1037", "SP1007"]
# K14 (HK7): senior semester 7 courses (same as K13 in HK161)
K14_COURSES = ["SP1037", "CO4029"]
# K15 (HK5): junior semester 5 courses (same as K14 in HK161)
K15_COURSES = curriculum_courses("HK5")
# K16 (HK3): sophomore semester 3 courses (same as K15 in HK161)
K16_COURSES = curriculum_courses("HK3")
# K17 (HK1): freshman new cohort semester 1 courses (same as K16 in HK161)
K17_COURSES = curriculum_courses("HK1")

K14_EXTRA_COURSES = [
    code for code in additional_courses("HK7") if code not in K14_COURSES
]
K15_EXTRA_COURSES = [
    code for code in additional_courses("HK5") if code not in K15_COURSES
]
K16_EXTRA_COURSES = [
    code for code in additional_courses("HK3") if code not in K16_COURSES
]
K17_EXTRA_COURSES = [
    code for code in additional_courses("HK1") if code not in K17_COURSES
]

MANAGEMENT = management_elective_courses("HK6")
FREE = free_elective_courses("HK7")
GROUP_C = group_c_elective_courses("HK7")

students = load_student_profiles()
classes = pd.read_csv(ROOT_DIR / "generated" / "classes" / "class_hk171.csv")
assessment = pd.read_csv(ROOT_DIR / "data" / "catalog" / "assessment.csv")
prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
history = load_history((
    "hk131", "hk132", "hk141", "hk142", "hk151", "hk152", "hk161", "hk162"
))
course_names, course_credits, difficulties = course_catalog()

eligibility, failed = calculate_eligibility_for_schedule(
    students,
    history,
    course_credits,
    prerequisites,
    {
        "13": K13_COURSES,
        "14": K14_COURSES,
        "15": K15_COURSES,
        "16": K16_COURSES,
        "17": K17_COURSES,
    },
    {
        "14": K14_EXTRA_COURSES,
        "15": K15_EXTRA_COURSES,
        "16": K16_EXTRA_COURSES,
        "17": K17_EXTRA_COURSES,
    },
    {
        "13": {"FREE": FREE, "GROUP_C": GROUP_C, "MANAGEMENT": MANAGEMENT},
        "14": {"FREE": FREE, "GROUP_C": GROUP_C},
        "15": {"FREE": FREE, "GROUP_C": GROUP_C},
        "16": {"FREE": FREE, "GROUP_C": GROUP_C},
        "17": {"FREE": FREE, "GROUP_C": GROUP_C},
    },
    {
        "13": {"FREE": FREE, "GROUP_C": GROUP_C},
        "14": {"FREE": FREE, "GROUP_C": GROUP_C},
        "15": {"FREE": FREE, "GROUP_C": GROUP_C},
        "16": {"FREE": FREE, "GROUP_C": GROUP_C},
        "17": {"FREE": FREE, "GROUP_C": GROUP_C},
    },
    {
        "13": {"FREE": 9, "GROUP_C": 15, "MANAGEMENT": 3},
        "14": {"FREE": 3, "GROUP_C": 6},
    },
    semester_code=SEMESTER,
)

components = {}
for item in assessment.itertuples(index=False):
    weights = [
        (name, float(getattr(item, name)) / 100)
        for name in ("quiz", "lab", "btl", "giua_ky", "cuoi_ky")
        if pd.notna(getattr(item, name))
        and float(getattr(item, name)) > 0
    ]
    components[item.course_id] = weights or [("cuoi_ky", 1.0)]

students_by_id = students.set_index("student_id")
records = []
enrollment_id = 1
students_by_course = students_by_course_from_eligibility(eligibility)
for course_code, student_ids in students_by_course.items():
    seed = int(hashlib.sha256(
        f"{SEMESTER}:{course_code}:roster".encode()
    ).hexdigest()[:8], 16)
    students_by_course[course_code] = np.random.default_rng(seed).permutation(
        student_ids
    ).tolist()
course_rosters = allocate_course_rosters(students_by_course, classes)

for course_code in classes["course_code"].drop_duplicates():
    for class_id, chunk in course_rosters.get(course_code, []):
        for student_id in chunk:
            student = students_by_id.loc[student_id]
            retake = course_code in failed.get(student_id, set())
            rng = np.random.default_rng(int(hashlib.sha256(
                f"{SEMESTER}:{student_id}:{course_code}:score".encode()
            ).hexdigest()[:8], 16))
            record = {
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
            record.update(component_scores)
            record["final_score"] = final_score
            record["letter_grade"] = letter
            record["gpa_4"] = gpa
            record["passed"] = letter != "F"
            record["status"] = "Pass" if record["passed"] else "Fail"
            records.append(record)
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
output = ROOT_DIR / "generated" / "enrollments" / "enrollment_hk171.csv"
result.to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(result)} enrollment records")
print(f"Maximum credits per student: {MAX_CREDITS}")
