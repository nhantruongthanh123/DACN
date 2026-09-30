import math

import pandas as pd

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "rules"))
from curriculum_rules import DATA_DIR, course_catalog, curriculum_courses, get_department


SEMESTER = "HK231"
CURRICULUM_SEMESTER = "HK1"
DEFAULT_CLASS_SIZE = 120
SMALL_CLASS_SIZE = 40

students = pd.read_csv(ROOT_DIR / "data" / "people" / "student_base_score.csv", dtype={"student_id": str})
lecturers = pd.read_csv(ROOT_DIR / "data" / "people" / "lecturer_for_class.csv")
student_ids = students.loc[
    students["student_id"].str.startswith("231"), "student_id"
].tolist()
course_names, _, _ = course_catalog()
course_codes = curriculum_courses(CURRICULUM_SEMESTER)

missing = [code for code in course_codes if code not in course_names]
if missing:
    raise ValueError("Courses missing from course.csv: " + ", ".join(missing))

id_to_name = dict(zip(lecturers["lecturer_id"], lecturers["lecturer_name"]))
class_data = []

for course_code in course_codes:
    size_limit = (
        SMALL_CLASS_SIZE
        if course_code.startswith(("LA", "PH"))
        else DEFAULT_CLASS_SIZE
    )
    department = get_department(course_code)
    lecturer_ids = lecturers.loc[
        lecturers["departments"] == department, "lecturer_id"
    ].tolist() or ["UNKNOWN"]
    for index in range(1, math.ceil(len(student_ids) / size_limit) + 1):
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

output = ROOT_DIR / "generated" / "classes" / "class_hk231.csv"
pd.DataFrame(class_data).to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(class_data)} classes")
