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
    management_elective_courses,
    free_elective_courses,
    group_c_elective_courses,
    get_department,
)


SEMESTER = "HK151"
K13_COURSES = curriculum_courses("HK5")
K13_EXTRA_COURSES = [
    code for code in additional_courses("HK5") if code not in K13_COURSES
]
K14_COURSES = curriculum_courses("HK3")
K14_EXTRA_COURSES = [
    code for code in additional_courses("HK3") if code not in K14_COURSES
]
K15_COURSES = curriculum_courses("HK1")
K15_EXTRA_COURSES = [
    code for code in additional_courses("HK1") if code not in K15_COURSES
]
COURSE_ORDER = list(dict.fromkeys(
    K13_COURSES
    + K13_EXTRA_COURSES
    + management_elective_courses("HK4")
    + free_elective_courses("HK4")
    + group_c_elective_courses("HK5")
    + K14_COURSES
    + K14_EXTRA_COURSES
    + K15_COURSES
    + K15_EXTRA_COURSES
))

students = load_student_profiles()
lecturers = pd.read_csv(ROOT_DIR / "data" / "people" / "lecturer_for_class.csv")
history = load_history(("hk131", "hk132", "hk141", "hk142"))
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
        "13": K13_COURSES,
        "14": K14_COURSES,
        "15": K15_COURSES,
    },
    {
        "13": K13_EXTRA_COURSES,
        "14": K14_EXTRA_COURSES,
        "15": K15_EXTRA_COURSES,
    },
    {
        "13": {"MANAGEMENT": management_elective_courses("HK4")},
        "14": {"MANAGEMENT": management_elective_courses("HK4")},
        "15": {"MANAGEMENT": management_elective_courses("HK4")},
    },
    {
        "13": {
            "FREE": free_elective_courses("HK4"),
            "GROUP_C": group_c_elective_courses("HK5"),
        },
        "14": {
            "FREE": free_elective_courses("HK4"),
            "GROUP_C": group_c_elective_courses("HK5"),
        },
        "15": {
            "FREE": free_elective_courses("HK4"),
            "GROUP_C": group_c_elective_courses("HK5"),
        },
    },
    semester_code=SEMESTER,
)
COURSE_ORDER = list(dict.fromkeys(
    COURSE_ORDER
    + [code for selected in eligibility.values() for code in selected]
))

lecturer_names = dict(
    zip(lecturers["lecturer_id"], lecturers["lecturer_name"])
)
class_data = []

for course_code in COURSE_ORDER:
    demand = sum(
        course_code in selected_courses
        for selected_courses in eligibility.values()
    )
    if not demand:
        continue

    department = get_department(course_code)
    lecturer_ids = lecturers.loc[
        lecturers["departments"] == department,
        "lecturer_id",
    ].tolist() or ["UNKNOWN_ID"]

    for index, _ in enumerate(balanced_class_sizes(demand), start=1):
        class_group = f"L{index:02d}"
        lecturer_id = lecturer_ids[(index - 1) % len(lecturer_ids)]
        class_data.append(
            {
                "class_id": f"{SEMESTER}_{course_code}_{class_group}",
                "course_code": course_code,
                "course_name": course_names[course_code],
                "semester": SEMESTER,
                "class_group": class_group,
                "lecturer_id": lecturer_id,
                "lecturer_name": lecturer_names.get(
                    lecturer_id,
                    "Unknown Name",
                ),
            }
        )

output = ROOT_DIR / "generated" / "classes" / "class_hk151.csv"
pd.DataFrame(class_data).to_csv(
    output,
    index=False,
    encoding="utf-8-sig",
)

print(f"Created {output.name}: {len(class_data)} classes")
print(f"K13 students: {sum(s.startswith('13') for s in eligibility)}")
print(f"K14 students: {sum(s.startswith('14') for s in eligibility)}")
print(f"K15 students: {sum(s.startswith('15') for s in eligibility)}")
print(f"Credit limit per student: {MAX_CREDITS}")
