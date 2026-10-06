"""Tra cứu hồ sơ và kết quả học tập của một sinh viên đã được sinh dữ liệu.

Ví dụ:
    python view_student.py 1392646
    python view_student.py 1392646 --data-dir generated_full --all-attempts
"""

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_DATA_DIR = Path(__file__).with_name("generated_full")


def get_student_info(user_id, data_dir=DEFAULT_DATA_DIR, all_attempts=False):
    """Trả về hồ sơ, thống kê môn học và điểm của một sinh viên.

    Mặc định mỗi môn chỉ trả về lần học gần nhất. Đặt ``all_attempts=True`` để
    xem cả các lần rớt/học lại.
    """
    data_dir = Path(data_dir)
    profile_path = data_dir / "student_profile.csv"
    attempts_path = data_dir / "student_course_attempts.csv"

    if not profile_path.is_file() or not attempts_path.is_file():
        raise FileNotFoundError(
            "Không tìm thấy student_profile.csv hoặc student_course_attempts.csv "
            f"trong: {data_dir}"
        )

    requested_id = str(user_id)
    profiles = pd.read_csv(profile_path, dtype={"user_id": str})
    attempts = pd.read_csv(attempts_path, dtype={"user_id": str, "course_code": str})

    profile = profiles.loc[profiles["user_id"] == requested_id]
    student_attempts = attempts.loc[attempts["user_id"] == requested_id].copy()
    if profile.empty and student_attempts.empty:
        raise LookupError(f"Không tìm thấy sinh viên có user_id = {requested_id}")

    student_attempts = student_attempts.sort_values(
        ["term_code", "course_code", "attempt_no"]
    )
    latest_by_course = student_attempts.drop_duplicates("course_code", keep="last")

    summary = {
        "courses_attempted": int(student_attempts["course_code"].nunique()),
        "courses_passed": int(
            student_attempts.loc[
                student_attempts["status"] == "PASS", "course_code"
            ].nunique()
        ),
        "courses_not_passed": int((latest_by_course["status"] == "FAIL").sum()),
        "total_attempts": int(len(student_attempts)),
    }

    columns = [
        "term_code", "course_code", "course_name", "credits", "class_id",
        "attempt_no", "status", "final_score", "letter_grade", "grade_4",
        "quiz", "lab", "btl", "giua_ky", "cuoi_ky",
    ]
    selected_attempts = student_attempts if all_attempts else latest_by_course
    return {
        "profile": profile.iloc[0].dropna().to_dict() if not profile.empty else {},
        "summary": summary,
        "courses": selected_attempts[columns].to_dict("records"),
    }


def print_student_info(info, all_attempts=False):
    """In kết quả tra cứu theo dạng dễ đọc trên terminal."""
    profile = info["profile"]
    print("THÔNG TIN SINH VIÊN")
    for key in (
        "user_id", "cohort", "ability_group", "personality", "ability",
        "gpa_4", "academic_classification",
    ):
        if key in profile:
            print(f"- {key}: {profile[key]}")

    summary = info["summary"]
    print("\nTỔNG KẾT")
    print(f"- Số môn đã học: {summary['courses_attempted']}")
    print(f"- Số môn đã đậu: {summary['courses_passed']}")
    print(f"- Số môn chưa đậu: {summary['courses_not_passed']}")
    print(f"- Tổng số lượt học (kể cả học lại): {summary['total_attempts']}")

    title = "TẤT CẢ LẦN HỌC" if all_attempts else "ĐIỂM LẦN HỌC GẦN NHẤT THEO MÔN"
    print(f"\n{title}")
    if not info["courses"]:
        print("Chưa có dữ liệu môn học.")
        return

    course_df = pd.DataFrame(info["courses"])
    print(course_df.to_string(index=False))


def main():
    parser = argparse.ArgumentParser(
        description="Xem hồ sơ, số môn đã học và điểm từng môn của một sinh viên."
    )
    parser.add_argument("user_id", help="Mã số sinh viên cần tra cứu")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Thư mục chứa student_profile.csv và student_course_attempts.csv",
    )
    parser.add_argument(
        "--all-attempts",
        action="store_true",
        help="Hiện cả các lần học lại thay vì chỉ lần học gần nhất của mỗi môn",
    )
    args = parser.parse_args()

    try:
        info = get_student_info(args.user_id, args.data_dir, args.all_attempts)
    except (FileNotFoundError, LookupError) as error:
        parser.error(str(error))

    print_student_info(info, args.all_attempts)


if __name__ == "__main__":
    main()
