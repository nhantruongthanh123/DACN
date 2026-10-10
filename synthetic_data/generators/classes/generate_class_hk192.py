import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "rules"))

from academic_rules import (
    balanced_class_sizes,
    calculate_eligibility_for_schedule,
    load_history,
    load_student_profiles,
)
from curriculum_rules import (
    MAX_CREDITS,
    additional_courses,
    course_catalog,
    curriculum_courses,
    free_elective_courses,
    group_c_elective_courses,
    management_elective_courses,
    get_department,
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

COURSE_ORDER = list(dict.fromkeys(
    K14_COURSES
    + K15_COURSES
    + K16_COURSES
    + K17_COURSES + K17_PROJECT_OPTIONS + K17_EXTRA_COURSES
    + K18_COURSES + K18_EXTRA_COURSES
    + K19_COURSES + K19_EXTRA_COURSES
    + MANAGEMENT + FREE + GROUP_C
))

students = load_student_profiles()
lecturers = pd.read_csv(ROOT_DIR / "data" / "people" / "lecturer_for_class.csv")
history = load_history((
    "hk131", "hk132", "hk141", "hk142", "hk151", "hk152", "hk161", "hk162", "hk171", "hk172", "hk181", "hk182", "hk191"
))
prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
course_names, course_credits, _ = course_catalog()

missing = [code for code in COURSE_ORDER if code not in course_names]
if missing:
    raise ValueError("Courses missing from course.csv: " + ", ".join(missing))

eligibility, _ = calculate_eligibility_for_schedule(
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

COURSE_ORDER = list(dict.fromkeys(
    COURSE_ORDER + [code for selected in eligibility.values() for code in selected]
))
lecturer_names = dict(zip(lecturers["lecturer_id"], lecturers["lecturer_name"]))
class_data = []

for course_code in COURSE_ORDER:
    demand = sum(course_code in selected for selected in eligibility.values())
    if not demand:
        continue
    lecturer_ids = lecturers.loc[
        lecturers["departments"] == get_department(course_code),
        "lecturer_id",
    ].tolist() or ["UNKNOWN_ID"]
    for index, _ in enumerate(balanced_class_sizes(demand), start=1):
        group = f"L{index:02d}"
        lecturer_id = lecturer_ids[(index - 1) % len(lecturer_ids)]
        class_data.append({
            "class_id": f"{SEMESTER}_{course_code}_{group}",
            "course_code": course_code,
            "course_name": course_names[course_code],
            "semester": SEMESTER,
            "class_group": group,
            "lecturer_id": lecturer_id,
            "lecturer_name": lecturer_names.get(lecturer_id, "Unknown Name"),
        })

output = ROOT_DIR / "generated" / "classes" / "class_hk192.csv"
pd.DataFrame(class_data).to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(class_data)} classes")
print(f"Maximum credits per student: {MAX_CREDITS}")
