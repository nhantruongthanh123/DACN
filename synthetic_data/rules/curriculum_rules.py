from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT_DIR / "data" / "catalog"
DATA_DIR = CATALOG_DIR
CURRICULUM_FILE = CATALOG_DIR / "curriculum_computer_science.csv"
RULE_FILE = CATALOG_DIR / "additional_course_rules.csv"
ELECTIVE_FILE = CATALOG_DIR / "elective_courses.csv"
MANAGEMENT_ELECTIVE_FILE = CATALOG_DIR / "management_electives.csv"
GROUP_C_ELECTIVE_FILE = CATALOG_DIR / "group_c_electives.csv"
MAX_CREDITS = 22
TUITION_BASELINE_CREDITS = 18


def load_curriculum():
    return pd.read_csv(CURRICULUM_FILE, dtype={"course_code": "string"})


def load_rules():
    return pd.read_csv(RULE_FILE, dtype={"course_code": "string"})


def load_electives():
    return pd.read_csv(ELECTIVE_FILE, dtype={"course_code": "string"})


def load_management_electives():
    return pd.read_csv(
        MANAGEMENT_ELECTIVE_FILE,
        dtype={"course_code": "string"},
    )


def load_group_c_electives():
    return pd.read_csv(
        GROUP_C_ELECTIVE_FILE,
        dtype={"course_code": "string"},
    )


def curriculum_courses(semester):
    curriculum = load_curriculum()
    rows = curriculum[
        (curriculum["semester"] == semester)
        & curriculum["course_code"].notna()
        & (curriculum["course_code"] != "")
    ].sort_values("course_order")
    return rows["course_code"].tolist()


def additional_courses(semester, *, early_graduation=False):
    rules = load_rules()
    rows = rules[
        (rules["available_from_semester"] <= semester)
        & rules["course_code"].notna()
        & ~rules["course_code"].isin(["GROUP_C"])
    ].sort_values(["priority", "rule_id"])
    if not early_graduation:
        rows = rows[rows["activation_condition"] != "early_graduation_3_5_years"]
    return rows["course_code"].tolist()


def free_elective_courses(semester):
    electives = load_electives()
    rows = electives[
        (electives["elective_group"] == "FREE")
        & (electives["available_from_semester"] <= semester)
    ].sort_values(["priority", "course_code"])
    return rows["course_code"].tolist()


def management_elective_courses(semester):
    electives = load_management_electives()
    rows = electives[
        (electives["elective_group"] == "MANAGEMENT")
        & (electives["available_from_semester"] <= semester)
    ].sort_values(["priority", "course_code"])
    return rows["course_code"].tolist()


def group_c_elective_courses(semester):
    electives = load_group_c_electives()
    rows = electives[
        electives["elective_group"].eq("GROUP_C")
        & (electives["available_from_semester"] <= semester)
    ].sort_values(["priority", "course_code"])
    return rows["course_code"].tolist()


def ordered_courses(semester, *, early_graduation=False):
    return list(dict.fromkeys(
        curriculum_courses(semester)
        + additional_courses(semester, early_graduation=early_graduation)
    ))


def course_catalog():
    courses = pd.read_csv(CATALOG_DIR / "course.csv")
    names = dict(zip(courses["course_code"], courses["course_name"]))
    credits = dict(zip(courses["course_code"], courses["credits"]))
    difficulties = dict(zip(courses["course_code"], courses["difficulty"]))
    return names, credits, difficulties


def validate_courses(course_codes, names):
    missing = [code for code in course_codes if code not in names]
    if missing:
        raise ValueError(
            "Courses in curriculum/rules missing from course.csv: "
            + ", ".join(missing)
        )


def get_department(course_code):
    if course_code.startswith(("MI", "SP")):
        return "Triet"
    if course_code.startswith(("MT", "PH", "LA", "CH")):
        return "DaiCuong"
    return "ChuyenNganh"
