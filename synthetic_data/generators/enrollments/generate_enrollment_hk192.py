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


SEMESTER = "HK192"
# K13 (HK14): exceeded 12 semesters maximum duration -> all ungraduated students dismissed / dropped out
# K14 (HK12): ungraduated students complete missing graduation requirements / retakes (same as K13 in HK182)
K14_COURSES = ["CO4029", "CO4337", "SP1037", "SP1007"]
# K15 (HK10): ungraduated students complete missing graduation requirements / retakes (same as K14 in HK182 and K13 in HK172)
K15_COURSES = ["CO4029", "CO4337", "SP1037", "SP1007"]
# K16 (HK8): graduation semester (same as K15 in HK182, K14 in HK172, and K13 in HK162)
K16_COURSES = ["SP1007", "CO4337"]
# K17 (HK6): semester 6 courses (same as K16 in HK182, K15 in HK172, and K14 in HK162)
K17_COURSES = ["SP1039", "CO2001", "CO3005", "CO3335"]
K17_PROJECT_OPTIONS = ["CO3107", "CO3109", "CO3111"]
# K18 (HK4): semester 4 courses (same as K17 in HK182, K16 in HK172, and K15 in HK162)
K18_COURSES = curriculum_courses("HK4")
# K19 (HK2): semester 2 courses (same as K18 in HK182, K17 in HK172, and K16 in HK162)
K19_COURSES = curriculum_courses("HK2")

K17_EXTRA_COURSES = [
    code for code in additional_courses("HK6") if code not in K17_COURSES
]
K18_EXTRA_COURSES = [
    code for code in additional_courses("HK4") if code not in K18_COURSES
]
K19_EXTRA_COURSES = [
    code for code in additional_courses("HK2") if code not in K19_COURSES
]

MANAGEMENT = management_elective_courses("HK4")
FREE = free_elective_courses("HK8")
GROUP_C = group_c_elective_courses("HK8")

students = load_student_profiles()
classes = pd.read_csv(ROOT_DIR / "generated" / "classes" / "class_hk192.csv")
assessment = pd.read_csv(ROOT_DIR / "data" / "catalog" / "assessment.csv")
prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
history = load_history((
    "hk131", "hk132", "hk141", "hk142", "hk151", "hk152", "hk161", "hk162", "hk171", "hk172", "hk181", "hk182", "hk191"
))
course_names, course_credits, difficulties = course_catalog()

eligibility, failed = calculate_eligibility_for_schedule(
    students,
    history,
    course_credits,
    prerequisites,
    {
        "14": K14_COURSES,
        "15": K15_COURSES,
        "16": K16_COURSES,
        "17": K17_COURSES,
        "18": K18_COURSES,
        "19": K19_COURSES,
    },
    {
        "17": K17_EXTRA_COURSES,
        "18": K18_EXTRA_COURSES,
        "19": K19_EXTRA_COURSES,
    },
    {
        "14": {"GROUP_C": GROUP_C, "MANAGEMENT": MANAGEMENT, "FREE": FREE},
        "15": {"GROUP_C": GROUP_C, "MANAGEMENT": MANAGEMENT, "FREE": FREE},
        "16": {"GROUP_C": GROUP_C, "MANAGEMENT": MANAGEMENT, "FREE": FREE},
        "17": {"MANAGEMENT": MANAGEMENT},
        "18": {"MANAGEMENT": MANAGEMENT},
        "19": {"MANAGEMENT": MANAGEMENT},
    },
    {
        "14": {"FREE": FREE, "GROUP_C": GROUP_C},
        "15": {"FREE": FREE, "GROUP_C": GROUP_C},
        "16": {"FREE": FREE, "GROUP_C": GROUP_C},
        "17": {"FREE": FREE, "GROUP_C": GROUP_C},
        "18": {"FREE": FREE, "GROUP_C": GROUP_C},
        "19": {"FREE": FREE, "GROUP_C": GROUP_C},
    },
    {
        "14": {"FREE": 9, "GROUP_C": 15, "MANAGEMENT": 3},
        "15": {"FREE": 9, "GROUP_C": 15, "MANAGEMENT": 3},
        "16": {"GROUP_C": 9, "MANAGEMENT": 3},
        "17": {"MANAGEMENT": 3},
    },
    {
        "17": {"INTERDISCIPLINARY_PROJECT": K17_PROJECT_OPTIONS},
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
output = ROOT_DIR / "generated" / "enrollments" / "enrollment_hk192.csv"
result.to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(result)} enrollment records")
print(f"Maximum credits per student: {MAX_CREDITS}")
