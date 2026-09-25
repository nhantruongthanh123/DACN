import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


COMPONENTS = ["quiz", "lab", "btl", "giua_ky", "cuoi_ky"]
GROUPS = [
    "NON_ELECTIVE",
    "ELECTIVE_GROUP_A",
    "ELECTIVE_GROUP_B",
    "ELECTIVE_GROUP_C",
    "ELECTIVE_MANAGEMENT",
]


def clip(x, lo=0.0, hi=10.0):
    return float(np.clip(x, lo, hi))


def score_to_letter(score):
    # Simple 10-point -> letter mapping.
    if score >= 8.5:
        return "A"
    if score >= 8.0:
        return "B+"
    if score >= 7.0:
        return "B"
    if score >= 6.5:
        return "C+"
    if score >= 5.5:
        return "C"
    if score >= 5.0:
        return "D+"
    if score >= 4.0:
        return "D"
    return "F"


def score_to_4(score):
    if score >= 8.5:
        return 4.0
    if score >= 8.0:
        return 3.5
    if score >= 7.0:
        return 3.0
    if score >= 6.5:
        return 2.5
    if score >= 5.5:
        return 2.0
    if score >= 5.0:
        return 1.5
    if score >= 4.0:
        return 1.0
    return 0.0


ACADEMIC_RANKS = (
    "YEU",
    "TRUNG_BINH",
    "TRUNG_BINH_KHA",
    "KHA",
    "GIOI",
    "XUAT_SAC",
)


def classify_gpa(gpa):
    if gpa < 2.0:
        return "YEU"
    if gpa < 2.4:
        return "TRUNG_BINH"
    if gpa < 2.8:
        return "TRUNG_BINH_KHA"
    if gpa < 3.2:
        return "KHA"
    if gpa < 3.6:
        return "GIOI"
    return "XUAT_SAC"


def cap_academic_rank(rank, retake_credits, improvement_credits):
    if retake_credits > 6:
        max_rank = "KHA"
    elif improvement_credits > 0:
        max_rank = "GIOI"
    else:
        return rank

    return ACADEMIC_RANKS[
        min(ACADEMIC_RANKS.index(rank), ACADEMIC_RANKS.index(max_rank))
    ]


def weighted_score(row):
    total = 0.0
    for c in COMPONENTS:
        total += row[c] * float(row[f"{c}_weight"]) / 100.0
    return clip(total)


def choose_electives(course_df, rng):
    """Mandatory = all NON_ELECTIVE.
    Electives: 5 from C, 1 from A, 1 from B, 1 from MANAGEMENT.
    """
    selected = list(course_df.loc[
        course_df["course_group"] == "NON_ELECTIVE", "course_code"
    ])

    rules = {
        "ELECTIVE_GROUP_C": 5,
        "ELECTIVE_GROUP_A": 1,
        "ELECTIVE_GROUP_B": 1,
        "ELECTIVE_MANAGEMENT": 1,
    }

    for group, n in rules.items():
        pool = course_df.loc[
            course_df["course_group"] == group, "course_code"
        ].tolist()
        if len(pool) < n:
            raise ValueError(f"Not enough courses in {group}: need {n}, have {len(pool)}")
        selected.extend(rng.choice(pool, size=n, replace=False).tolist())

    return set(selected)



def add_prerequisite_closure(selected_codes, prereq):
    """If a selected course has prerequisites, include them automatically."""
    selected = set(selected_codes)
    changed = True
    while changed:
        changed = False
        for course in list(selected):
            for prerequisite in prereq.get(course, set()):
                if prerequisite not in selected:
                    selected.add(prerequisite)
                    changed = True
    return selected


def build_prerequisites(prereq_df):
    """course_code -> set(related prerequisite course codes)."""
    prereq = {}
    for _, r in prereq_df.iterrows():
        course = str(r["course_code"])
        related = str(r["related_course_code"])
        prereq.setdefault(course, set()).add(related)
    return prereq


def make_course_order(selected_codes, course_df, prereq):
    """Topological order for the selected curriculum."""
    selected = set(selected_codes)
    deps = {
        c: {p for p in prereq.get(c, set()) if p in selected}
        for c in selected
    }

    order = []
    remaining = set(selected)

    while remaining:
        ready = sorted([c for c in remaining if not (deps[c] & remaining)])
        if not ready:
            # Defensive fallback if the source contains an unexpected cycle.
            order.extend(sorted(remaining))
            break
        order.extend(ready)
        remaining -= set(ready)

    return order


