import sys
import unittest
from pathlib import Path

import pandas as pd


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from generate_academic_metrics import _distribution_tables


class AcademicMetricsTests(unittest.TestCase):
    def test_score_and_letter_distributions_include_course_and_university(self):
        history = pd.DataFrame([
            {
                "course_code": "CO1001",
                "final_score": 9.7,
                "gpa_4": 4.0,
                "letter_grade": "A+",
            },
            {
                "course_code": "CO1001",
                "final_score": 6.5,
                "gpa_4": 2.5,
                "letter_grade": "C+",
            },
            {
                "course_code": "CO1002",
                "final_score": pd.NA,
                "gpa_4": pd.NA,
                "letter_grade": pd.NA,
            },
        ])

        scores, grades = _distribution_tables(history)

        self.assertEqual(set(scores["course_code"]), {"CO1001", "ALL_UNIVERSITY"})
        self.assertEqual(set(scores["scale"]), {"10-point", "4-point"})
        university_grades = grades[grades["course_code"] == "ALL_UNIVERSITY"]
        self.assertEqual(int(university_grades["count"].sum()), 2)
        self.assertAlmostEqual(float(university_grades["share"].sum()), 1.0)
        course_grades = grades[grades["course_code"] == "CO1001"]
        self.assertEqual(
            course_grades.set_index("letter_grade").loc["A+", "count"], 1
        )
        self.assertEqual(
            course_grades.set_index("letter_grade").loc["C+", "count"], 1
        )


if __name__ == "__main__":
    unittest.main()
