from pathlib import Path
import hashlib
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from curriculum_rules import (
    MAX_CREDITS,
    TUITION_BASELINE_CREDITS,
    additional_courses,
    course_catalog,
    curriculum_courses,
    get_department as catalog_department,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data" / "people"
OPTIONAL_ENROLLMENT_THRESHOLD = 15
OPTIONAL_16_CREDIT_PROBABILITY = 0.35
ACCELERATION_BASE_SCORE = 8.0
ACCELERATION_PROBABILITY = 0.35
SEMESTER = "HK241"
K23_COURSES = curriculum_courses("HK3")
K23_EXTRA_COURSES = [
    code for code in additional_courses("HK3") if code not in K23_COURSES
]
K24_COURSES = curriculum_courses("HK1")
COURSE_ORDER = list(dict.fromkeys(K23_COURSES + K23_EXTRA_COURSES + K24_COURSES))


def load_course_data():
    names, credits, difficulties = course_catalog()
    missing = [code for code in COURSE_ORDER if code not in names]
    if missing:
        raise ValueError(f"Courses missing from course.csv: {', '.join(missing)}")
    return names, credits, difficulties


def load_history(semesters=("hk231", "hk232")):
    history = []
    for semester in semesters:
        enrollment_file = ROOT_DIR / "generated" / "enrollments" / f"enrollment_{semester}.csv"
        class_file = ROOT_DIR / "generated" / "classes" / f"class_{semester}.csv"
        if enrollment_file.exists() and class_file.exists():
            enrollment = pd.read_csv(enrollment_file, dtype={"student_id": str})
            classes = pd.read_csv(class_file)[["class_id", "course_code"]]
            history.append(pd.merge(enrollment, classes, on="class_id"))
    if not history:
        return pd.DataFrame(columns=["student_id", "course_code", "status"])
    return pd.concat(history, ignore_index=True)


def can_skip_la1003(student_id, base_score):
    digest = hashlib.sha256(str(student_id).encode("utf-8")).hexdigest()
    random_value = int(digest[:8], 16) / 0xFFFFFFFF
    if base_score >= 8.0:
        return True
    if base_score >= 7.0:
        return random_value < 0.70
    if base_score >= 5.0:
        return random_value < 0.15
    return False


def get_department(course_code):
    return catalog_department(course_code)


def wants_acceleration(student_id, base_score):
    if float(base_score) < ACCELERATION_BASE_SCORE:
        return False
    digest = hashlib.sha256(
        f"{student_id}:acceleration".encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF < ACCELERATION_PROBABILITY


def allows_optional_course_at_16(student_id):
    digest = hashlib.sha256(
        f"{student_id}:optional-at-16".encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF < OPTIONAL_16_CREDIT_PROBABILITY


def calculate_eligibility(students, history, credits, prerequisites):
    passed = (
        history[history["status"].astype(str).str.casefold() == "pass"]
        .groupby("student_id")["course_code"].apply(set).to_dict()
    )
    failed = (
        history[history["status"].astype(str).str.casefold() == "fail"]
        .groupby("student_id")["course_code"].apply(set).to_dict()
    )
    tq_rules = (
        prerequisites[prerequisites["relation_type"] == "TQ"]
        .groupby("course_code")["related_course_code"].apply(list).to_dict()
    )
    eligibility = {student_id: [] for student_id in students["student_id"]}
    registered_credits = {student_id: 0 for student_id in eligibility}

    k23 = students[students["student_id"].str.startswith("231")]
    for student in k23.itertuples(index=False):
        student_id = student.student_id
        passed_courses = passed.get(student_id, set())
        failed_courses = failed.get(student_id, set())
        ordered_courses = [
            code for code in sorted(failed_courses)
            if code in credits and code not in passed_courses
        ] + [
            code for code in K23_COURSES if code not in failed_courses
        ]
        for code in ordered_courses:
            if code in passed_courses:
                continue
            if code not in failed_courses and not all(
                prerequisite in passed_courses
                for prerequisite in tq_rules.get(code, [])
            ):
                continue
            if registered_credits[student_id] + credits[code] > MAX_CREDITS:
                continue
            eligibility[student_id].append(code)
            registered_credits[student_id] += credits[code]
        acceleration = wants_acceleration(
            student.student_id,
            student.base_score,
        )
        can_fill_gap = (
            registered_credits[student_id] < TUITION_BASELINE_CREDITS
            and (
                registered_credits[student_id] <= OPTIONAL_ENROLLMENT_THRESHOLD
                or acceleration
            )
        )
        if can_fill_gap:
            for code in K23_EXTRA_COURSES:
                if registered_credits[student_id] >= TUITION_BASELINE_CREDITS:
                    break
                if code in passed_courses or code in eligibility[student_id]:
                    continue
                if not all(
                    prerequisite in passed_courses
                    for prerequisite in tq_rules.get(code, [])
                ):
                    continue
                if registered_credits[student_id] + credits[code] > MAX_CREDITS:
                    continue
                eligibility[student_id].append(code)
                registered_credits[student_id] += credits[code]

    k24 = students[students["student_id"].str.startswith("241")]
    for student in k24.itertuples(index=False):
        failed_courses = failed.get(student.student_id, set())
        ordered_courses = [
            code for code in sorted(failed_courses)
            if code in credits and code not in passed.get(student.student_id, set())
        ] + [
            code for code in K24_COURSES if code not in failed_courses
        ]
        for code in ordered_courses:
            if code == "LA1003" and code not in failed_courses and can_skip_la1003(
                student.student_id, student.base_score
            ):
                continue
            if registered_credits[student.student_id] + credits[code] > MAX_CREDITS:
                continue
            eligibility[student.student_id].append(code)
            registered_credits[student.student_id] += credits[code]

    return eligibility, failed


def calculate_eligibility_for_schedule(
    students,
    history,
    credits,
    prerequisites,
    scheduled_courses,
    additional_course_groups,
    required_elective_groups=None,
    optional_elective_groups=None,
    required_elective_credits=None,
    required_choice_groups=None,
):
    """Build one eligibility map for a semester's class and enrollment generators."""
    passed = (
        history[history["status"].astype(str).str.casefold() == "pass"]
        .groupby("student_id")["course_code"].apply(set).to_dict()
    )
    failed = (
        history[history["status"].astype(str).str.casefold() == "fail"]
        .groupby("student_id")["course_code"].apply(set).to_dict()
    )
    tq_rules = (
        prerequisites[prerequisites["relation_type"] == "TQ"]
        .groupby("course_code")["related_course_code"].apply(list).to_dict()
    )
    eligibility = {}
    required_elective_groups = required_elective_groups or {}
    optional_elective_groups = optional_elective_groups or {}
    required_elective_credits = required_elective_credits or {}
    required_choice_groups = required_choice_groups or {}
    for student in students.itertuples(index=False):
        prefix = str(student.student_id)[:3]
        scheduled = scheduled_courses.get(prefix)
        if scheduled is None:
            continue
        extras = additional_course_groups.get(prefix, [])
        elective_groups = required_elective_groups.get(prefix, {})
        optional_groups = optional_elective_groups.get(prefix, {})
        credit_targets = required_elective_credits.get(prefix, {})
        choice_groups = required_choice_groups.get(prefix, {})
        passed_courses = passed.get(student.student_id, set())
        failed_courses = failed.get(student.student_id, set())
        selected = []
        registered_credits = 0
        chosen_courses = set()
        for group_name, candidates in choice_groups.items():
            available = [
                code for code in candidates
                if code in credits
                and code not in passed_courses
                and all(
                    prerequisite in passed_courses
                    for prerequisite in tq_rules.get(code, [])
                )
            ]
            if available:
                digest = hashlib.sha256(
                    f"{student.student_id}:{group_name}".encode("utf-8")
                ).hexdigest()
                chosen_courses.add(
                    available[int(digest[:8], 16) % len(available)]
                )
        failed_to_retake = [
            code for code in sorted(failed_courses)
            if code in credits and code not in passed_courses
        ]
        choice_codes = list(chosen_courses)
        ordered = list(dict.fromkeys(
            failed_to_retake
            + choice_codes
            + [
                code for code in scheduled
                if code not in failed_courses
                and code not in choice_codes
            ]
        ))
        for code in ordered:
            if code in passed_courses or registered_credits + credits[code] > MAX_CREDITS:
                continue
            if code not in failed_courses and not all(
                prerequisite in passed_courses
                for prerequisite in tq_rules.get(code, [])
            ):
                continue
            selected.append(code)
            registered_credits += credits[code]
        for group_name, target in credit_targets.items():
            candidates = elective_groups.get(group_name, [])
            completed = sum(
                credits[code]
                for code in passed_courses | set(selected)
                if code in candidates
            )
            for code in candidates:
                if completed >= target:
                    break
                if code in passed_courses or code in selected:
                    continue
                if not all(
                    prerequisite in passed_courses
                    for prerequisite in tq_rules.get(code, [])
                ):
                    continue
                if registered_credits + credits[code] > MAX_CREDITS:
                    continue
                selected.append(code)
                registered_credits += credits[code]
                completed += credits[code]
        acceleration = wants_acceleration(
            student.student_id,
            student.base_score,
        )
        optional_at_16 = (
            registered_credits == 16
            and allows_optional_course_at_16(student.student_id)
        )
        can_fill_gap = (
            registered_credits < TUITION_BASELINE_CREDITS
            and (
                registered_credits <= OPTIONAL_ENROLLMENT_THRESHOLD
                or optional_at_16
                or acceleration
            )
        )
        if can_fill_gap:
            elective_stages = []
            management_candidates = elective_groups.get("MANAGEMENT", [])
            management_completed = (
                passed_courses | set(selected)
            ).intersection(management_candidates)
            if management_candidates and not management_completed:
                elective_stages.append(
                    ("MANAGEMENT", management_candidates)
                )
            peer_candidates = [
                (group_name, candidates)
                for group_name, candidates in [
                    *elective_groups.items(),
                    *optional_groups.items(),
                ]
                if group_name != "MANAGEMENT"
                and group_name in {"FREE", "GROUP_C"}
            ]
            if peer_candidates:
                peer_candidates.sort(key=lambda item: item[0])
                elective_stages.append(
                    (
                        "FREE_OR_GROUP_C",
                        [
                            (group_name, code)
                            for group_name, candidates in peer_candidates
                            for code in candidates
                        ],
                    )
                )
            management_stage = [
                stage for stage in elective_stages
                if stage[0] == "MANAGEMENT"
            ]
            for group_name, candidates in management_stage:
                if registered_credits >= TUITION_BASELINE_CREDITS:
                    break
                available = [
                    (group_name, code)
                    for code in candidates
                    if code not in passed_courses
                    and code not in selected
                    and all(
                        prerequisite in passed_courses
                        for prerequisite in tq_rules.get(code, [])
                    )
                    and registered_credits + credits[code] <= MAX_CREDITS
                ]
                if available:
                    digest = hashlib.sha256(
                        f"{student.student_id}:{group_name}".encode("utf-8")
                    ).hexdigest()
                    _, choice = available[
                        int(digest[:8], 16) % len(available)
                    ]
                    selected.append(choice)
                    registered_credits += credits[choice]

            peer_stage = next(
                (
                    candidates
                    for group_name, candidates in elective_stages
                    if group_name == "FREE_OR_GROUP_C"
                ),
                [],
            )
            peer_round = 0
            max_peer_courses = (
                None
                if acceleration or registered_credits <= OPTIONAL_ENROLLMENT_THRESHOLD
                else 1
            )
            optional_credit_limit = (
                MAX_CREDITS
                if acceleration
                else TUITION_BASELINE_CREDITS + 1
            )
            while (
                registered_credits < TUITION_BASELINE_CREDITS
                and peer_stage
                and (
                    max_peer_courses is None
                    or peer_round < max_peer_courses
                )
            ):
                available = [
                    (source_group, code)
                    for source_group, code in peer_stage
                    if code not in passed_courses
                    and code not in selected
                    and all(
                        prerequisite in passed_courses
                        for prerequisite in tq_rules.get(code, [])
                    )
                    and registered_credits + credits[code] <= optional_credit_limit
                ]
                if not available:
                    break
                digest = hashlib.sha256(
                    f"{student.student_id}:FREE_OR_GROUP_C:{peer_round}"
                    .encode("utf-8")
                ).hexdigest()
                _, choice = available[
                    int(digest[:8], 16) % len(available)
                ]
                selected.append(choice)
                registered_credits += credits[choice]
                peer_round += 1
        if (
            can_fill_gap
            and acceleration
            and registered_credits < TUITION_BASELINE_CREDITS
        ):
            for code in extras:
                if registered_credits >= TUITION_BASELINE_CREDITS:
                    break
                if code in passed_courses or code in selected:
                    continue
                if not all(
                    prerequisite in passed_courses
                    for prerequisite in tq_rules.get(code, [])
                ):
                    continue
                if registered_credits + credits[code] > MAX_CREDITS:
                    continue
                selected.append(code)
                registered_credits += credits[code]
        eligibility[student.student_id] = selected
    return eligibility, failed