def choose_class(class_df, course_code, term_code, rng):
    """Pick the first class matching course + term.
    class.csv uses ids such as 231_L01_CH1003, where the first 3 chars are term code.
    """
    pool = class_df[
        (class_df["course_id"] == course_code)
        & (class_df["id"].astype(str).str[:3] == str(term_code))
    ].sort_values("id")

    if pool.empty:
        # Fallback: the first available class of that course.
        pool = class_df[class_df["course_id"] == course_code].sort_values("id")

    if pool.empty:
        return ""

    return str(pool.iloc[0]["id"])


def build_term_codes(start_cohort, max_terms):
    """Generate term codes: cohort*10+1, +2, +3, then next academic year."""
    # cohort 23 -> 231,232,233,241,242,243,...
    year = int(start_cohort)
    result = []
    for _ in range(max_terms):
        for sem in (1, 2, 3):
            if len(result) >= max_terms:
                break
            result.append(f"{year}{sem}")
        year += 1
    return result


def sample_ability(group_cfg, rng):
    return float(np.clip(
        rng.normal(group_cfg["mean"], group_cfg["std"]),
        float(group_cfg.get("min_ability", 3.0)),
        float(group_cfg.get("max_ability", 9.2)),
    ))


def generate_assessment(
    ability, difficulty, assessment_row, group_cfg, personality_cfg, rng, noise_cfg
):
    """Generate component scores first, then calculate weighted final score."""
    result = {}

    # A small course-level performance shock makes all components of a course
    # move together without making them identical.
    course_shock = rng.normal(0, 0.20)

    for c in COMPONENTS:
        weight = float(assessment_row[c])
        result[f"{c}_weight"] = weight

        if weight <= 0:
            result[c] = 0.0
            continue

        component_mean = (
            ability
            - difficulty
            + float(personality_cfg.get("score_offset", 0.0))
            + float(personality_cfg.get("component_offsets", {}).get(c, 0.0))
            + course_shock
        )
        noise = (
            float(noise_cfg.get(c, 0.8))
            * float(personality_cfg.get("noise_multiplier", 1.0))
        )
        result[c] = clip(rng.normal(component_mean, noise))

    # Convert the generated components to the actual weighted course score.
    result["final_score"] = weighted_score(result)
    return result


