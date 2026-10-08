import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

RULES_DIR = Path(__file__).resolve().parents[1] / "rules"
sys.path.insert(0, str(RULES_DIR))

from academic_rules import (
    DISMISSAL_AFTER_SEMESTERS,
    FREE_CREDIT_LIMIT,
    GENERATOR_CONFIG,
    GROUP_C_CREDIT_LIMIT,
    MAX_LATE_SEMESTERS,
    STANDARD_SEMESTERS,
    academic_dismissal_semesters,
    academic_suspension_semesters,
    add_gpa_summaries,
    allocate_course_rosters,
    balanced_class_sizes,
    calculate_eligibility_for_schedule,
    convert_score_to_grade,
    course_mean_score,
    filter_students_from_2013,
    generate_observed_score,
    generate_student_profile,
    get_academic_dismissal_semester,
    get_exempted_english_courses,
    get_late_semesters_count,
    is_academic_dismissal,
    is_late_semester,
    semester_from_index,
    semester_index,
    students_by_course_from_eligibility,
    validate_generator_config,
    wants_acceleration,
)


class AcademicScoreRulesTests(unittest.TestCase):
    def test_cohort_filter_keeps_real_students_from_2013_onward(self):
        students = pd.DataFrame({
            "student_id": ["1210001", "1310001", "1610001", "2310001"],
            "name": ["old", "2013", "2016", "2023"],
        })

        result = filter_students_from_2013(students)

        self.assertEqual(
            result["student_id"].tolist(),
            ["1310001", "1610001", "2310001"],
        )

    def test_class_sections_are_balanced_and_respect_capacity(self):
        self.assertEqual(balanced_class_sizes(0), [])
        self.assertEqual(balanced_class_sizes(39), [39])
        self.assertEqual(balanced_class_sizes(120), [120])
        self.assertEqual(balanced_class_sizes(121), [61, 60])
        self.assertEqual(balanced_class_sizes(241), [81, 80, 80])

    def test_course_rosters_assign_every_student_to_available_matching_classes(self):
        eligibility = {
            "2310001": ["CO1001", "CO1002"],
            "2310002": ["CO1001"],
            "2310003": ["CO1001"],
        }
        students_by_course = students_by_course_from_eligibility(eligibility)
        classes = pd.DataFrame({
            "class_id": ["CO1001-L01", "CO1002-L01"],
            "course_code": ["CO1001", "CO1002"],
        })

        rosters = allocate_course_rosters(students_by_course, classes)

        self.assertEqual(
            {
                course: [
                    student_id
                    for _, roster in assignments
                    for student_id in roster
                ]
                for course, assignments in rosters.items()
            },
            students_by_course,
        )
        self.assertTrue(all(
            len(roster) <= 120
            for assignments in rosters.values()
            for _, roster in assignments
        ))

    def test_course_roster_fails_when_available_classes_cannot_cover_demand(self):
        eligible = {"CO1001": [f"231{index:04d}" for index in range(121)]}
        classes = pd.DataFrame({
            "class_id": ["CO1001-L01"],
            "course_code": ["CO1001"],
        })

        with self.assertRaisesRegex(ValueError, "needs 2 classes"):
            allocate_course_rosters(eligible, classes)

    def test_course_roster_fails_when_an_eligible_course_has_no_class(self):
        with self.assertRaisesRegex(ValueError, "No existing class"):
            allocate_course_rosters(
                {"CO1001": ["2310001"]},
                pd.DataFrame(columns=["class_id", "course_code"]),
            )

    def test_profile_is_reproducible_and_within_configured_ranges(self):
        first = generate_student_profile("2310001")
        second = generate_student_profile("2310001")

        self.assertEqual(first, second)
        self.assertIsInstance(first["english_pass"], bool)
        self.assertIsInstance(first["ctxh_days_by_semester"], list)
        self.assertTrue(all(
            earlier["cumulative_days"] <= later["cumulative_days"]
            for earlier, later in zip(
                first["ctxh_days_by_semester"],
                first["ctxh_days_by_semester"][1:],
            )
        ))
        for field in (
            "discipline",
            "motivation",
            "stress",
            "social_activity",
            "academic_level",
            "math_level",
            "english_level",
        ):
            self.assertIn(first[field], range(1, 6))

    def test_thesis_course_requires_english_and_prior_ctxh_days(self):
        history = pd.DataFrame(columns=[
            "student_id", "course_code", "semester", "status",
        ])
        prerequisites = pd.DataFrame(columns=[
            "course_code", "related_course_code", "relation_type",
        ])
        students = pd.DataFrame([
            {
                "student_id": "2310001",
                "base_score": 6.5,
                "english_pass": True,
                "ctxh_days_by_semester": [
                    {"semester": "HK231", "cumulative_days": 12},
                ],
            },
            {
                "student_id": "2310002",
                "base_score": 6.5,
                "english_pass": False,
                "ctxh_days_by_semester": [
                    {"semester": "HK231", "cumulative_days": 15},
                ],
            },
            {
                "student_id": "2310003",
                "base_score": 6.5,
                "english_pass": True,
                "ctxh_days_by_semester": [
                    {"semester": "HK231", "cumulative_days": 11},
                ],
            },
        ])
        thesis_pause_config = {
            **GENERATOR_CONFIG,
            "student_progress": {
                **GENERATOR_CONFIG["student_progress"],
                "graduation": {
                    **GENERATOR_CONFIG["student_progress"]["graduation"],
                    "ineligible_thesis_empty_semester_probability": 1.0,
                },
            },
        }

        eligible, _ = calculate_eligibility_for_schedule(
            students,
            history,
            {"CO4029": 2, "CO1001": 3},
            prerequisites,
            {"23": ["CO4029", "CO1001"]},
            {},
            semester_code="HK241",
            config=thesis_pause_config,
        )

        self.assertEqual(eligible, {
            "2310001": ["CO4029", "CO1001"],
            "2310002": [],
            "2310003": [],
        })

    def test_two_low_credit_terms_trigger_only_one_suspension_term(self):
        history = pd.DataFrame([
            {
                "student_id": "1310001",
                "course_code": "CO0001",
                "semester": semester_index("HK131"),
                "status": "Pass",
            },
            {
                "student_id": "1310001",
                "course_code": "CO0002",
                "semester": semester_index("HK132"),
                "status": "Pass",
            },
            {
                "student_id": "1310001",
                "course_code": "CO0003",
                "semester": semester_index("HK142"),
                "status": "Pass",
            },
        ])
        credits = {
            "CO0001": 5,
            "CO0002": 5,
            "CO0003": 5,
        }
        semesters = [
            "HK131", "HK132", "HK141", "HK142",
            "HK151", "HK152", "HK161",
        ]

        suspensions = academic_suspension_semesters(
            history, semesters, credits
        )

        self.assertEqual(suspensions, {"HK141", "HK152"})

    def test_suspended_student_cannot_enroll_then_can_resume_next_term(self):
        history = pd.DataFrame([
            {
                "student_id": "1310001",
                "course_code": "CO0001",
                "semester": semester_index("HK131"),
                "status": "Pass",
            },
            {
                "student_id": "1310001",
                "course_code": "CO0002",
                "semester": semester_index("HK132"),
                "status": "Pass",
            },
        ])
        students = pd.DataFrame([{
            "student_id": "1310001",
            "base_score": 6.5,
            "english_pass": True,
            "ctxh_days_by_semester": [],
        }])
        prerequisites = pd.DataFrame(columns=[
            "course_code", "related_course_code", "relation_type",
        ])
        credits = {
            "CO0001": 5,
            "CO0002": 5,
            "CO1001": 3,
        }
        scheduled = {"13": ["CO1001"]}

        paused, _ = calculate_eligibility_for_schedule(
            students,
            history,
            credits,
            prerequisites,
            scheduled,
            {},
            semester_code="HK141",
        )
        resumed, _ = calculate_eligibility_for_schedule(
            students,
            history,
            credits,
            prerequisites,
            scheduled,
            {},
            semester_code="HK142",
        )

        self.assertEqual(paused, {"1310001": []})
        self.assertEqual(resumed, {"1310001": ["CO1001"]})

    def test_stronger_profile_is_less_affected_by_course_difficulty(self):
        low_profile = {
            "student_id": "low",
            "academic_level": 1,
            "discipline": 1,
            "motivation": 1,
            "stress": 5,
        }
        high_profile = {
            "student_id": "high",
            "academic_level": 5,
            "discipline": 5,
            "motivation": 5,
            "stress": 1,
        }
        easy_config = {
            **GENERATOR_CONFIG,
            "difficulty": {
                **GENERATOR_CONFIG["difficulty"],
                "course_overrides": {"CO9999": 1},
            },
        }
        hard_config = {
            **GENERATOR_CONFIG,
            "difficulty": {
                **GENERATOR_CONFIG["difficulty"],
                "course_overrides": {"CO9999": 5},
            },
        }

        low_change = course_mean_score(
            low_profile, "CO9999", 0, hard_config
        ) - course_mean_score(low_profile, "CO9999", 0, easy_config)
        high_change = course_mean_score(
            high_profile, "CO9999", 0, hard_config
        ) - course_mean_score(high_profile, "CO9999", 0, easy_config)

        self.assertLess(abs(high_change), abs(low_change))

    def test_grade_boundaries_are_lower_inclusive(self):
        cases = {
            3.99: ("F", 0.0),
            4.0: ("D", 1.0),
            5.0: ("D+", 1.5),
            5.5: ("C", 2.0),
            6.4: ("C+", 2.5),
            7.0: ("B", 3.0),
            8.0: ("B+", 3.5),
            8.5: ("A", 4.0),
            9.5: ("A+", 4.0),
            10.0: ("A+", 4.0),
        }
        for score, expected in cases.items():
            with self.subTest(score=score):
                self.assertEqual(convert_score_to_grade(score), expected)

    def test_scores_are_clipped_and_gpa_summaries_are_credit_weighted(self):
        rng = np.random.default_rng(42)
        scores = [
            generate_observed_score(6.0, rng)
            for _ in range(1000)
        ]
        self.assertTrue(all(0 <= score <= 10 for score in scores))

        history = pd.DataFrame([{
            "student_id": "s1",
            "course_code": "CO1001",
            "final_score": 8.5,
        }])
        current = pd.DataFrame([
            {
                "student_id": "s1",
                "course_id": "CO1002",
                "final_score": 3.9,
                "gpa_4": 0.0,
            },
            {
                "student_id": "s1",
                "course_id": "CO1003",
                "final_score": 4.5,
                "gpa_4": 1.0,
            },
        ])

        result = add_gpa_summaries(
            current,
            history,
            {"CO1001": 3, "CO1002": 3, "CO1003": 3},
        )

        self.assertEqual(result["semester_gpa_4"].tolist(), [0.5, 0.5])
        self.assertEqual(result["final_gpa_4"].tolist(), [2.5, 2.5])

    def test_zero_credit_pass_does_not_divide_by_zero_in_cumulative_gpa(self):
        result = add_gpa_summaries(
            pd.DataFrame([{
                "student_id": "s1",
                "course_id": "CO0000",
                "final_score": 8.5,
                "gpa_4": 4.0,
            }]),
            pd.DataFrame(columns=["student_id", "course_code", "final_score"]),
            {"CO0000": 0},
        )

    def test_exempted_english_courses_exempts_all_when_english_pass_is_true(self):
        student = {"student_id": "1300001", "english_pass": True, "english_level": 2}
        exempted = get_exempted_english_courses(student)
        self.assertEqual(exempted, {"LA1003", "LA1005", "LA1007", "LA1009"})

    def test_exempted_english_courses_placement_when_english_pass_is_false(self):
        # Level 1 student never skips more than LA1003 and never skips LA1009
        student_l1 = {"student_id": "1300002", "english_pass": False, "english_level": 1}
        exempted_l1 = get_exempted_english_courses(student_l1)
        self.assertTrue(exempted_l1.issubset({"LA1003"}))
        self.assertNotIn("LA1009", exempted_l1)

        # Level 5 student skips early courses but still must learn LA1009
        student_l5 = {"student_id": "1300003", "english_pass": False, "english_level": 5}
        exempted_l5 = get_exempted_english_courses(student_l5)
        self.assertEqual(exempted_l5, {"LA1003", "LA1005", "LA1007"})
        self.assertNotIn("LA1009", exempted_l5)

    def test_calculate_eligibility_exempted_english_satisfies_prerequisites(self):
        # Student exempt from LA1003: LA1003 should not be scheduled, but LA1005 can be scheduled
        students = pd.DataFrame([{
            "student_id": "1300003",
            "base_score": 6.5,
            "english_pass": False,
            "english_level": 5,  # skips LA1003, LA1005, LA1007
        }])
        history = pd.DataFrame(columns=["student_id", "course_code", "status"])
        prerequisites = pd.DataFrame([
            {"course_code": "LA1005", "related_course_code": "LA1003", "relation_type": "TQ"},
            {"course_code": "LA1009", "related_course_code": "LA1007", "relation_type": "TQ"},
        ])
        credits = {"LA1003": 2, "LA1005": 2, "LA1009": 2}
        scheduled = {"13": ["LA1003", "LA1009"]}

        eligible, _ = calculate_eligibility_for_schedule(
            students,
            history,
            credits,
            prerequisites,
            scheduled,
            {},
            semester_code="HK142",
        )
        # LA1003 was exempted so not in eligible; LA1009 had prerequisite LA1007 which was exempted, so satisfied!
        self.assertNotIn("LA1003", eligible["1300003"])
        self.assertIn("LA1009", eligible["1300003"])

    def test_student_switches_course_type_when_elective_limit_reached(self):
        # Student 1310001 has passed 15 credits of GROUP_C courses
        # and needs to register courses for the semester
        students = pd.DataFrame([{
            "student_id": "1310001",
            "base_score": 7.0,
            "english_pass": True,
        }])
        # 5 courses * 3 credits = 15 credits from actual GROUP_C courses
        passed_group_c = ["CO3011", "CO3013", "CO3015", "CO3017", "CO3021"]
        history = pd.DataFrame([
            {"student_id": "1310001", "course_code": code, "status": "Pass"}
            for code in passed_group_c
        ])
        prerequisites = pd.DataFrame(columns=["course_code", "related_course_code", "relation_type"])
        credits = {code: 3 for code in passed_group_c}
        credits.update({"CO3023": 3, "CO3027": 3, "IM1011": 3, "IM1021": 3, "EXTRA01": 3})

        free_candidates = ["IM1011", "IM1021"]
        group_c_candidates = ["CO3023", "CO3027"]

        eligible, _ = calculate_eligibility_for_schedule(
            students,
            history,
            credits,
            prerequisites,
            {"13": []},
            {"13": ["EXTRA01"]},
            {"13": {"FREE": free_candidates, "GROUP_C": group_c_candidates}},
            {"13": {"FREE": free_candidates, "GROUP_C": group_c_candidates}},
            semester_code="HK161",
        )

        selected = eligible["1310001"]
        # Since student already passed 15 credits of GROUP_C, no more GROUP_C should be selected!
        for c in group_c_candidates:
            self.assertNotIn(c, selected)
        # FREE candidates should be selected instead
        self.assertTrue(any(c in selected for c in free_candidates))

        # Scenario 2: Student has passed BOTH 15 credits of GROUP_C AND 9 credits of FREE
        passed_both = passed_group_c + ["IM1011", "IM1021", "IM1019"]
        history_both = pd.DataFrame([
            {"student_id": "1310001", "course_code": code, "status": "Pass"}
            for code in passed_both
        ])
        credits.update({"IM1019": 3})
        eligible_both, _ = calculate_eligibility_for_schedule(
            students,
            history_both,
            credits,
            prerequisites,
            {"13": []},
            {"13": ["EXTRA01"]},
            {"13": {"FREE": free_candidates, "GROUP_C": group_c_candidates}},
            {"13": {"FREE": free_candidates, "GROUP_C": group_c_candidates}},
            semester_code="HK161",
        )
        selected_both = eligible_both["1310001"]
        # No FREE and no GROUP_C should be selected!
        for c in group_c_candidates + free_candidates:
            self.assertNotIn(c, selected_both)
        # Other course type (EXTRA01) should be selected instead!
        self.assertIn("EXTRA01", selected_both)

    def test_constants_and_semester_from_index(self):
        self.assertEqual(STANDARD_SEMESTERS, 8)
        self.assertEqual(MAX_LATE_SEMESTERS, 4)
        self.assertEqual(DISMISSAL_AFTER_SEMESTERS, 12)

        self.assertEqual(semester_from_index(-19), "HK131")
        self.assertEqual(semester_from_index(-12), "HK162")
        self.assertEqual(semester_from_index(-7), "HK191")

        for year in range(13, 26):
            for term in (1, 2):
                code = f"HK{year}{term}"
                self.assertEqual(semester_from_index(semester_index(code)), code)

    def test_late_semesters_count(self):
        # Student K13 starts at HK131
        student_id = "1310001"
        # Semesters 1-8: standard duration, late count = 0
        self.assertEqual(get_late_semesters_count(student_id, "HK131"), 0)
        self.assertEqual(get_late_semesters_count(student_id, "HK162"), 0)

        # Semesters 9-12: allowed late semesters (1 to 4)
        self.assertEqual(get_late_semesters_count(student_id, "HK171"), 1)
        self.assertEqual(get_late_semesters_count(student_id, "HK172"), 2)
        self.assertEqual(get_late_semesters_count(student_id, "HK181"), 3)
        self.assertEqual(get_late_semesters_count(student_id, "HK182"), 4)

        # Semester 13: exceeding 12 semesters (late count = 5)
        self.assertEqual(get_late_semesters_count(student_id, "HK191"), 5)

        # Unknown cohort returns 0
        self.assertEqual(get_late_semesters_count("9910001", "HK191"), 0)

    def test_academic_dismissal_logic(self):
        student_id = "1310001"
        # Semesters 1-12: NOT dismissed
        for sem in ["HK131", "HK141", "HK151", "HK161", "HK162", "HK171", "HK172", "HK181", "HK182"]:
            self.assertFalse(
                is_academic_dismissal(student_id, sem),
                f"Student should not be dismissed at {sem}",
            )

        # Semester 13+ (HK191 onward): Dismissed
        self.assertTrue(is_academic_dismissal(student_id, "HK191"))
        self.assertTrue(is_academic_dismissal(student_id, "HK192"))

        # Dismissal trigger semester
        self.assertEqual(get_academic_dismissal_semester(student_id), "HK191")
        self.assertEqual(get_academic_dismissal_semester("1610001"), "HK221")
        self.assertIsNone(get_academic_dismissal_semester("9910001"))

        # academic_dismissal_semesters set filtering
        sems = ["HK162", "HK182", "HK191", "HK192"]
        self.assertEqual(
            academic_dismissal_semesters(student_id, sems),
            {"HK191", "HK192"},
        )

    def test_calculate_eligibility_blocks_dismissed_student(self):
        students = pd.DataFrame([{
            "student_id": "1310001",
            "base_score": 7.0,
            "voluntary_dropout_semester": "",
            "english_pass": True,
            "ctxh_days": 15,
        }])
        history = pd.DataFrame(columns=["student_id", "course_code", "status"])
        credits = {"CO1001": 3}
        prerequisites = pd.DataFrame(
            columns=["course_code", "related_course_code", "relation_type"]
        )
        scheduled = {"13": ["CO1001"]}

        # Semester 12 (HK182): Still eligible
        eligible_12, _ = calculate_eligibility_for_schedule(
            students,
            history,
            credits,
            prerequisites,
            {"13": []},
            scheduled,
            {"13": {}},
            {"13": {}},
            semester_code="HK182",
        )
        self.assertEqual(eligible_12["1310001"], ["CO1001"])

        # Semester 13 (HK191): Exceeds 12 semesters -> blocked / dismissed
        eligible_13, _ = calculate_eligibility_for_schedule(
            students,
            history,
            credits,
            prerequisites,
            {"13": []},
            scheduled,
            {"13": {}},
            {"13": {}},
            semester_code="HK191",
        )
        self.assertEqual(eligible_13["1310001"], [])

    def test_is_late_semester(self):
        student_id = "1310001"
        # Semesters 1-8: Not late (standard time)
        for sem in ["HK131", "HK141", "HK151", "HK161", "HK162"]:
            self.assertFalse(is_late_semester(student_id, sem))

        # Semesters 9-12: Late within allowed window (1 to 4 late semesters)
        for sem in ["HK171", "HK172", "HK181", "HK182"]:
            self.assertTrue(is_late_semester(student_id, sem))

        # Semester 13: Exceeds allowed window (>4 late semesters -> dismissed)
        self.assertFalse(is_late_semester(student_id, "HK191"))

    def test_config_contains_constants_and_validation(self):
        progress = GENERATOR_CONFIG["student_progress"]
        self.assertEqual(progress["graduation"]["max_late_semesters"], 4)
        self.assertEqual(progress["electives"]["free_credit_limit"], 9)
        self.assertEqual(progress["electives"]["group_c_credit_limit"], 15)
        self.assertEqual(progress["enrollment_policy"]["optional_threshold"], 15)
        self.assertEqual(progress["enrollment_policy"]["acceleration_base_score"], 8.0)

        # Fallbacks in code
        self.assertEqual(FREE_CREDIT_LIMIT, 9)
        self.assertEqual(GROUP_C_CREDIT_LIMIT, 15)

        # Validation checks
        import copy
        bad_config = copy.deepcopy(GENERATOR_CONFIG)
        bad_config["student_progress"]["electives"]["free_credit_limit"] = -1
        with self.assertRaisesRegex(ValueError, "Invalid electives configuration"):
            validate_generator_config(bad_config)

        bad_policy = copy.deepcopy(GENERATOR_CONFIG)
        bad_policy["student_progress"]["enrollment_policy"]["acceleration_probability"] = 1.5
        with self.assertRaisesRegex(ValueError, "Invalid enrollment policy configuration"):
            validate_generator_config(bad_policy)

    def test_custom_config_overrides_electives_and_acceleration(self):
        import copy
        custom_config = copy.deepcopy(GENERATOR_CONFIG)
        # Raise acceleration score requirement to 9.5
        custom_config["student_progress"]["enrollment_policy"]["acceleration_base_score"] = 9.5
        # Student with score 8.5 does NOT get acceleration under this custom config
        self.assertFalse(wants_acceleration("1310001", 8.5, custom_config))


if __name__ == "__main__":
    unittest.main()


