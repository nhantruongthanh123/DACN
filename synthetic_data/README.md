# Synthetic Course and Semester Data

This folder contains synthetic data used for analyzing study plans, prerequisite relationships between courses, and academic semester information.

## 1. course.csv

File: `course.csv`

Description: A table listing all courses in the curriculum.

Columns:
- `course_id`: internal unique identifier for the course.
- `course_code`: course code, for example `CO1005`, `MT1003`, `SP1031`.
- `course_name`: course name in Vietnamese.
- `credits`: number of credits for the course.

Example:
```csv
1,CO1005,Nhập môn Điện toán,3
```

Purpose:
- Used to look up general information about each course.
- Supports curriculum analysis, credit mapping, and course grouping.

---

## 2. course_prerequisite.csv

File: `course_prerequisite.csv`

Description: A table showing prerequisite relationships between courses.

Columns:
- `course_prerequisite_id`: unique identifier for the prerequisite relationship.
- `course_code`: the course being evaluated, which has prerequisite conditions.
- `related_course_code`: the related course, typically the course that must be completed first.
- `relation_type`: the type of relationship between the two courses.

Common values in `relation_type`:
- `KN`: knowledge block / required prerequisite.
- `TQ`: equivalent prerequisite or a course that must be completed before another.
- `HT`: prerequisite / required sequence condition.
- `SHT`: a specific prerequisite relationship, often representing a stronger or additional condition.

Example:
```csv
1,MT1005,MT1003,KN
```

Explanation:
- `MT1005` (Calculus 2) has a `KN` relationship with `MT1003` (Calculus 1), meaning this course requires `MT1003` to be completed first.

Purpose:
- Used to build a course dependency graph, check prerequisite rules, and support academic roadmap recommendations.

---

## 3. semester.csv

File: `semester.csv`

Description: A table containing academic semester information.

Columns:
- `semester_id`: unique identifier for the semester.
- `semester_code`: semester code, for example `HK231`, `HK242`, `HK251`.
- `academic_year`: corresponding academic year.
- `term`: semester in the academic year, values 1, 2, or 3.

Example:
```csv
1,HK231,2023-2024,1
```

Explanation:
- `HK231` represents semester 1 of the 2023-2024 academic year.

Purpose:
- Used to categorize data by study period.
- Supports tracking student progression, scheduling, and analysis by academic year and semester.

---

## 4. student.csv

File: `student.csv`

Description: A list of synthetic student accounts. The file contains 9,890 student records and does not include administrator accounts or password fields.

Columns:
- `user_id`: unique identifier for the student.
- `name`: student's full name.
- `email`: student's synthetic university email address.
- `role`: account role; this file contains `student`.
- `title`: academic level; student records use `undergraduate`.

Purpose:
- Provides student information for enrollment, progression, and risk analysis.
- Can be joined to other student-related datasets through `user_id`.

---

## 5. lecture.csv

File: `lecture.csv`

Description: A list of synthetic lecturer accounts. The file contains 100 lecturer records and does not include administrator accounts or password fields.

Columns:
- `user_id`: unique identifier for the lecturer.
- `name`: lecturer's full name.
- `email`: lecturer's synthetic university email address.
- `role`: account role; this file contains `lecturer`.
- `title`: academic qualification or position, such as `bachelor`, `master`, `doctor`, `associate_professor`, or `professor`.

Purpose:
- Provides lecturer information for teaching assignments.
- The lecturer's `name` is referenced by `class.csv` in the `lecturer_name` column.

---

## 6. class.csv

File: `class.csv`

Description: A list of synthetic course classes, mapping specific course offerings to semesters, class groups, and lecturers. 

Columns:
- `class_id`: auto-incrementing integer acting as the unique surrogate key for the class (e.g., `1`, `2`, `3`).
- `course_code`: the official course code, linking the class to its academic metadata (e.g., `CH1003`, `CO1005`).
- `semester`: the academic semester code in which the class is offered (e.g., `HK231`, `HK243`).
- `class_group`: the specific section or group identifier for the class (e.g., `L01`, `L02`).
- `lecturer_name`: name of the lecturer assigned to teach this specific class.

Example:
```csv
1,CH1003,HK231,L01,Đặng Gia Hiếu
```

---

## Dataset overview

This dataset simulates a training management system with six main components:
1. Course list.
2. Prerequisite relationships between courses.
3. Semester information.
4. Student accounts.
5. Lecturer accounts.
6. Course classes and lecturer assignments.

The data can be used for:
- Building study roadmaps.
- Analyzing prerequisite courses.
- Evaluating student progress by semester.
- Analyzing course offerings and lecturer assignments.
- Generating data for machine learning models, course recommendation systems, or risk assessments for delayed progression.

## Notes

- This is synthetic data and not real academic data from a management system.
- Course codes and semester codes are designed with a consistent format to simplify data processing.
