import csv
from contextlib import ExitStack
import re
import secrets
import string
import unicodedata
from pathlib import Path

from faker import Faker


STUDENTS_PER_COHORT = 1_000
COHORTS = tuple(range(13, 23))
OUTPUT_FILE = Path(__file__).with_name("user.csv")
ROLE_OUTPUT_FILES = {
    "student": Path(__file__).with_name("student.csv"),
    "lecturer": Path(__file__).with_name("lecturer.csv"),
    "admin": Path(__file__).with_name("admin.csv"),
}
MSSV_STEP = 7919
MSSV_MODULUS = 100_000
ADMIN_COUNT = 10
LECTURER_COUNT = 100
LECTURER_TITLES = ("bachelor", "master", "doctor", "associate_professor", "professor")

SURNAMES = (
    "Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Võ", "Đặng",
    "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Huỳnh", "Phan",
)
MIDDLE_NAMES = (
    "Văn", "Thị", "Hữu", "Minh", "Ngọc", "Quốc", "Thanh", "Gia",
    "Đức", "Hoàng", "Anh", "Phương", "Khánh", "Tuấn", "Quang",
)
GIVEN_NAMES = (
    "An", "Anh", "Bảo", "Châu", "Duy", "Hà", "Hải", "Hiếu", "Hùng",
    "Khang", "Khôi", "Lam", "Linh", "Long", "Mai", "Minh", "Nam",
    "Nhi", "Phát", "Phúc", "Quân", "Quang", "Thảo", "Trang", "Trinh",
    "Tú", "Tuấn", "Uyên", "Việt", "Yến",
)


def normalize_name(name):
    name = name.replace("Đ", "D").replace("đ", "d")
    normalized = unicodedata.normalize("NFD", name)
    without_marks = "".join(
        character for character in normalized
        if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"[^a-z0-9]", "", without_marks.lower())


def generate_password():
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(12))


def generate_vietnamese_name(fake):
    surname = fake.random_element(elements=SURNAMES)
    middle_name = fake.random_element(elements=MIDDLE_NAMES)
    given_name = fake.random_element(elements=GIVEN_NAMES)
    return f"{surname} {middle_name} {given_name}"


def generate_students():
    fake = Faker("vi_VN")
    Faker.seed(20260923)

    header = [
        "user_id", "name", "email", "password", "password_hash", "role", "title",
    ]
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8-sig") as output, ExitStack() as role_outputs:
        writer = csv.writer(output)
        role_writers = {}
        for role, role_output_file in ROLE_OUTPUT_FILES.items():
            role_output = role_outputs.enter_context(
                role_output_file.open("w", newline="", encoding="utf-8-sig")
            )
            role_writer = csv.writer(role_output)
            role_writer.writerow(header)
            role_writers[role] = role_writer
        writer.writerow(header)

        record_number = 0
        for cohort in COHORTS:
            for sequence in range(1, STUDENTS_PER_COHORT + 1):
                suffix = (sequence * MSSV_STEP + cohort * 1049) % MSSV_MODULUS
                user_id = f"{cohort}{suffix:05d}"
                name = generate_vietnamese_name(fake)
                email_name = normalize_name(name)
                email = f"{email_name}.{user_id}@hcmut.edu.vn"
                password = generate_password()
                if record_number < ADMIN_COUNT:
                    role, title = "admin", "none"
                elif record_number < ADMIN_COUNT + LECTURER_COUNT:
                    role = "lecturer"
                    title = fake.random_element(elements=LECTURER_TITLES)
                else:
                    role, title = "student", "undergraduate"
                writer.writerow([
                    user_id, name, email, password, password, role, title,
                ])
                role_writers[role].writerow([
                    user_id, name, email, password, password, role, title,
                ])
                record_number += 1


if __name__ == "__main__":
    generate_students()
    print(f"Generated {len(COHORTS) * STUDENTS_PER_COHORT} students: {OUTPUT_FILE}")