def pick_next_courses(remaining, completed, in_progress, course_df, prereq,
                      credits_limit, rng, blocked=None):
    """Greedily select ready courses for the current term."""
    blocked = blocked or set()
    candidates = []
    for code in remaining:
        if code in in_progress or code in blocked:
            continue
        requirements = prereq.get(code, set())
        if requirements.issubset(completed):
            candidates.append(code)

    # Shuffle first, then sort by credits so selection isn't always deterministic.
    rng.shuffle(candidates)
    candidates.sort(
        key=lambda c: int(course_df.loc[
            course_df["course_code"] == c, "credits"
        ].iloc[0])
    )

    selected = []
    credits = 0
    for code in candidates:
        cr = int(course_df.loc[
            course_df["course_code"] == code, "credits"
        ].iloc[0])

        if credits + cr <= credits_limit:
            selected.append(code)
            credits += cr

    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="input")
    parser.add_argument("--output", default="generated")
    parser.add_argument("--config", default="config.json")
    parser.add_argument(
        "--limit-students",
        type=int,
        default=None,
        help="Process only the first N students.",
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    rng = np.random.default_rng(int(cfg["seed"]))

    student_df = pd.read_csv(input_dir / "student.csv")
    if args.limit_students is not None:
        if args.limit_students < 1:
            raise ValueError("--limit-students must be greater than 0")
        student_df = student_df.head(args.limit_students)
    course_df = pd.read_csv(input_dir / "course.csv")
    assessment_df = pd.read_csv(input_dir / "assessment.csv")
    prereq_df = pd.read_csv(input_dir / "course_prerequisite.csv")
    class_df = pd.read_csv(input_dir / "class.csv")

    # Normalize IDs to strings.
    student_df["user_id"] = student_df["user_id"].astype(str)
    course_df["course_code"] = course_df["course_code"].astype(str)
    assessment_df["course_id"] = assessment_df["course_id"].astype(str)
    prereq_df["course_code"] = prereq_df["course_code"].astype(str)
    prereq_df["related_course_code"] = prereq_df["related_course_code"].astype(str)
    class_df["course_id"] = class_df["course_id"].astype(str)

    # Assessment lookup.
    assess = assessment_df.set_index("course_id").to_dict("index")
    prereq = build_prerequisites(prereq_df)

    # Map course code -> course metadata.
    course_meta = course_df.set_index("course_code").to_dict("index")

    # Build target group labels using proportions.
    group_names = list(cfg["ability_groups"].keys())
    probs = np.array([
        cfg["ability_groups"][g]["proportion"] for g in group_names
    ], dtype=float)
    probs = probs / probs.sum()

    personality_names = list(cfg["personality_profiles"].keys())
    personality_probs = np.array([
        cfg["personality_profiles"][p]["proportion"]
        for p in personality_names
    ], dtype=float)
    if personality_probs.sum() <= 0:
        raise ValueError("personality_profiles proportions must sum to a positive value")
    personality_probs = personality_probs / personality_probs.sum()

    student_rows = []
    attempt_rows = []

    for _, s in student_df.iterrows():
        user_id = str(s["user_id"])
        cohort = user_id[:2]

        group = str(rng.choice(group_names, p=probs))
        group_cfg = cfg["ability_groups"][group]
        ability = sample_ability(group_cfg, rng)
        personality = str(rng.choice(personality_names, p=personality_probs))
        personality_cfg = cfg["personality_profiles"][personality]

        curriculum = choose_electives(course_df, rng)
        curriculum = add_prerequisite_closure(curriculum, prereq)
        order = make_course_order(curriculum, course_df, prereq)

        # Status for the student is intentionally NOT graduation/dropout.
        # DROPOUT here only means a higher failure tendency; final dropout
        # labeling is left for a later stage.
        remaining = set(order)
        completed = set()
        failed_attempts = {}   # course -> number of failed attempts
        blocked_courses = set()
        term_codes = build_term_codes(cohort, int(cfg["max_terms"]))

        for term_code in term_codes:
            if not remaining:
                break

            # A student can take a normal load every term.
            selected = pick_next_courses(
                remaining=remaining,
                completed=completed,
                in_progress=set(),
                course_df=course_df,
                prereq=prereq,
                credits_limit=int(cfg["max_credits_per_term"]),
                rng=rng,
                blocked=blocked_courses,
            )

            # If prerequisites or ordering create no ready course, stop.
            if not selected:
                continue

            for code in selected:
                meta = course_meta[code]
                arow = assess.get(code)

                if arow is None:
                    raise ValueError(f"Missing assessment rule for {code}")

                credits = int(meta["credits"])
                group_modifier = float(
                    cfg["course_group_difficulty"].get(meta["course_group"], 0.0)
                )

                # Larger-credit courses are only slightly harder.
                difficulty = (
                    group_modifier
                    + 0.08 * max(0, credits - 3)
                    + rng.normal(0, 0.12)
                )

                # First attempt: group-specific fail tendency.
                fail_rate = float(group_cfg["fail_rate"])

                # Retakes get another independent roll.
                attempt_no = failed_attempts.get(code, 0) + 1

                scores = generate_assessment(
                    ability=ability,
                    difficulty=difficulty,
                    assessment_row=arow,
                    group_cfg=group_cfg,
                    personality_cfg=personality_cfg,
                    rng=rng,
                    noise_cfg=cfg["component_noise"],
                )

                # Roll an additional fail event for realism.
                # A low score naturally fails; this small event allows occasional
                # surprising failures/pass outcomes without dominating the grade.
                event = rng.random()
                forced_fail = event < max(0.0, fail_rate - 0.05)

                final_score = scores["final_score"]
                passed = (final_score >= float(cfg["pass_score"])) and not forced_fail

                # If the random fail event triggers, pull the final score down
                # instead of creating an inconsistent "F with 8.0" record.
                if forced_fail and final_score >= float(cfg["pass_score"]):
                    final_score = clip(
                        float(cfg["pass_score"]) - rng.uniform(0.05, 0.80)
                    )
                    scores["final_score"] = final_score

                status = "PASS" if passed else "FAIL"

                class_id = choose_class(
                    class_df, code, term_code, rng
                )

                row = {
                    "user_id": user_id,
                    "cohort": cohort,
                    "ability_group": group,
                    "personality": personality,
                    "term_code": term_code,
                    "course_code": code,
                    "course_name": meta["course_name"],
                    "credits": credits,
                    "course_group": meta["course_group"],
                    "class_id": class_id,
                    "attempt_no": attempt_no,
                    "status": status,
                    "final_score": round(final_score, 3),
                    "letter_grade": score_to_letter(final_score),
                    "grade_4": score_to_4(final_score),
                }

                for c in COMPONENTS:
                    row[c] = round(float(scores[c]), 3)
                    row[f"{c}_weight"] = float(arow[c])

                attempt_rows.append(row)

                if passed:
                    completed.add(code)
                    remaining.discard(code)
                    failed_attempts.pop(code, None)
                else:
                    failed_attempts[code] = attempt_no

                    # The course stays in remaining and becomes available again
                    # next term. Maximum retakes prevents infinite loops.
                    if attempt_no >= int(cfg["max_retakes"]):
                        # Stop scheduling this unresolved course after the
                        # configured number of failed attempts.
                        blocked_courses.add(code)
                        remaining.discard(code)

        student_rows.append({
            "user_id": user_id,
            "cohort": cohort,
            "ability_group": group,
            "personality": personality,
            "ability": round(ability, 3),
            "courses_completed": len({
                r["course_code"] for r in attempt_rows
                if r["user_id"] == user_id and r["status"] == "PASS"
            }),
        })

    attempts = pd.DataFrame(attempt_rows)
    students = pd.DataFrame(student_rows)

    # Summary: actual score distribution generated by the current config.
    bins = [-0.001, 2, 4, 5, 6, 7, 8, 9, 10.001]
    labels = ["0-2", "2-4", "4-5", "5-6", "6-7", "7-8", "8-9", "9-10"]
    if not attempts.empty:
        attempts["score_bin"] = pd.cut(
            attempts["final_score"], bins=bins, labels=labels, right=False
        )
        distribution = (
            attempts["score_bin"]
            .value_counts(sort=False)
            .rename("count")
            .to_frame()
        )
        distribution["proportion"] = distribution["count"] / len(attempts)
    else:
        distribution = pd.DataFrame(columns=["count", "proportion"])

    # Per-student GPA over passed, credit-bearing attempts only.
    passed = attempts[
        (attempts["status"] == "PASS") & (attempts["credits"] > 0)
    ].copy()
    if not passed.empty:
        passed["weighted_grade"] = passed["grade_4"] * passed["credits"]
        gpa = (
            passed.groupby("user_id", as_index=False)
            .agg(weighted_grade=("weighted_grade", "sum"), credits=("credits", "sum"))
        )
        gpa["gpa_4"] = gpa["weighted_grade"] / gpa["credits"]
        gpa = gpa[["user_id", "gpa_4"]]
    else:
        gpa = pd.DataFrame(columns=["user_id", "gpa_4"])

    students = students.merge(gpa, on="user_id", how="left")
    students["gpa_4"] = students["gpa_4"].fillna(0).round(3)

    attempt_summary = attempts.sort_values(
        ["user_id", "course_code", "attempt_no"]
    ).groupby(["user_id", "course_code"], as_index=False).agg(
        credits=("credits", "first"),
        failed=("status", lambda statuses: (statuses == "FAIL").any()),
        improvement=("attempt_no", lambda attempts: len(attempts) > 1),
    )
    repeat_summary = attempt_summary.groupby("user_id", as_index=False).agg(
        retake_credits=("credits", lambda credits: 0),
        improvement_credits=("credits", lambda credits: 0),
    )
    if not attempt_summary.empty:
        attempt_summary["retake_credits"] = attempt_summary["credits"].where(
            attempt_summary["failed"], 0
        )
        attempt_summary["improvement_credits"] = attempt_summary["credits"].where(
            attempt_summary["improvement"] & ~attempt_summary["failed"], 0
        )
        repeat_summary = attempt_summary.groupby("user_id", as_index=False).agg(
            retake_credits=("retake_credits", "sum"),
            improvement_credits=("improvement_credits", "sum"),
        )

    students = students.merge(repeat_summary, on="user_id", how="left")
    students[["retake_credits", "improvement_credits"]] = students[
        ["retake_credits", "improvement_credits"]
    ].fillna(0).astype(int)
    students["academic_classification"] = students.apply(
        lambda row: cap_academic_rank(
            classify_gpa(row["gpa_4"]),
            row["retake_credits"],
            row["improvement_credits"],
        ),
        axis=1,
    )

    attempts.drop(columns=["score_bin"], errors="ignore").to_csv(
        output_dir / "student_course_attempts.csv", index=False
    )
    class_assessments = attempts.drop(columns=["score_bin"], errors="ignore")
    class_assessments.to_csv(output_dir / "class_assessments.csv", index=False)
    students.to_csv(output_dir / "student_profile.csv", index=False)
    distribution.to_csv(output_dir / "score_distribution.csv")

    print(f"Generated {len(students):,} students")
    print(f"Generated {len(attempts):,} course attempts")
    print(f"Saved to: {output_dir.resolve()}")
    print("\nScore distribution:")
    print(distribution.to_string())


if __name__ == "__main__":
    main()
