import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "rules"))

from curriculum_rules import (
    MAX_CREDITS,
    additional_courses,
    course_catalog,
    curriculum_courses,
    management_elective_courses,
    free_elective_courses,
    get_department,
)
from academic_rules import (
    balanced_class_sizes,
    calculate_eligibility_for_schedule,
    load_history,
    load_student_profiles,
)


SEMESTER = "HK242"
K23_COURSES = list(dict.fromkeys(
    curriculum_courses("HK4")
))
K23_EXTRA_COURSES = [
    code for code in additional_courses("HK4") if code not in K23_COURSES
]
K24_COURSES = list(dict.fromkeys(
    curriculum_courses("HK2")
))
K24_EXTRA_COURSES = [
    code for code in additional_courses("HK2") if code not in K24_COURSES
]
COURSE_ORDER = list(dict.fromkeys(
    K23_COURSES
    + K23_EXTRA_COURSES
    + management_elective_courses("HK4")
    + free_elective_courses("HK4")
    + K24_COURSES
    + K24_EXTRA_COURSES
))
students = load_student_profiles()
lecturers = pd.read_csv(ROOT_DIR / "data" / "people" / "lecturer_for_class.csv")
history = load_history(("hk231", "hk232", "hk241"))
course_names, course_credits, _ = course_catalog()
missing = [code for code in COURSE_ORDER if code not in course_names]
if missing:
    raise ValueError("Courses missing from course.csv: " + ", ".join(missing))

prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
eligibility, _ = calculate_eligibility_for_schedule(
    students,
    history,
    course_credits,
    prerequisites,
    {"231": K23_COURSES, "241": K24_COURSES},
    {"231": K23_EXTRA_COURSES, "241": K24_EXTRA_COURSES},
    {"231": {"MANAGEMENT": management_elective_courses("HK4")}},
    {"231": {"FREE": free_elective_courses("HK4")}},
    semester_code=SEMESTER,
)
COURSE_ORDER = list(dict.fromkeys(
    COURSE_ORDER
    + [code for selected in eligibility.values() for code in selected]
))

id_to_name = dict(zip(lecturers["lecturer_id"], lecturers["lecturer_name"]))
class_data = []
for course_code in COURSE_ORDER:
    demand = sum(course_code in courses for courses in eligibility.values())
    if not demand:
        continue
    lecturer_ids = lecturers.loc[
        lecturers["departments"] == get_department(course_code), "lecturer_id"
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

output = ROOT_DIR / "generated" / "classes" / "class_hk242.csv"
pd.DataFrame(class_data).to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(class_data)} classes")
print(f"K23 students: {sum(s.startswith('23') for s in eligibility)}")
print(f"K24 students: {sum(s.startswith('24') for s in eligibility)}")
print(f"Credit limit per student: {MAX_CREDITS}")
