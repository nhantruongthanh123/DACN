from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
COURSE_FILE = ROOT_DIR / "data" / "catalog" / "course.csv"
OUTPUT_FILE = ROOT_DIR / "student_curriculum_plan.csv"

# Kế hoạch chuẩn theo chương trình đào tạo.
# Đây là môn nhà trường đề xuất theo tiến độ, không phải lịch sử điểm
# và không loại các môn mà sinh viên được miễn/học lại.
CURRICULUM_PLAN = {
    "K23": {
        "HK231": (
            "MI1003", "MT1003", "PH1003", "CO1005", "LA1003",
        ),
        "HK232": (
            "MT1005", "MT1007", "CO1007", "CO1027", "PH1007",
            "LA1005", "CH1003",
        ),
        "HK241": (
            "LA1007", "SP1031", "CO2007", "CO2011", "CO2003", "CO2001",
        ),
        "HK242": (
            "CO2013", "CO2017", "CO2039", "MT2013", "LA1007",
        ),
    },
    "K24": {
        "HK241": (
            "MI1003", "MT1003", "PH1003", "CO1005", "LA1003", "CO1023",
        ),
        "HK242": (
            "MT1005", "MT1007", "CO1007", "CO1027", "PH1007",
            "LA1005", "CH1003",
        ),
    },
}


def main():
    courses = pd.read_csv(COURSE_FILE)
    course_data = courses.set_index("course_code")[
        ["course_name", "credits"]
    ].to_dict("index")

    rows = []
    for cohort, semesters in CURRICULUM_PLAN.items():
        for semester, course_codes in semesters.items():
            for order, course_code in enumerate(course_codes, start=1):
                if course_code not in course_data:
                    raise ValueError(
                        f"{course_code} is missing from course.csv"
                    )
                course = course_data[course_code]
                rows.append(
                    {
                        "cohort": cohort,
                        "semester": semester,
                        "course_order": order,
                        "course_code": course_code,
                        "course_name": course["course_name"],
                        "credits": course["credits"],
                    }
                )

    plan = pd.DataFrame(rows)
    plan.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"Created {OUTPUT_FILE.name}: {len(plan)} course suggestions")

    for (cohort, semester), group in plan.groupby(
        ["cohort", "semester"], sort=False
    ):
        credits = group["credits"].sum()
        print(
            f"{cohort} - {semester}: {len(group)} courses, "
            f"{credits:g} credits"
        )


if __name__ == "__main__":
    main()
