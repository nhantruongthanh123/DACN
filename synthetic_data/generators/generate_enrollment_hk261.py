import hashlib

import numpy as np
import pandas as pd
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "rules"))

from academic_rules import (
    MAX_CREDITS,
    calculate_eligibility_for_schedule,
    load_history,
)
from curriculum_rules import (
    additional_courses,
    course_catalog,
    curriculum_courses,
    free_elective_courses,
    group_c_elective_courses,
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

students = pd.read_csv(ROOT_DIR / "data" / "people" / "student_base_score.csv", dtype={"student_id": str})
classes = pd.read_csv(ROOT_DIR / "generated" / "classes" / "class_hk261.csv")
assessment = pd.read_csv(ROOT_DIR / "data" / "catalog" / "assessment.csv")
prerequisites = pd.read_csv(ROOT_DIR / "data" / "catalog" / "course_prerequisite.csv")
history = load_history(("hk231", "hk232", "hk241", "hk242", "hk251", "hk252"))
course_names, course_credits, difficulties = course_catalog()

eligibility, failed = calculate_eligibility_for_schedule(
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
    {"231": {"FREE": 3, "GROUP_C": 6}},
)

components = {}
for item in assessment.itertuples(index=False):
    weights = [
        (name, float(getattr(item, name)) / 100)
        for name in ("quiz", "lab", "btl", "giua_ky", "cuoi_ky")
        if name != "cuoi_ky"
        and pd.notna(getattr(item, name))
        and float(getattr(item, name)) > 0
    ]
    components[item.course_id] = weights

students_by_id = students.set_index("student_id")
records = []
enrollment_id = 1

for course_code in classes["course_code"].drop_duplicates():
    student_ids = [
        student_id for student_id, selected in eligibility.items()
        if course_code in selected
    ]
    class_ids = classes.loc[
        classes["course_code"] == course_code, "class_id"
    ].tolist()
    if not student_ids or not class_ids:
        continue
    seed = int(hashlib.sha256(
        f"{SEMESTER}:{course_code}:roster".encode()
    ).hexdigest()[:8], 16)
    shuffled = np.random.default_rng(seed).permutation(student_ids)
    for class_id, chunk in zip(class_ids, np.array_split(shuffled, len(class_ids))):
        for student_id in chunk:
            student = students_by_id.loc[student_id]
            retake = course_code in failed.get(student_id, set())
            rng = np.random.default_rng(int(hashlib.sha256(
                f"{SEMESTER}:{student_id}:{course_code}:score".encode()
            ).hexdigest()[:8], 16))
            boost = rng.uniform(1.0, 1.8) if retake else 0.0
            record = {
                "enrollment_id": enrollment_id,
                "student_id": student_id,
                "class_id": class_id,
            }
            for component, _weight in components.get(course_code, []):
                score = np.clip(
                    float(student["base_score"])
                    + difficulties.get(course_code, 0.0)
                    + rng.uniform(0, 0.3)
                    + boost
                    + rng.normal(0, 1.2),
                    0,
                    10,
                )
                record[component] = round(float(score), 1)
            record["final_score"] = pd.NA
            record["status"] = pd.NA
            records.append(record)
            enrollment_id += 1

result = pd.DataFrame(records)
base = ["enrollment_id", "student_id", "class_id"]
end = ["final_score", "status"]
components_in_result = [c for c in result.columns if c not in base + end]
result = result[base + components_in_result + end]
output = ROOT_DIR / "generated" / "enrollments" / "enrollment_hk261.csv"
result.to_csv(output, index=False, encoding="utf-8-sig")
print(f"Created {output.name}: {len(result)} enrollment records")
print(f"Maximum credits per student: {MAX_CREDITS}")
