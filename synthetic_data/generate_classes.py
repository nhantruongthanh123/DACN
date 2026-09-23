import csv
import random
from pathlib import Path


DATA_DIR = Path(__file__).parent
COURSE_FILE = DATA_DIR / "course.csv"
STUDENTS_FILE = DATA_DIR / "user.csv"
OUTPUT_FILE = DATA_DIR / "class.csv"
FIRST_SEMESTER = 131
LAST_SEMESTER = 242
MIN_CLASSES = 3
MAX_CLASSES = 10
RANDOM_SEED = 20260923


def semester_codes():
    codes = []
    for year in range(13, 25):
        first_term = 1
        last_term = 2 if year == 24 else 3
        for term in range(first_term, last_term + 1):
            codes.append(f"{year:02d}{term}")
    return codes


def read_courses():
    with COURSE_FILE.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def read_lecturers():
    with STUDENTS_FILE.open(encoding="utf-8-sig", newline="") as source:
        return [row["name"] for row in csv.DictReader(source) if row["role"] == "lecturer"]


def generate_classes():
    courses = read_courses()
    lecturers = read_lecturers()
    if not lecturers:
        raise ValueError("students.csv does not contain any lecturer")

    rng = random.Random(RANDOM_SEED)
    with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["id", "course_id", "lecturer_name"])

        for semester in semester_codes():
            for course in courses:
                class_count = rng.randint(MIN_CLASSES, MAX_CLASSES)
                for group_number in range(1, class_count + 1):
                    class_id = f"{semester}_L{group_number:02d}_{course['course_code']}"
                    lecturer_name = rng.choice(lecturers)
                    writer.writerow([class_id, course["course_code"], lecturer_name])


if __name__ == "__main__":
    generate_classes()
    print(f"Generated classes: {OUTPUT_FILE}")
