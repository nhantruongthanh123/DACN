

import pandas as pd

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "rules"))
from academic_rules import (
    balanced_class_sizes,
    can_skip_la1003,
    load_student_profiles,
)
from curriculum_rules import course_catalog, curriculum_courses, get_department


SEMESTER = "HK131"
CURRICULUM_SEMESTER = "HK1"
students = load_student_profiles()
lecturers = pd.read_csv(ROOT_DIR / "data" / "people" / "lecturer_for_class.csv")
student_ids = students.loc[
    students["student_id"].str.startswith("13"), "student_id"
].tolist()
course_names, _, _ = course_catalog()
course_codes = curriculum_courses(CURRICULUM_SEMESTER)

missing = [code for code in course_codes if code not in course_names]
if missing:
    raise ValueError("Courses missing from course.csv: " + ", ".join(missing))

id_to_name = dict(zip(lecturers["lecturer_id"], lecturers["lecturer_name"]))
class_data = []

for course_code in course_codes:
    department = get_department(course_code)
    lecturer_ids = lecturers.loc[
        lecturers["departments"] == department, "lecturer_id"
    ].tolist() or ["UNKNOWN"]
    if course_code == "LA1003":
        course_demand = sum(
            not can_skip_la1003(student.student_id, student.base_score)
            for student in students.loc[
                students["student_id"].str.startswith("13")
            ].itertuples(index=False)
        )
    else:
        course_demand = len(student_ids)
    for index, _ in enumerate(balanced_class_sizes(course_demand), start=1):
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

output = ROOT_DIR / "generated" / "classes" / "class_hk131.csv"
pd.DataFrame(class_data).to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(class_data)} classes")
