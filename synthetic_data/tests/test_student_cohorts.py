import sys
import unittest
from pathlib import Path

import pandas as pd

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from generate_student_cohorts import (
    allocate_cohort_counts,
    generate_student_ids,
    reassign_student_cohorts,
)


class StudentCohortGenerationTests(unittest.TestCase):
    def test_weighted_cohort_sizes_are_increasing_and_preserve_total(self):
        counts = allocate_cohort_counts(9890)

        self.assertEqual(sum(counts.values()), 9890)
        self.assertEqual(list(counts), list(range(2013, 2027)))
        self.assertTrue(all(
            left < right
            for left, right in zip(counts.values(), list(counts.values())[1:])
        ))
        self.assertEqual(counts[2013], 502)
        self.assertEqual(counts[2026], 910)

    def test_modulo_ids_are_unique_in_a_cohort_without_collision_scans(self):
        ids = generate_student_ids(2026, 1200)

        self.assertEqual(len(ids), 1200)
        self.assertEqual(len(set(ids)), 1200)
        self.assertTrue(all(
            len(student_id) == 7
            and student_id.startswith("26")
            and student_id[2:].isdigit()
            for student_id in ids
        ))
        self.assertEqual(ids, generate_student_ids(2026, 1200))

    def test_reassignment_changes_only_id_email_and_cohort(self):
        students = pd.DataFrame({
            "student_id": ["2310001", "2410001", "2510001", "2610001"],
            "name": ["A", "B", "C", "D"],
            "email": [
                "a.2310001@hcmut.edu.vn",
                "b.2410001@hcmut.edu.vn",
                "c.2510001@hcmut.edu.vn",
                "d.2610001@hcmut.edu.vn",
            ],
            "role": ["student"] * 4,
            "title": ["undergraduate"] * 4,
            "cohort": ["K23", "K24", "K25", "K26"],
            "major": ["computer science"] * 4,
        })

        result, counts = reassign_student_cohorts(students, seed=42)

        self.assertEqual(len(result), len(students))
        for column in ("name", "role", "title", "major"):
            self.assertEqual(result[column].tolist(), students[column].tolist())
        self.assertEqual(result["student_id"].str[:2].tolist(), [
            cohort[1:] for cohort in result["cohort"]
        ])
        self.assertTrue(all(
            email.endswith(f".{student_id}@hcmut.edu.vn")
            for email, student_id in zip(result["email"], result["student_id"])
        ))
        self.assertEqual(sum(counts.values()), len(students))


if __name__ == "__main__":
    unittest.main()
