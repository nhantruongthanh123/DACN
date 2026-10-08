from pathlib import Path
import json
import hashlib
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from curriculum_rules import (
    MAX_CREDITS,
    TUITION_BASELINE_CREDITS,
    additional_courses,
    course_catalog,
    curriculum_courses,
    get_department as catalog_department,
    load_electives,
    load_group_c_electives,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data" / "people"
CONFIG_FILE = ROOT_DIR / "config" / "generator_config.json"
PROFILE_OUTPUT_DIR = ROOT_DIR / "generated" / "student_profile"
PROFILE_OUTPUT_FILE = PROFILE_OUTPUT_DIR / "student_profiles.csv"
LEGACY_PROFILE_FILE = DATA_DIR / "student_base_score.csv"
OPTIONAL_ENROLLMENT_THRESHOLD = 15
OPTIONAL_16_CREDIT_PROBABILITY = 0.35
ACCELERATION_BASE_SCORE = 8.0
ACCELERATION_PROBABILITY = 0.35
FREE_CREDIT_LIMIT = 9
GROUP_C_CREDIT_LIMIT = 15
STANDARD_SEMESTERS = 8
MAX_LATE_SEMESTERS = 4
DISMISSAL_AFTER_SEMESTERS = 12

_FREE_COURSE_CODES = None
_GROUP_C_COURSE_CODES = None


def get_free_course_codes():
    global _FREE_COURSE_CODES
    if _FREE_COURSE_CODES is None:
        try:
            df = load_electives()
            _FREE_COURSE_CODES = set(
                df[df["elective_group"] == "FREE"]["course_code"].dropna()
            )
        except Exception:
            _FREE_COURSE_CODES = set()
    return _FREE_COURSE_CODES


def get_group_c_course_codes():
    global _GROUP_C_COURSE_CODES
    if _GROUP_C_COURSE_CODES is None:
        try:
            df = load_group_c_electives()
            _GROUP_C_COURSE_CODES = set(
                df[df["elective_group"] == "GROUP_C"]["course_code"].dropna()
            )
        except Exception:
            _GROUP_C_COURSE_CODES = set()
    return _GROUP_C_COURSE_CODES

SEMESTER = "HK141"
K13_COURSES = curriculum_courses("HK3")
K13_EXTRA_COURSES = [
    code for code in additional_courses("HK3") if code not in K13_COURSES
]
K14_COURSES = curriculum_courses("HK1")
COURSE_ORDER = list(dict.fromkeys(K13_COURSES + K13_EXTRA_COURSES + K14_COURSES))
PROFILE_FIELDS = (
    "family_income",
    "financial_pressure",
    "living_condition",
    "discipline",
    "motivation",
    "stress",
    "social_activity",
    "academic_level",
    "math_level",
    "english_level",
)


def validate_generator_config(config):
    def validate_distribution(name, values):
        if (
            not values
            or any(not isinstance(value, (int, float)) or value < 0 for value in values)
            or not math.isclose(sum(values), 1.0, abs_tol=1e-9)
        ):
            raise ValueError(f"{name} probabilities must be non-negative and sum to 1")

    personality = config["personality"]
    scale = personality["scale"]
    for trait in ("discipline", "motivation", "stress", "social_activity"):
        if len(personality[trait]) != len(scale):
            raise ValueError(f"personality.{trait} must match personality.scale")
        validate_distribution(f"personality.{trait}", personality[trait])

    academic = config["academic"]
    if len(academic["distribution"]) != 5 or len(academic["base_scores"]) != 5:
        raise ValueError("academic distribution and base_scores must have five values")
    validate_distribution("academic.distribution", academic["distribution"])
    if (
        academic["subject_sigma"] < 0
        or academic["base_scores"] != sorted(academic["base_scores"])
    ):
        raise ValueError("academic subject_sigma must be non-negative and base_scores ordered")

    for name, distribution in config["background"].items():
        if len(distribution["values"]) != len(distribution["probabilities"]):
            raise ValueError(f"background.{name} values and probabilities must match")
        validate_distribution(
            f"background.{name}",
            distribution["probabilities"],
        )

    noise = config["noise"]
    validate_distribution(
        "noise population",
        [noise["normal_ratio"], noise["high_deviation_ratio"]],
    )
    validate_distribution(
        "noise direction",
        [noise["low_direction_ratio"], noise["high_direction_ratio"]],
    )
    difficulty = config["difficulty"]
    if not 0 <= difficulty["resilience"] <= 1:
        raise ValueError("difficulty.resilience must be between 0 and 1")
    if (
        difficulty["catalog_min"] >= difficulty["catalog_max"]
        or difficulty["min_level"] >= difficulty["max_level"]
        or difficulty["max_penalty"] < 0
    ):
        raise ValueError("difficulty ranges must be increasing and penalty non-negative")
    if any(
        not difficulty["min_level"] <= float(level) <= difficulty["max_level"]
        for level in difficulty["course_overrides"].values()
    ):
        raise ValueError("course difficulty overrides must be within the configured levels")
    if noise["normal_sigma"] < 0 or noise["high_sigma"] < 0:
        raise ValueError("noise sigma values must be non-negative")
    if config["score"]["min"] >= config["score"]["max"]:
        raise ValueError("score.min must be less than score.max")

    progress = config["student_progress"]
    semesters = progress["observed_semesters"]
    if (
        not semesters
        or len(semesters) != len(set(semesters))
        or semesters != sorted(semesters, key=lambda value: int(value[2:]))
    ):
        raise ValueError(
            "student_progress.observed_semesters must be unique and ordered"
        )
    if any(
        start not in semesters
        for start in progress["cohort_start_semester"].values()
    ):
        raise ValueError(
            "cohort start semesters must be present in observed_semesters"
        )
    ctxh = progress["ctxh"]
    if (
        ctxh["minimum_for_thesis"] < 0
        or ctxh["minimum_for_graduation"] < ctxh["minimum_for_thesis"]
        or ctxh["minimum_expected_days_per_semester"] < 0
        or ctxh["maximum_expected_days_per_semester"]
        < ctxh["minimum_expected_days_per_semester"]
        or any(weight < 0 for weight in ctxh["personality_weights"].values())
        or not math.isclose(
            sum(ctxh["personality_weights"].values()), 1.0, abs_tol=1e-9
        )
    ):
        raise ValueError("Invalid CTXH progress configuration")
    if not 0 <= progress["dropout"]["voluntary_probability"] <= 1:
        raise ValueError("voluntary_dropout_probability must be between 0 and 1")
    if not math.isclose(
        sum(progress["dropout"]["voluntary_reason_weights"].values()),
        1.0,
        abs_tol=1e-9,
    ):
        raise ValueError("voluntary dropout reason weights must sum to 1")
    english = progress["english"]
    if (
        any(
            english[name] < 0
            for name in (
                "base_probability",
                "background_weight",
                "english_skill_weight",
                "academic_weight",
                "personality_weight",
            )
        )
        or english["base_probability"] > 1
    ):
        raise ValueError("Invalid English eligibility probability configuration")
    graduation = progress["graduation"]
    if (
        graduation["standard_semesters"] <= 0
        or graduation.get("max_late_semesters", 1) <= 0
        or graduation["dismissal_after_semesters"]
        < graduation["standard_semesters"]
        or graduation["minimum_passed_credits_per_semester"] < 0
        or not 0 <= graduation[
            "ineligible_thesis_empty_semester_probability"
        ] <= 1
        or not graduation["thesis_course_codes"]
        or not graduation["graduation_project_codes"]
    ):
        raise ValueError("Invalid graduation progress configuration")
    if "electives" in progress:
        electives = progress["electives"]
        if (
            electives.get("free_credit_limit", 0) < 0
            or electives.get("group_c_credit_limit", 0) < 0
        ):
            raise ValueError("Invalid electives configuration")
    if "enrollment_policy" in progress:
        policy = progress["enrollment_policy"]
        if (
            policy.get("optional_threshold", 0) < 0
            or not 0 <= policy.get("optional_16_credit_probability", 0) <= 1
            or policy.get("acceleration_base_score", 0) < 0
            or not 0 <= policy.get("acceleration_probability", 0) <= 1
        ):
            raise ValueError("Invalid enrollment policy configuration")

    grade_scale = config["grade_scale"]
    if (
        not grade_scale
        or grade_scale[0]["min"] != config["score"]["min"]
        or grade_scale[-1]["max"] != config["score"]["max"]
        or any(
            lower["max"] != upper["min"]
            for lower, upper in zip(grade_scale, grade_scale[1:])
        )
    ):
        raise ValueError("grade_scale must continuously cover the configured score range")
    return config


def load_generator_config(config_file=None):
    target = Path(config_file) if config_file else CONFIG_FILE
    with target.open(encoding="utf-8") as file_obj:
        config = json.load(file_obj)
    return validate_generator_config(config)


GENERATOR_CONFIG = load_generator_config()


def filter_students_from_2013(students):
    if "student_id" not in students:
        raise ValueError("Student data must contain a student_id column")
    student_ids = students["student_id"].astype(str).str.strip()
    prefixes = student_ids.str[:2]
    valid_prefixes = prefixes.str.fullmatch(r"\d{2}")
    if not valid_prefixes.all():
        invalid_ids = students.loc[~valid_prefixes, "student_id"].head(5).tolist()
        raise ValueError(
            "Student IDs must start with a two-digit cohort year; "
            f"invalid examples: {invalid_ids}"
        )
    filtered = students.copy()
    filtered["student_id"] = student_ids
    return filtered.loc[prefixes.astype(int) >= 13].copy()


def cohort_year(student_id):
    """Return the cohort year encoded by the first two ID digits."""
    student_id = str(student_id).strip()
    prefix = student_id[:2]
    if not prefix.isdigit() or len(prefix) != 2:
        raise ValueError(
            f"Student ID must start with a two-digit cohort year: {student_id}"
        )
    return int(prefix)


def load_student_profiles():
    """Load generated profiles for cohort 2013 onward."""
    if not PROFILE_OUTPUT_FILE.exists():
        raise FileNotFoundError(
            "Student profiles are missing. Run tools/add_base_score.py first."
        )
    students = pd.read_csv(PROFILE_OUTPUT_FILE, dtype={"student_id": str})
    required_columns = {"student_id", "name", "base_score"}
    missing_columns = required_columns.difference(students.columns)
    if missing_columns:
        raise ValueError(
            "student_profiles.csv is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )
    students = filter_students_from_2013(students)
    cohort_filter = os.environ.get("SYNTHETIC_DATA_COHORT_FILTER", "").strip()
    if cohort_filter:
        if len(cohort_filter) != 2 or not cohort_filter.isdigit():
            raise ValueError(
                "SYNTHETIC_DATA_COHORT_FILTER must be a two-digit cohort year"
            )
        students = students[
            students["student_id"].str.startswith(cohort_filter)
        ].copy()
    return students


def balanced_class_sizes(demand, max_size=120):
    """Use the fewest sections possible and balance them within the capacity limit."""
    demand = int(demand)
    max_size = int(max_size)
    if demand < 0:
        raise ValueError("Class demand cannot be negative")
    if max_size <= 0:
        raise ValueError("Class capacity must be positive")
    if demand == 0:
        return []
    class_count = math.ceil(demand / max_size)
    base_size, remainder = divmod(demand, class_count)
    return [
        base_size + (1 if index < remainder else 0)
        for index in range(class_count)
    ]


def students_by_course_from_eligibility(eligibility):
    students_by_course = {}
    for student_id, courses in eligibility.items():
        for course_code in courses:
            students_by_course.setdefault(course_code, []).append(student_id)
    return students_by_course


def allocate_course_rosters(students_by_course, classes, max_size=120):
    """Assign every eligible student to an existing same-course class within capacity."""
    required_columns = {"class_id", "course_code"}
    if not required_columns.issubset(classes.columns):
        missing = sorted(required_columns - set(classes.columns))
        raise ValueError(f"Class data is missing columns: {', '.join(missing)}")
    if classes["class_id"].duplicated().any():
        duplicates = classes.loc[
            classes["class_id"].duplicated(), "class_id"
        ].head(5).tolist()
        raise ValueError(f"Duplicate class IDs: {duplicates}")

    classes_by_course = {
        course_code: group["class_id"].tolist()
        for course_code, group in classes.groupby("course_code", sort=False)
    }
    rosters = {}
    for course_code, student_ids in students_by_course.items():
        student_ids = list(student_ids)
        if not student_ids:
            continue
        if len(student_ids) != len(set(student_ids)):
            raise ValueError(f"Duplicate eligible student for {course_code}")
        class_ids = classes_by_course.get(course_code, [])
        if not class_ids:
            raise ValueError(
                f"No existing class is available for {len(student_ids)} "
                f"eligible students in {course_code}"
            )
        sizes = balanced_class_sizes(len(student_ids), max_size)
        if len(class_ids) < len(sizes):
            raise ValueError(
                f"{course_code} needs {len(sizes)} classes for "
                f"{len(student_ids)} students, but only {len(class_ids)} exist"
            )
        assignments = []
        offset = 0
        for class_id, size in zip(class_ids, sizes):
            assignments.append((class_id, student_ids[offset:offset + size]))
            offset += size
        rosters[course_code] = assignments
    return rosters


def _stable_seed(student_id, config, salt):
    value = f"{config['seed']}:{student_id}:{salt}".encode("utf-8")
    return int(hashlib.sha256(value).hexdigest()[:8], 16)


def _base_score_for_level(level, config):
    base_scores = config["academic"]["base_scores"]
    lower = int(math.floor(level))
    upper = int(math.ceil(level))
    if lower == upper:
        return float(base_scores[lower - 1])
    fraction = level - lower
    return (
        float(base_scores[lower - 1]) * (1 - fraction)
        + float(base_scores[upper - 1]) * fraction
    )


def generate_student_profile(student_id, config=None):
    config = config or GENERATOR_CONFIG
    profile = {}
    for field, distribution in config["background"].items():
        rng = np.random.default_rng(_stable_seed(student_id, config, field))
        profile[field] = rng.choice(
            distribution["values"],
            p=distribution["probabilities"],
        )
    for field in ("discipline", "motivation", "stress", "social_activity"):
        rng = np.random.default_rng(_stable_seed(student_id, config, field))
        profile[field] = int(rng.choice(
            config["personality"]["scale"],
            p=config["personality"][field],
        ))

    rng = np.random.default_rng(_stable_seed(student_id, config, "academic_level"))
    academic_level = int(rng.choice(
        [1, 2, 3, 4, 5],
        p=config["academic"]["distribution"],
    ))
    profile["academic_level"] = academic_level
    for field in ("math_level", "english_level"):
        subject_rng = np.random.default_rng(
            _stable_seed(student_id, config, field)
        )
        profile[field] = int(np.clip(
            round(subject_rng.normal(
                academic_level,
                config["academic"]["subject_sigma"],
            )),
            1,
            5,
        ))
    progress_config = config["student_progress"]
    background_scores = progress_config["english"]["background_scores"]
    background_strength = float(np.mean([
        background_scores[field][profile[field]]
        for field in background_scores
    ]))
    personality_strength = _progress_personality_strength(profile, progress_config)
    english_probability = (
        progress_config["english"]["base_probability"]
        + progress_config["english"]["background_weight"] * background_strength
        + progress_config["english"]["english_skill_weight"]
        * ((profile["english_level"] - 1) / 4)
        + progress_config["english"]["academic_weight"]
        * ((profile["academic_level"] - 1) / 4)
        + progress_config["english"]["personality_weight"]
        * personality_strength
    )
    english_rng = np.random.default_rng(
        _stable_seed(student_id, config, "english_eligibility")
    )
    profile["english_pass"] = bool(
        english_rng.random() < np.clip(english_probability, 0.0, 1.0)
    )
    profile["ctxh_days_by_semester"] = _generate_ctxh_progress(
        student_id, profile, config
    )
    dropout_semester, dropout_reason = _generate_voluntary_dropout(
        student_id, profile, config
    )
    profile["voluntary_dropout_semester"] = dropout_semester or ""
    profile["voluntary_dropout_reason"] = dropout_reason or ""
    return profile


def _progress_personality_strength(profile, progress_config):
    weights = progress_config["ctxh"]["personality_weights"]
    trait_strengths = {
        "discipline": (profile["discipline"] - 1) / 4,
        "motivation": (profile["motivation"] - 1) / 4,
        "social_activity": (profile["social_activity"] - 1) / 4,
        "stress": (5 - profile["stress"]) / 4,
    }
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("CTXH personality weights must sum to a positive value")
    return float(sum(
        weights[trait] * trait_strengths[trait]
        for trait in weights
    ) / total_weight)


def _generate_ctxh_progress(student_id, profile, config):
    progress_config = config["student_progress"]
    start_semester = progress_config["cohort_start_semester"].get(
        str(student_id)[:2]
    )
    if start_semester is None:
        return []
    start_index = semester_index(start_semester)
    semesters = [
        semester
        for semester in progress_config["observed_semesters"]
        if semester_index(semester) >= start_index
    ]
    ctxh_config = progress_config["ctxh"]
    personality_strength = _progress_personality_strength(
        profile, progress_config
    )
    expected_days = (
        ctxh_config["minimum_expected_days_per_semester"]
        + personality_strength
        * (
            ctxh_config["maximum_expected_days_per_semester"]
            - ctxh_config["minimum_expected_days_per_semester"]
        )
    )
    cumulative_days = 0
    progress = []
    for semester in semesters:
        rng = np.random.default_rng(
            _stable_seed(student_id, config, f"ctxh:{semester}")
        )
        cumulative_days += int(rng.poisson(expected_days))
        progress.append({
            "semester": semester,
            "cumulative_days": cumulative_days,
        })
    return progress


def _generate_voluntary_dropout(student_id, profile, config):
    progress_config = config["student_progress"]
    dropout_config = progress_config["dropout"]
    background_scores = progress_config["english"]["background_scores"]
    background_strength = float(np.mean([
        background_scores[field][profile[field]]
        for field in background_scores
    ]))
    at_risk = (
        background_strength <= dropout_config["low_background_score_max"]
        or profile["academic_level"]
        <= dropout_config["low_academic_level_max"]
    )
    if not at_risk:
        return None, None

    rng = np.random.default_rng(
        _stable_seed(student_id, config, "voluntary_dropout")
    )
    if rng.random() >= dropout_config["voluntary_probability"]:
        return None, None

    reason_weights = dropout_config["voluntary_reason_weights"]
    reasons = list(reason_weights)
    weights = np.array([reason_weights[reason] for reason in reasons], dtype=float)
    reason = str(rng.choice(reasons, p=weights))
    start_semester = progress_config["cohort_start_semester"].get(
        str(student_id)[:2]
    )
    if start_semester is None:
        return None, None
    start_index = semester_index(start_semester)
    semesters = [
        semester
        for semester in progress_config["observed_semesters"]
        if semester_index(semester) >= start_index
    ]
    if not semesters:
        return None, None
    return str(rng.choice(semesters)), reason


def _student_value(student, field, default=None):
    if hasattr(student, "get"):
        return student.get(field, default)
    return getattr(student, field, default)


def ctxh_days_before_semester(student, semester_code):
    progress = _student_value(student, "ctxh_days_by_semester", [])
    if progress is None or (
        not isinstance(progress, (list, str)) and pd.isna(progress)
    ):
        progress = []
    if isinstance(progress, str):
        try:
            progress = json.loads(progress) if progress else []
        except json.JSONDecodeError as error:
            raise ValueError("ctxh_days_by_semester must contain a JSON array") from error
    if not isinstance(progress, list):
        raise ValueError("ctxh_days_by_semester must be an array")
    current_index = semester_index(semester_code)
    return max(
        (
            int(entry["cumulative_days"])
            for entry in progress
            if semester_index(entry["semester"]) < current_index
        ),
        default=0,
    )


def academic_suspension_semesters(
    student_history, semesters, credits, config=None
):
    """Return the one-semester pauses triggered by consecutive low-credit terms."""
    config = config or GENERATOR_CONFIG
    if "status" not in student_history or "course_code" not in student_history:
        return set()

    semester_column = (
        "semester_code"
        if "semester_code" in student_history
        else "semester"
        if "semester" in student_history
        else None
    )
    if semester_column is None:
        return set()

    low_credit_threshold = config["student_progress"]["graduation"][
        "minimum_passed_credits_per_semester"
    ]
    low_credit_streak = 0
    suspensions = set()

    for semester in semesters:
        current_index = semester_index(semester)
        if low_credit_streak >= 2:
            suspensions.add(semester)
            low_credit_streak = 0
            continue

        if semester_column == "semester_code":
            term_history = student_history[
                student_history[semester_column].astype(str).str.upper()
                == semester.upper()
            ]
        else:
            term_history = student_history[
                pd.to_numeric(
                    student_history[semester_column], errors="coerce"
                )
                == current_index
            ]
        passed = term_history[
            term_history["status"].astype(str).str.casefold() == "pass"
        ]
        passed_credits = sum(
            float(credits[course_code])
            for course_code in passed["course_code"].drop_duplicates()
            if course_code in credits
        )
        if passed_credits < low_credit_threshold:
            low_credit_streak += 1
        else:
            low_credit_streak = 0

    return suspensions


def _is_academic_suspension_semester(
    student_id, history, credits, semester_code, config
):
    if history.empty:
        return False
    progress_config = config["student_progress"]
    start_semester = progress_config["cohort_start_semester"].get(
        str(student_id)[:2]
    )
    if start_semester is None:
        return False
    current_index = semester_index(semester_code)
    semesters = [
        semester
        for semester in progress_config["observed_semesters"]
        if semester_index(start_semester)
        <= semester_index(semester)
        <= current_index
    ]
    student_history = (
        history[history["student_id"] == student_id]
        if "student_id" in history
        else history
    )
    return semester_code in academic_suspension_semesters(
        student_history, semesters, credits, config
    )


def resolve_student_profile(student, config=None, *, student_id=None):
    config = config or GENERATOR_CONFIG
    student_id = student_id or student.get("student_id")
    if student_id is None or pd.isna(student_id):
        raise ValueError("student_id is required to resolve a student profile")
    student_id = str(student_id)
    profile = generate_student_profile(student_id, config)
    for field in PROFILE_FIELDS:
        value = student.get(field)
        if pd.notna(value):
            profile[field] = value
    if pd.isna(student.get("academic_level")) and pd.notna(student.get("base_score")):
        base_scores = config["academic"]["base_scores"]
        profile["academic_level"] = min(
            range(1, 6),
            key=lambda level: abs(
                float(student["base_score"]) - base_scores[level - 1]
            ),
        )
    for field in (
        "discipline",
        "motivation",
        "stress",
        "social_activity",
        "academic_level",
        "math_level",
        "english_level",
    ):
        value = int(profile[field])
        if value < 1 or value > 5:
            raise ValueError(f"{field} for student {student_id} must be between 1 and 5")
        profile[field] = value
    return profile


def _normalized_trait(value):
    return (float(value) - 3.0) / 2.0


def course_mean_score(
    student,
    course_code,
    catalog_difficulty,
    config=None,
    *,
    student_id=None,
):
    config = config or GENERATOR_CONFIG
    profile = resolve_student_profile(
        student,
        config,
        student_id=student_id,
    )
    prefix = str(course_code)[:2].upper()
    subject = (
        "english_level"
        if prefix == "LA"
        else "math_level"
        if prefix in {"MT", "MA", "PH", "CH"}
        else None
    )
    ability_level = float(profile["academic_level"])
    if subject:
        ability_level += config["academic"]["subject_effect"] * (
            profile[subject] - profile["academic_level"]
        )
    mean_score = _base_score_for_level(ability_level, config)
    mean_score += sum(
        weight * _normalized_trait(profile[trait])
        for trait, weight in config["personality_weights"].items()
    )

    difficulty_config = config["difficulty"]
    overrides = difficulty_config["course_overrides"]
    if course_code in overrides:
        difficulty_fraction = (
            overrides[course_code] - difficulty_config["min_level"]
        ) / (difficulty_config["max_level"] - difficulty_config["min_level"])
    else:
        catalog_value = float(catalog_difficulty)
        if not math.isfinite(catalog_value):
            raise ValueError(f"Invalid catalog difficulty for course {course_code}")
        difficulty_fraction = (
            catalog_value - difficulty_config["catalog_min"]
        ) / (difficulty_config["catalog_max"] - difficulty_config["catalog_min"])
    difficulty_fraction = float(np.clip(difficulty_fraction, 0.0, 1.0))

    academic_strength = (profile["academic_level"] - 1) / 4.0
    personality_strength = sum((
        (profile["discipline"] - 1) / 4.0,
        (profile["motivation"] - 1) / 4.0,
        (5 - profile["stress"]) / 4.0,
    )) / 3.0
    overall_strength = (academic_strength + personality_strength) / 2.0
    difficulty_effect = (
        difficulty_fraction
        * difficulty_config["max_penalty"]
        * (1.0 - difficulty_config["resilience"] * overall_strength)
    )
    return mean_score - difficulty_effect


def generate_observed_score(mean_score, rng, config=None, *, retaken=False):
    config = config or GENERATOR_CONFIG
    noise = config["noise"]
    if rng.random() < noise["high_deviation_ratio"]:
        deviation = abs(rng.normal(0, noise["high_sigma"]))
        if rng.random() < noise["low_direction_ratio"]:
            score = mean_score - deviation
        else:
            score = mean_score + deviation
    else:
        score = rng.normal(mean_score, noise["normal_sigma"])
    if retaken:
        score += config["score"]["retake_bonus"]
    return float(np.clip(score, config["score"]["min"], config["score"]["max"]))


def convert_score_to_grade(score, config=None):
    config = config or GENERATOR_CONFIG
    grade_scale = config["grade_scale"]
    for index, grade in enumerate(grade_scale):
        if grade["min"] <= score < grade["max"]:
            return grade["letter"], float(grade["gpa4"])
        if index == len(grade_scale) - 1 and score == grade["max"]:
            return grade["letter"], float(grade["gpa4"])
    raise ValueError(f"Score {score} is outside the configured grade scale")


def semester_index(semester_code):
    code = str(semester_code).upper()
    if len(code) != 5 or not code.startswith("HK") or not code[2:].isdigit():
        raise ValueError(f"Invalid semester code: {semester_code}")
    year = int(code[2:4])
    term = int(code[4])
    if term not in (1, 2):
        raise ValueError(f"Invalid semester term in {semester_code}")
    return (year - 23) * 2 + term


def semester_from_index(idx):
    """Convert integer semester index back to canonical semester code, e.g. -19 -> 'HK131'."""
    year = 23 + (idx - 1) // 2
    term = 1 if (idx % 2 != 0) else 2
    return f"HK{year}{term}"


def get_late_semesters_count(student_id, semester_code, config=None):
    """Calculate the number of late semesters for a student at a given semester.

    Returns:
        int: Number of late semesters (0 if on-time or early, 1-4 if within late allowance, >4 if overdue).
    """
    config = config or GENERATOR_CONFIG
    progress_config = config["student_progress"]
    cohort_start = progress_config["cohort_start_semester"].get(str(student_id)[:2])
    if cohort_start is None:
        return 0
    elapsed = semester_index(semester_code) - semester_index(cohort_start)
    standard_terms = progress_config["graduation"].get(
        "standard_semesters", STANDARD_SEMESTERS
    )
    return max(0, elapsed - standard_terms + 1)


def is_late_semester(student_id, semester_code, config=None):
    """Check if student is in an allowed late semester (1 to max_late_semesters late)."""
    late_count = get_late_semesters_count(student_id, semester_code, config)
    config = config or GENERATOR_CONFIG
    max_late = config.get("student_progress", {}).get("graduation", {}).get(
        "max_late_semesters", MAX_LATE_SEMESTERS
    )
    return 1 <= late_count <= max_late


def is_academic_dismissal(student_id, semester_code, config=None):
    """Check if student is dismissed for exceeding maximum allowed study duration.

    Under HCMUT academic regulations:
    - Standard curriculum duration: 8 semesters (4 years).
    - Maximum extension allowed: 4 late semesters (2 years).
    - Total maximum study duration: 12 semesters.
    After 12 semesters (i.e. at or after the 13th semester from cohort start),
    students who have not graduated are subjected to academic dismissal (buộc thôi học).
    """
    config = config or GENERATOR_CONFIG
    progress_config = config["student_progress"]
    cohort_start = progress_config["cohort_start_semester"].get(str(student_id)[:2])
    if cohort_start is None:
        return False
    elapsed = semester_index(semester_code) - semester_index(cohort_start)
    grad_config = progress_config.get("graduation", {})
    dismissal_threshold = grad_config.get(
        "dismissal_after_semesters",
        grad_config.get("standard_semesters", STANDARD_SEMESTERS)
        + grad_config.get("max_late_semesters", MAX_LATE_SEMESTERS),
    )
    return elapsed >= dismissal_threshold


def get_academic_dismissal_semester(student_id, config=None):
    """Return the semester code where dismissal triggers (the 13th semester, exceeding 12 semesters)."""
    config = config or GENERATOR_CONFIG
    progress_config = config["student_progress"]
    cohort_start = progress_config["cohort_start_semester"].get(str(student_id)[:2])
    if cohort_start is None:
        return None
    start_idx = semester_index(cohort_start)
    grad_config = progress_config.get("graduation", {})
    dismissal_threshold = grad_config.get(
        "dismissal_after_semesters",
        grad_config.get("standard_semesters", STANDARD_SEMESTERS)
        + grad_config.get("max_late_semesters", MAX_LATE_SEMESTERS),
    )
    return semester_from_index(start_idx + dismissal_threshold)


def academic_dismissal_semesters(student_id, semesters, config=None):
    """Return the set of semesters from the list that fall under academic dismissal for the student."""
    return {
        semester
        for semester in semesters
        if is_academic_dismissal(student_id, semester, config)
    }



def score_course_components(
    student,
    course_code,
    components,
    catalog_difficulty,
    rng,
    config=None,
    *,
    retaken=False,
    student_id=None,
):
    config = config or GENERATOR_CONFIG
    mean_score = course_mean_score(
        student,
        course_code,
        catalog_difficulty,
        config,
        student_id=student_id,
    )
    scores = {}
    final_score = 0.0
    for component, weight in components:
        score = round(generate_observed_score(
            mean_score,
            rng,
            config,
            retaken=retaken,
        ), 1)
        scores[component] = score
        final_score += score * weight
    final_score = round(final_score, 1)
    letter, gpa = convert_score_to_grade(final_score, config)
    return scores, final_score, letter, gpa


def add_gpa_summaries(result, history, credits, config=None):
    config = config or GENERATOR_CONFIG
    semester_gpas = {}
    for student_id, attempts in result.groupby("student_id"):
        weighted_points = 0.0
        attempted_credits = 0.0
        for attempt in attempts.to_dict("records"):
            score = attempt.get("final_score")
            if pd.isna(score):
                continue
            course_code = attempt["course_id"]
            if course_code not in credits:
                raise ValueError(f"Credits missing for course {course_code}")
            course_credits = float(credits[course_code])
            weighted_points += float(attempt["gpa_4"]) * course_credits
            attempted_credits += course_credits
        semester_gpas[student_id] = (
            round(weighted_points / attempted_credits, 2)
            if attempted_credits
            else pd.NA
        )

    completed_courses = {}
    history_rows = history.to_dict("records")
    current_rows = result.to_dict("records")
    for attempt in history_rows + current_rows:
        score = attempt.get("final_score")
        if pd.isna(score):
            continue
        course_code = attempt.get("course_code", attempt.get("course_id"))
        student_id = attempt.get("student_id")
        if course_code not in credits:
            raise ValueError(f"Credits missing for course {course_code}")
        letter, gpa = convert_score_to_grade(float(score), config)
        if letter == "F":
            continue
        student_courses = completed_courses.setdefault(student_id, {})
        student_courses[course_code] = (
            gpa,
            float(credits[course_code]),
        )

    final_gpas = {}
    for student_id, student_courses in completed_courses.items():
        total_credits = sum(credit for _, credit in student_courses.values())
        final_gpas[student_id] = (
            round(
                sum(gpa * credit for gpa, credit in student_courses.values())
                / total_credits,
                2,
            )
            if total_credits > 0
            else pd.NA
        )

    result["semester_gpa_4"] = result["student_id"].map(semester_gpas)
    result["final_gpa_4"] = result["student_id"].map(final_gpas)
    return result


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


ENGLISH_COURSE_CODES = ("LA1003", "LA1005", "LA1007", "LA1009")


def get_exempted_english_courses(student, config=None):
    """Return the set of English courses exempted for the student.

    - If english_pass is True, student is exempt from all 4 courses (LA1003-LA1009).
    - If english_pass is False, student takes the English placement test upon entry.
      Based on their english_level and test score, they can skip early courses:
        * Placement 1: Skip none (learn LA1003, LA1005, LA1007, LA1009)
        * Placement 2: Skip LA1003 (learn LA1005, LA1007, LA1009)
        * Placement 3: Skip LA1003, LA1005 (learn LA1007, LA1009)
        * Placement 4+: Skip LA1003, LA1005, LA1007 (learn LA1009)
    """
    config = config or GENERATOR_CONFIG
    english_pass = (
        str(_student_value(student, "english_pass", False)).casefold() == "true"
    )
    if english_pass:
        return set(ENGLISH_COURSE_CODES)

    student_id = str(_student_value(student, "student_id", ""))
    english_level = int(_student_value(student, "english_level", 3))

    seed = _stable_seed(student_id, config, "english_placement_test")
    rng = np.random.default_rng(seed)
    val = rng.random()

    if english_level <= 1:
        skip_count = 1 if val < 0.20 else 0
    elif english_level == 2:
        skip_count = 0 if val < 0.20 else (2 if val > 0.80 else 1)
    elif english_level == 3:
        skip_count = 1 if val < 0.10 else (3 if val > 0.80 else 2)
    elif english_level == 4:
        skip_count = 2 if val < 0.10 else 3
    else:
        skip_count = 3

    mapping = {
        0: set(),
        1: {"LA1003"},
        2: {"LA1003", "LA1005"},
        3: {"LA1003", "LA1005", "LA1007"},
    }
    return mapping[skip_count]


def can_skip_la1003(student_id, base_score=None, *, student=None, config=None):
    target = student if student is not None else student_id
    if hasattr(target, "get") or hasattr(target, "student_id") or isinstance(target, dict):
        return "LA1003" in get_exempted_english_courses(target, config)
    digest = hashlib.sha256(str(student_id).encode("utf-8")).hexdigest()
    random_value = int(digest[:8], 16) / 0xFFFFFFFF
    if base_score is not None:
        if base_score >= 8.0:
            return True
        if base_score >= 7.0:
            return random_value < 0.70
        if base_score >= 5.0:
            return random_value < 0.15
    return False


def get_department(course_code):
    return catalog_department(course_code)


def wants_acceleration(student_id, base_score, config=None):
    config = config or GENERATOR_CONFIG
    policy = config.get("student_progress", {}).get("enrollment_policy", {})
    min_base_score = policy.get("acceleration_base_score", ACCELERATION_BASE_SCORE)
    prob = policy.get("acceleration_probability", ACCELERATION_PROBABILITY)
    if float(base_score) < min_base_score:
        return False
    digest = hashlib.sha256(
        f"{student_id}:acceleration".encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF < prob


def allows_optional_course_at_16(student_id, config=None):
    config = config or GENERATOR_CONFIG
    policy = config.get("student_progress", {}).get("enrollment_policy", {})
    prob = policy.get("optional_16_credit_probability", OPTIONAL_16_CREDIT_PROBABILITY)
    digest = hashlib.sha256(
        f"{student_id}:optional-at-16".encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF < prob


def calculate_eligibility(students, history, credits, prerequisites, config=None):
    config = config or GENERATOR_CONFIG
    policy = config.get("student_progress", {}).get("enrollment_policy", {})
    optional_threshold = policy.get("optional_threshold", OPTIONAL_ENROLLMENT_THRESHOLD)
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

    k23 = students[students["student_id"].str.startswith("23")]
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
            config,
        )
        can_fill_gap = (
            registered_credits[student_id] < TUITION_BASELINE_CREDITS
            and (
                registered_credits[student_id] <= optional_threshold
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

    k24 = students[students["student_id"].str.startswith("24")]
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
    *,
    semester_code=None,
    config=None,
):
    """Build one eligibility map for a semester's class and enrollment generators."""
    config = config or GENERATOR_CONFIG
    if semester_code is None:
        raise ValueError("semester_code is required to evaluate student eligibility")
    progress_config = config.get("student_progress", {})
    electives_config = progress_config.get("electives", {})
    free_credit_limit = electives_config.get("free_credit_limit", FREE_CREDIT_LIMIT)
    group_c_credit_limit = electives_config.get("group_c_credit_limit", GROUP_C_CREDIT_LIMIT)
    policy_config = progress_config.get("enrollment_policy", {})
    optional_threshold = policy_config.get("optional_threshold", OPTIONAL_ENROLLMENT_THRESHOLD)
    scheduled_courses = {
        str(cohort)[:2]: courses for cohort, courses in scheduled_courses.items()
    }
    additional_course_groups = {
        str(cohort)[:2]: groups
        for cohort, groups in additional_course_groups.items()
    }
    required_elective_groups = {
        str(cohort)[:2]: groups
        for cohort, groups in (required_elective_groups or {}).items()
    }
    optional_elective_groups = {
        str(cohort)[:2]: groups
        for cohort, groups in (optional_elective_groups or {}).items()
    }
    required_elective_credits = {
        str(cohort)[:2]: groups
        for cohort, groups in (required_elective_credits or {}).items()
    }
    required_choice_groups = {
        str(cohort)[:2]: groups
        for cohort, groups in (required_choice_groups or {}).items()
    }
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
    for student in students.itertuples(index=False):
        student_id = student.student_id
        dropout_semester_value = getattr(
            student, "voluntary_dropout_semester", ""
        )
        dropout_semester = (
            ""
            if pd.isna(dropout_semester_value)
            else str(dropout_semester_value)
        )
        if dropout_semester and semester_index(semester_code) > semester_index(
            dropout_semester
        ):
            continue
        if is_academic_dismissal(student_id, semester_code, config):
            eligibility[student_id] = []
            continue
        if _is_academic_suspension_semester(
            student_id, history, credits, semester_code, config
        ):
            eligibility[student_id] = []
            continue

        thesis_courses = set(
            config["student_progress"]["graduation"]["thesis_course_codes"]
        )
        thesis_eligible = (
            str(getattr(student, "english_pass", False)).casefold() == "true"
            and ctxh_days_before_semester(student, semester_code)
            >= config["student_progress"]["ctxh"]["minimum_for_thesis"]
        )
        exempted_english = get_exempted_english_courses(student, config)

        def course_is_available(course_code):
            if course_code in exempted_english:
                return False
            return course_code not in thesis_courses or thesis_eligible

        prefix = str(student.student_id)[:2]
        scheduled = scheduled_courses.get(prefix)
        if scheduled is None:
            continue
        passed_courses = passed.get(student.student_id, set())
        failed_courses = failed.get(student.student_id, set())
        thesis_pending = any(
            code in thesis_courses and code not in passed_courses
            for code in scheduled
        )
        if thesis_pending and not thesis_eligible:
            empty_semester_probability = config["student_progress"][
                "graduation"
            ]["ineligible_thesis_empty_semester_probability"]
            pause_rng = np.random.default_rng(
                _stable_seed(
                    student_id,
                    config,
                    f"empty-thesis-semester:{semester_code}",
                )
            )
            if pause_rng.random() < empty_semester_probability:
                eligibility[student.student_id] = []
                continue
        scheduled = [code for code in scheduled if course_is_available(code)]
        extras = additional_course_groups.get(prefix, [])
        extras = [code for code in extras if course_is_available(code)]
        elective_groups = required_elective_groups.get(prefix, {})
        elective_groups = {
            name: [code for code in courses if course_is_available(code)]
            for name, courses in elective_groups.items()
        }
        optional_groups = optional_elective_groups.get(prefix, {})
        optional_groups = {
            name: [code for code in courses if course_is_available(code)]
            for name, courses in optional_groups.items()
        }
        credit_targets = required_elective_credits.get(prefix, {})
        choice_groups = required_choice_groups.get(prefix, {})
        choice_groups = {
            name: [code for code in courses if course_is_available(code)]
            for name, courses in choice_groups.items()
        }
        selected = []
        registered_credits = 0
        chosen_courses = set()
        for group_name, candidates in choice_groups.items():
            available = [
                code for code in candidates
                if code in credits
                and code not in passed_courses
                and all(
                    prerequisite in passed_courses or prerequisite in exempted_english
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
            and course_is_available(code)
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
                prerequisite in passed_courses or prerequisite in exempted_english
                for prerequisite in tq_rules.get(code, [])
            ):
                continue
            selected.append(code)
            registered_credits += credits[code]
        free_codes = (
            get_free_course_codes()
            | set(elective_groups.get("FREE", []))
            | set(optional_groups.get("FREE", []))
        )
        group_c_codes = (
            get_group_c_course_codes()
            | set(elective_groups.get("GROUP_C", []))
            | set(optional_groups.get("GROUP_C", []))
        )
        for group_name, target in credit_targets.items():
            candidates = elective_groups.get(group_name, [])
            current_all = passed_courses | set(selected)
            if group_name == "FREE" and sum(credits.get(code, 0) for code in current_all if code in free_codes) >= free_credit_limit:
                continue
            if group_name == "GROUP_C" and sum(credits.get(code, 0) for code in current_all if code in group_c_codes) >= group_c_credit_limit:
                continue
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
                if group_name == "FREE" and sum(credits.get(c, 0) for c in (passed_courses | set(selected)) if c in get_free_course_codes()) >= free_credit_limit:
                    break
                if group_name == "GROUP_C" and sum(credits.get(c, 0) for c in (passed_courses | set(selected)) if c in get_group_c_course_codes()) >= group_c_credit_limit:
                    break
                if not all(
                    prerequisite in passed_courses or prerequisite in exempted_english
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
            config,
        )
        optional_at_16 = (
            registered_credits == 16
            and allows_optional_course_at_16(student.student_id, config)
        )
        can_fill_gap = (
            registered_credits < TUITION_BASELINE_CREDITS
            and (
                registered_credits <= optional_threshold
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
                        prerequisite in passed_courses or prerequisite in exempted_english
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
                if acceleration or registered_credits <= optional_threshold
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
                current_all = passed_courses | set(selected)
                completed_free = sum(
                    credits.get(c, 0) for c in current_all if c in free_codes
                )
                completed_group_c = sum(
                    credits.get(c, 0) for c in current_all if c in group_c_codes
                )
                available = [
                    (source_group, code)
                    for source_group, code in peer_stage
                    if code not in passed_courses
                    and code not in selected
                    and not (source_group == "FREE" and completed_free >= free_credit_limit)
                    and not (source_group == "GROUP_C" and completed_group_c >= group_c_credit_limit)
                    and all(
                        prerequisite in passed_courses or prerequisite in exempted_english
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
            and registered_credits < TUITION_BASELINE_CREDITS
        ):
            for code in extras:
                if registered_credits >= TUITION_BASELINE_CREDITS:
                    break
                if code in passed_courses or code in selected:
                    continue
                if not all(
                    prerequisite in passed_courses or prerequisite in exempted_english
                    for prerequisite in tq_rules.get(code, [])
                ):
                    continue
                if registered_credits + credits[code] > MAX_CREDITS:
                    continue
                selected.append(code)
                registered_credits += credits[code]
        eligibility[student.student_id] = selected
    return eligibility, failed
