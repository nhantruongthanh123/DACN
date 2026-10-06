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
    additional_courses,
    course_catalog,
    curriculum_courses,
    get_department,
)


SEMESTER = "HK232"
CURRICULUM_SEMESTER = "HK2"
students = load_student_profiles()
lecturers = pd.read_csv(ROOT_DIR / "data" / "people" / "lecturer_for_class.csv")
student_ids = students.loc[
    students["student_id"].str.startswith("23"), "student_id"
].tolist()
course_names, course_credits, _ = course_catalog()
standard_courses = curriculum_courses(CURRICULUM_SEMESTER)
extra_courses = [
    code for code in additional_courses(CURRICULUM_SEMESTER)
    if code not in standard_courses
]
history = load_history(("hk231",))
prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
eligibility, _ = calculate_eligibility_for_schedule(
    students,
    history,
    course_credits,
    prerequisites,
    {"231": standard_courses},
    {"231": extra_courses},
    semester_code=SEMESTER,
)

id_to_name = dict(zip(lecturers["lecturer_id"], lecturers["lecturer_name"]))
class_data = []
course_codes = list(dict.fromkeys(
    standard_courses
    + extra_courses
    + [code for selected in eligibility.values() for code in selected]
))
for course_code in course_codes:
    demand = sum(course_code in selected for selected in eligibility.values())
    if not demand:
        continue
    lecturer_ids = lecturers.loc[
        lecturers["departments"] == get_department(course_code), "lecturer_id"
    ].tolist() or ["UNKNOWN"]
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

output = ROOT_DIR / "generated" / "classes" / "class_hk232.csv"
pd.DataFrame(class_data).to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(class_data)} classes")
