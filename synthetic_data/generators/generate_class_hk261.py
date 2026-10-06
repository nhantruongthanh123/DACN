import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
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
    get_department,
)


SEMESTER = "HK261"
K23_COURSES = ["SP1037", "CO4029"]
K24_COURSES = curriculum_courses("HK5")
K25_COURSES = curriculum_courses("HK3")
K26_COURSES = curriculum_courses("HK1")
K24_EXTRA_COURSES = [
    code for code in additional_courses("HK5") if code not in K24_COURSES
]
K25_EXTRA_COURSES = [
    code for code in additional_courses("HK3") if code not in K25_COURSES
]
K26_EXTRA_COURSES = [
    code for code in additional_courses("HK1") if code not in K26_COURSES
]
FREE = free_elective_courses("HK7")
GROUP_C = group_c_elective_courses("HK7")
COURSE_ORDER = list(dict.fromkeys(
    K23_COURSES
    + K24_COURSES + K24_EXTRA_COURSES
    + K25_COURSES + K25_EXTRA_COURSES
    + K26_COURSES + K26_EXTRA_COURSES
    + FREE + GROUP_C
))

students = load_student_profiles()
lecturers = pd.read_csv(ROOT_DIR / "data" / "people" / "lecturer_for_class.csv")
history = load_history(("hk231", "hk232", "hk241", "hk242", "hk251", "hk252"))
prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
course_names, course_credits, _ = course_catalog()

eligibility, _ = calculate_eligibility_for_schedule(
    students,
    history,
    course_credits,
    prerequisites,
    {"231": K23_COURSES, "241": K24_COURSES, "251": K25_COURSES, "261": K26_COURSES},
    {
        "241": K24_EXTRA_COURSES,
        "251": K25_EXTRA_COURSES,
        "261": K26_EXTRA_COURSES,
    },
    {
        "231": {"FREE": FREE, "GROUP_C": GROUP_C},
        "241": {"FREE": FREE, "GROUP_C": GROUP_C},
        "251": {"FREE": FREE, "GROUP_C": GROUP_C},
        "261": {"FREE": FREE, "GROUP_C": GROUP_C},
    },
    {
        "231": {"FREE": FREE, "GROUP_C": GROUP_C},
        "241": {"FREE": FREE, "GROUP_C": GROUP_C},
        "251": {"FREE": FREE, "GROUP_C": GROUP_C},
        "261": {"FREE": FREE, "GROUP_C": GROUP_C},
    },
    {
        "231": {"FREE": 3, "GROUP_C": 6},
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

output = ROOT_DIR / "generated" / "classes" / "class_hk261.csv"
pd.DataFrame(class_data).to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(class_data)} classes")
print(f"Maximum credits per student: {MAX_CREDITS}")
