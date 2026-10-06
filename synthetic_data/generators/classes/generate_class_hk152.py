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


SEMESTER = "HK152"
K13_COURSES = [
    "SP1039", "CO2001", "CO3005", "CO3335",
]
K13_PROJECT_OPTIONS = ["CO3107", "CO3109", "CO3111"]
K14_COURSES = curriculum_courses("HK4")
K15_COURSES = curriculum_courses("HK2")
K14_EXTRA_COURSES = [
    code for code in additional_courses("HK4") if code not in K14_COURSES
]
K15_EXTRA_COURSES = [
    code for code in additional_courses("HK2") if code not in K15_COURSES
]
MANAGEMENT = management_elective_courses("HK4")
FREE = free_elective_courses("HK4")
GROUP_C = group_c_elective_courses("HK5")
COURSE_ORDER = list(dict.fromkeys(
    K13_COURSES + K13_PROJECT_OPTIONS + MANAGEMENT
    + K14_COURSES + K14_EXTRA_COURSES
    + K15_COURSES + K15_EXTRA_COURSES
    + FREE + GROUP_C
))

students = load_student_profiles()
lecturers = pd.read_csv(ROOT_DIR / "data" / "people" / "lecturer_for_class.csv")
history = load_history(("hk131", "hk132", "hk141", "hk142", "hk151"))
prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
course_names, course_credits, _ = course_catalog()

eligibility, _ = calculate_eligibility_for_schedule(
    students,
    history,
    course_credits,
    prerequisites,
    {"13": K13_COURSES, "14": K14_COURSES, "15": K15_COURSES},
    {
        "14": K14_EXTRA_COURSES,
        "15": K15_EXTRA_COURSES,
    },
    {
        "13": {"MANAGEMENT": MANAGEMENT},
        "14": {"MANAGEMENT": MANAGEMENT},
        "15": {"MANAGEMENT": MANAGEMENT},
    },
    {
        "13": {"FREE": FREE, "GROUP_C": GROUP_C},
        "14": {"FREE": FREE, "GROUP_C": GROUP_C},
        "15": {"FREE": FREE, "GROUP_C": GROUP_C},
    },
    {"13": {"MANAGEMENT": 3}},
    {"13": {"INTERDISCIPLINARY_PROJECT": K13_PROJECT_OPTIONS}},
    semester_code=SEMESTER,
)

COURSE_ORDER = list(dict.fromkeys(
    COURSE_ORDER + [
        code for selected in eligibility.values() for code in selected
    ]
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

output = ROOT_DIR / "generated" / "classes" / "class_hk152.csv"
pd.DataFrame(class_data).to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(class_data)} classes")
print(f"Maximum credits per student: {MAX_CREDITS}")
