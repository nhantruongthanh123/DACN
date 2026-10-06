import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "rules"))

from academic_rules import (
    balanced_class_sizes,
    get_department,
    load_history,
    calculate_eligibility_for_schedule,
    load_student_profiles,
)
from curriculum_rules import (
    additional_courses,
    course_catalog,
    curriculum_courses,
)


SEMESTER = "HK141"
K13_COURSES = curriculum_courses("HK3")
K13_EXTRA_COURSES = [
    code for code in additional_courses("HK3") if code not in K13_COURSES
]
K14_COURSES = curriculum_courses("HK1")
COURSE_ORDER = list(dict.fromkeys(
    K13_COURSES + K13_EXTRA_COURSES + K14_COURSES
))

students = load_student_profiles()
lecturers = pd.read_csv(
    ROOT_DIR / "data" / "people" / "lecturer_for_class.csv"
)
history = load_history(("hk131", "hk132"))
prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
course_names, course_credits, _ = course_catalog()

eligibility, _ = calculate_eligibility_for_schedule(
    students,
    history,
    course_credits,
    prerequisites,
    {"13": K13_COURSES, "14": K14_COURSES},
    {"13": K13_EXTRA_COURSES},
    semester_code=SEMESTER,
)

course_codes = list(dict.fromkeys(
    COURSE_ORDER
    + [
        code
        for selected in eligibility.values()
        for code in selected
    ]
))
id_to_name = dict(zip(lecturers["lecturer_id"], lecturers["lecturer_name"]))
class_data = []

for course_code in course_codes:
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
        class_data.append(
            {
                "class_id": f"{SEMESTER}_{course_code}_{group}",
                "course_code": course_code,
                "course_name": course_names[course_code],
                "semester": SEMESTER,
                "class_group": group,
                "lecturer_id": lecturer_id,
                "lecturer_name": id_to_name.get(lecturer_id, "Unknown Name"),
            }
        )

output = ROOT_DIR / "generated" / "classes" / "class_hk141.csv"
pd.DataFrame(class_data).to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(class_data)} classes")
