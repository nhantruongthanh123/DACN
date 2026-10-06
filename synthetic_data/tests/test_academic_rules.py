import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

RULES_DIR = Path(__file__).resolve().parents[1] / "rules"
sys.path.insert(0, str(RULES_DIR))

from academic_rules import (
    GENERATOR_CONFIG,
    add_gpa_summaries,
    allocate_course_rosters,
    balanced_class_sizes,
    calculate_eligibility_for_schedule,
    convert_score_to_grade,
    course_mean_score,
    filter_students_from_2013,
    generate_observed_score,
    generate_student_profile,
    students_by_course_from_eligibility,
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

        self.assertTrue(pd.isna(result.loc[0, "final_gpa_4"]))


if __name__ == "__main__":
    unittest.main()
