import json
import os
from pathlib import Path
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT_DIR / "data" / "catalog"
PEOPLE_DIR = ROOT_DIR / "data" / "people"
CLASSES_DIR = ROOT_DIR / "generated" / "classes"
ENROLLMENTS_DIR = ROOT_DIR / "generated" / "enrollments"

PROFILE_FILE = ROOT_DIR / "generated" / "student_profile" / "student_profiles.csv"
STUDENT_FILE = PEOPLE_DIR / "student.csv"
INPUT_FILE = (
    PROFILE_FILE if PROFILE_FILE.exists() else PEOPLE_DIR / "student_base_score.csv"
)
LECTURE_FILE = PEOPLE_DIR / "lecturer_for_class.csv"


def get_available_semesters():
    """Return list of sorted uppercase semester codes available in generated enrollments."""
    semesters = []
    for file in sorted(ENROLLMENTS_DIR.glob("enrollment_hk*.csv")):
        code = file.stem.removeprefix("enrollment_").upper()
        semesters.append(code)
    return semesters


def get_sample_student_id():
    """Find a representative active student ID who completed all semesters."""
    semesters = get_available_semesters()
    if semesters:
        latest_file = ENROLLMENTS_DIR / f"enrollment_{semesters[-1].lower()}.csv"
        first_file = ENROLLMENTS_DIR / f"enrollment_{semesters[0].lower()}.csv"
        if latest_file.exists() and first_file.exists():
            df_latest = pd.read_csv(latest_file, dtype={"student_id": str})
            df_first = pd.read_csv(first_file, dtype={"student_id": str})
            common = set(df_latest["student_id"].str.strip()).intersection(
                set(df_first["student_id"].str.strip())
            )
            if common:
                return sorted(common)[0]
    return "1300511"


def summarize_required_courses(student_id, print_report=True):
    """Summarize curriculum courses a student has not passed yet.

    Returns a dictionary with ``courses`` (DataFrame of required/retake
    courses) and ``electives`` (credit progress for curriculum elective
    groups).
    """
    student_id = str(student_id).strip()
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy file hồ sơ sinh viên: {INPUT_FILE}")

    students = pd.read_csv(INPUT_FILE, dtype={"student_id": str})
    student_ids = set(students["student_id"].astype(str).str.strip().values)
    if student_id not in student_ids:
        raise ValueError(f"Không tìm thấy sinh viên: {student_id}")

    passed = set()
    failed = set()
    for enrollment_file in sorted(ENROLLMENTS_DIR.glob("enrollment_hk*.csv")):
        semester = enrollment_file.stem.removeprefix("enrollment_")
        class_file = CLASSES_DIR / f"class_{semester}.csv"
        if not class_file.exists():
            continue
        enrollment = pd.read_csv(enrollment_file, dtype={"student_id": str, "class_id": str})
        classes = pd.read_csv(class_file, dtype={"class_id": str})
        if not {"student_id", "class_id", "status"}.issubset(enrollment.columns):
            continue

        enrollment["student_id"] = enrollment["student_id"].astype(str).str.strip()
        enrollment["class_id"] = enrollment["class_id"].astype(str).str.strip()
        classes["class_id"] = classes["class_id"].astype(str).str.strip()

        rows = enrollment[enrollment["student_id"] == student_id].merge(
            classes[["class_id", "course_code", "course_name"]].drop_duplicates("class_id"),
            on="class_id",
            how="left",
        )
        for row in rows.itertuples(index=False):
            code = str(row.course_code).strip()
            status = str(row.status).strip().casefold()
            if status == "pass":
                passed.add(code)
                failed.discard(code)
            elif status == "fail" and code not in passed:
                failed.add(code)

    curriculum_file = CATALOG_DIR / "curriculum_computer_science.csv"
    curriculum = pd.read_csv(curriculum_file, dtype={"course_code": "string"})
    catalog = pd.read_csv(CATALOG_DIR / "course.csv", dtype={"course_code": str})
    catalog_map = catalog.drop_duplicates("course_code").set_index("course_code")

    rows = []
    for item in curriculum.itertuples(index=False):
        code = str(item.course_code).strip() if pd.notna(item.course_code) else ""
        if not code or code in passed:
            continue
        credits_val = (
            catalog_map.loc[code, "credits"]
            if code in catalog_map.index
            else getattr(item, "credits", 0)
        )
        rows.append({
            "semester": item.semester,
            "course_code": code,
            "course_name": getattr(item, "course_name", ""),
            "credit": credits_val,
            "status": "Retake" if code in failed else "Not passed",
        })
    courses = pd.DataFrame(rows, columns=[
        "semester", "course_code", "course_name", "credit", "status"
    ])

    elective_files = {
        "FREE": CATALOG_DIR / "elective_courses.csv",
        "GROUP_C": CATALOG_DIR / "group_c_electives.csv",
        "GROUP_B": CATALOG_DIR / "management_electives.csv",
    }
    elective_rows = []
    for group, file_path in elective_files.items():
        if not file_path.exists():
            continue
        options = pd.read_csv(file_path, dtype={"course_code": str})
        codes = set(options["course_code"].astype(str).str.strip())
        completed_total = sum(
            int(catalog_map.loc[code, "credits"])
            for code in passed & codes
            if code in catalog_map.index
        )
        completed_courses = len(passed & codes)
        curriculum_requirement = (
            curriculum.loc[curriculum["elective_group"] == group, "credits"]
            .dropna()
            .astype(int)
            .sum()
        )
        option_credits = options["course_code"].map(catalog_map["credits"]).dropna()
        typical_credits = (
            int(option_credits.mode().iloc[0])
            if not option_credits.empty
            else 0
        )
        is_course_count = group == "GROUP_B"
        required_courses = curriculum_requirement if is_course_count else pd.NA
        required = (
            required_courses * typical_credits
            if is_course_count
            else curriculum_requirement
        )
        completed = min(completed_total, required)
        elective_rows.append({
            "elective_group": group,
            "required_credits": required,
            "completed_credits": completed,
            "remaining_credits": max(required - completed, 0),
            "required_courses": required_courses,
            "completed_courses": completed_courses,
            "extra_credits": max(completed_total - required, 0),
        })
    electives = pd.DataFrame(elective_rows)

    result = {"courses": courses, "electives": electives}
    if print_report:
        print(f"\n{'='*75}")
        print(f" CÁC MÔN CẦN HỌC / HỌC LẠI - SINH VIÊN: {student_id} ".center(75, "="))
        print(f"{'='*75}")
        if courses.empty:
            print("Không còn môn bắt buộc nào chưa đậu.")
        else:
            print(courses.to_string(index=False))
        if not electives.empty:
            print(f"\n{'-'*75}")
            print(" TIẾN ĐỘ TÍN CHỈ CÁC NHÓM TỰ CHỌN ".center(75, "-"))
            print(f"{'-'*75}")
            print(electives.to_string(index=False))
        print(f"\nTổng số môn cần học/học lại: {len(courses)}")
        remaining_elective_credits = (
            electives["remaining_credits"].sum() if not electives.empty else 0
        )
        print(f"Tổng tín chỉ tự chọn còn thiếu: {remaining_elective_credits:g}\n")

    return result


def view_student_results(student_id, print_report=True):
    """View detailed transcript report for a student across all simulated semesters."""
    student_id_str = str(student_id).strip()
    semester_frames = []
    course_file = CATALOG_DIR / "course.csv"
    try:
        courses = pd.read_csv(course_file, dtype={"course_code": str})
    except FileNotFoundError:
        courses = pd.DataFrame(columns=["course_code", "credits"])

    for enrollment_file in sorted(ENROLLMENTS_DIR.glob("enrollment_hk*.csv")):
        semester = enrollment_file.stem.removeprefix("enrollment_").upper()
        class_file = CLASSES_DIR / f"class_{semester.lower()}.csv"
        if not class_file.exists():
            continue

        enrollment = pd.read_csv(enrollment_file, dtype={"student_id": str, "class_id": str})
        classes = pd.read_csv(class_file, dtype={"class_id": str})
        if "student_id" not in enrollment.columns or "class_id" not in enrollment.columns:
            continue

        enrollment["student_id"] = enrollment["student_id"].astype(str).str.strip()
        enrollment["class_id"] = enrollment["class_id"].astype(str).str.strip()
        classes["class_id"] = classes["class_id"].astype(str).str.strip()

        student_result = enrollment[enrollment["student_id"] == student_id_str].copy()
        if student_result.empty:
            continue

        class_columns = [
            col for col in ("class_id", "course_code", "course_name")
            if col in classes.columns
        ]
        student_result = student_result.merge(
            classes[class_columns].drop_duplicates("class_id"),
            on="class_id",
            how="left",
        )
        if set(("course_code", "credits")).issubset(courses.columns):
            student_result = student_result.merge(
                courses[["course_code", "credits"]].rename(
                    columns={"credits": "credit"}
                ).drop_duplicates("course_code"),
                on="course_code",
                how="left",
            )
        else:
            student_result["credit"] = "-"
        student_result["Học kỳ"] = semester
        semester_frames.append(student_result)

    if not semester_frames:
        if print_report:
            print(f"\n[!] Không tìm thấy dữ liệu đăng ký nào cho sinh viên: {student_id_str}\n")
        return pd.DataFrame()

    df_all = pd.concat(semester_frames, ignore_index=True)

    base_cols = ["Học kỳ", "course_code", "credit", "course_name"]
    end_cols = ["final_score", "letter_grade", "gpa_4", "status"]
    ignore_cols = base_cols + end_cols + ["class_id", "student_id", "enrollment_id", "semester", "retaken", "course_id", "passed", "semester_gpa_4", "final_gpa_4"]
    comp_cols = [c for c in df_all.columns if c not in ignore_cols]

    available_base_cols = [c for c in base_cols if c in df_all.columns]
    available_end_cols = [c for c in end_cols if c in df_all.columns]
    final_cols = available_base_cols + comp_cols + available_end_cols
    df_display = df_all[[c for c in final_cols if c in df_all.columns]].fillna("-")

    if print_report:
        print(f"\n{'='*95}")
        print(f" BẢNG ĐIỂM CHI TIẾT - SINH VIÊN: {student_id_str} ".center(95, "="))
        print(f"{'='*95}")

        for hk in sorted(df_display["Học kỳ"].unique()):
            df_hk = df_display[df_display["Học kỳ"] == hk]
            if not df_hk.empty:
                print(f"\n>>> THỐNG KÊ {hk} <<<")
                print(df_hk.drop(columns=["Học kỳ"]).to_string(index=False))
                tong_mon = len(df_hk)
                tong_tin_chi = pd.to_numeric(df_hk["credit"], errors="coerce").sum()
                if "status" in df_hk.columns:
                    mon_dau = (df_hk["status"].astype(str).str.casefold() == "pass").sum()
                    print(f"Tổng kết {hk}: Đậu {mon_dau}/{tong_mon} môn | Tổng tín chỉ: {tong_tin_chi:g}")
                else:
                    print(f"Tổng số tín chỉ {hk}: {tong_tin_chi:g}")
        print(f"\n{'='*95}\n")

    return df_all


def view_fail_result(semester=None, print_report=True):
    """View distribution of failed courses in a given semester."""
    if semester is None:
        semesters = get_available_semesters()
        semester = semesters[-1] if semesters else "HK162"

    semester = str(semester).strip().upper()
    file_path = ENROLLMENTS_DIR / f"enrollment_{semester.lower()}.csv"
    if not file_path.exists():
        if print_report:
            print(f"[!] Không tìm thấy file {file_path.name}")
        return None

    df_enr = pd.read_csv(file_path, dtype={"student_id": str})
    if "status" not in df_enr.columns:
        if print_report:
            print(f"[!] File {file_path.name} không có cột 'status'")
        return None

    df_fail = df_enr[df_enr["status"].astype(str).str.casefold() == "fail"]
    fail_counts = df_fail.groupby("student_id").size()
    distribution = fail_counts.value_counts().sort_index()

    total_students = df_enr["student_id"].nunique()
    students_with_failures = len(fail_counts)
    students_passed_all = total_students - students_with_failures

    result = {
        "semester": semester,
        "total_students": total_students,
        "passed_all": students_passed_all,
        "failed_students": students_with_failures,
        "distribution": distribution,
    }

    if print_report:
        print(f"\n{'='*65}")
        print(f" PHÂN PHỐI SỐ LƯỢNG MÔN RỚT - {semester} ".center(65, "="))
        print(f"{'='*65}")
        print(f"Tổng số sinh viên có đăng ký: {total_students}")
        pass_all_rate = (students_passed_all / total_students) * 100 if total_students else 0
        print(f"Số SV qua tất cả các môn:    {students_passed_all} ({pass_all_rate:.1f}%)")
        print(f"Số SV rớt ít nhất 1 môn:     {students_with_failures} ({100 - pass_all_rate:.1f}%)")
        print("-" * 65)
        print(f"{'Số môn rớt':<15} | {'Số lượng sinh viên':<20} | {'Tỷ lệ (%)'}")
        print("-" * 65)
        print(f"{'0 môn':<15} | {students_passed_all:<20} | {pass_all_rate:.1f}%")

        for num_fails, count in distribution.items():
            pct = (count / total_students) * 100 if total_students else 0
            print(f"{str(num_fails) + ' môn':<15} | {count:<20} | {pct:.1f}%")

        overload_fails = distribution[distribution.index >= 3].sum()
        print("-" * 65)
        print(f">>> CẢNH BÁO NGUY CƠ (Rớt >= 3 môn): {overload_fails} sinh viên\n")

    return result


def get_class_roster(semester, class_id, print_report=True):
    """Retrieve instructor info and enrolled students for a specific class section."""
    semester = str(semester).strip().upper()
    class_id_str = str(class_id).strip()

    class_file = CLASSES_DIR / f"class_{semester.lower()}.csv"
    enrollment_file = ENROLLMENTS_DIR / f"enrollment_{semester.lower()}.csv"
    student_file = INPUT_FILE

    for f in [class_file, enrollment_file, student_file]:
        if not f.exists():
            if print_report:
                print(f"[!] Lỗi: Không tìm thấy file '{f.name}'.")
            return None

    df_class = pd.read_csv(class_file, dtype={"class_id": str})
    df_enr = pd.read_csv(enrollment_file, dtype={"class_id": str, "student_id": str})
    df_student = pd.read_csv(student_file, dtype={"student_id": str})

    df_class["class_id"] = df_class["class_id"].astype(str).str.strip()
    df_enr["class_id"] = df_enr["class_id"].astype(str).str.strip()

    class_info = df_class[df_class["class_id"] == class_id_str]
    if class_info.empty:
        if print_report:
            print(f"[!] Không tìm thấy lớp '{class_id_str}' trong học kỳ {semester}.")
        return None

    course_code = class_info["course_code"].values[0]
    course_name = class_info["course_name"].values[0] if "course_name" in class_info.columns else "N/A"
    lecturer_id = class_info["lecturer_id"].values[0] if "lecturer_id" in class_info.columns else "N/A"
    lecturer_name = class_info["lecturer_name"].values[0] if "lecturer_name" in class_info.columns else "N/A"

    enrolled = df_enr[df_enr["class_id"] == class_id_str].copy()
    if enrolled.empty:
        if print_report:
            print(f"[!] Lớp {class_id_str} ({course_code} - {course_name}) chưa có sinh viên nào đăng ký.")
        return {
            "semester": semester,
            "class_id": class_id_str,
            "course": {"code": course_code, "name": course_name},
            "lecturer": {"id": lecturer_id, "name": lecturer_name},
            "total_students": 0,
            "students": pd.DataFrame(),
        }

    enrolled["student_id"] = enrolled["student_id"].astype(str).str.strip()
    df_student["student_id"] = df_student["student_id"].astype(str).str.strip()

    student_details = pd.merge(enrolled, df_student, on="student_id", how="left")

    result = {
        "semester": semester,
        "class_id": class_id_str,
        "course": {"code": course_code, "name": course_name},
        "lecturer": {"id": lecturer_id, "name": lecturer_name},
        "total_students": len(student_details),
        "students": student_details,
    }

    if print_report:
        print(f"\n{'='*85}")
        print(f" DANH SÁCH LỚP {class_id_str} - HỌC KỲ {semester} ".center(85, "="))
        print(f"{'='*85}")
        print(f"Môn học:    {course_code} - {course_name}")
        print(f"Giảng viên: {lecturer_name} (Mã: {lecturer_id})")
        print(f"Sĩ số lớp:  {len(student_details)} sinh viên")
        print("-" * 85)
        display_cols = ["student_id", "name"]
        if "final_score" in student_details.columns:
            display_cols.append("final_score")
        if "letter_grade" in student_details.columns:
            display_cols.append("letter_grade")
        if "status" in student_details.columns:
            display_cols.append("status")
        available_cols = [c for c in display_cols if c in student_details.columns]
        print(student_details[available_cols].to_string(index=False))
        print(f"{'='*85}\n")

    return result


def view_ctxh_distribution(cohort, print_report=True):
    """Phân tích phân phối số ngày Công tác Xã hội (CTXH) của một khóa sinh viên (K13, K14,...).

    Parameters
    ----------
    cohort : str
        Mã khóa cần phân tích (VD: 'K13', 'K14', '13', 'k13',...).
    print_report : bool
        Có in báo cáo trực quan ra màn hình hay không (mặc định: True).

    Returns
    -------
    dict or None
        Từ điển chứa dữ liệu phân tích thống kê, các mốc chuẩn học vụ, phân phối khoảng ngày
        và tiến độ theo từng học kỳ; hoặc None nếu không tìm thấy khóa hợp lệ.
    """
    cohort_str = str(cohort).strip().upper()
    if not cohort_str.startswith("K") and cohort_str.isdigit():
        cohort_str = f"K{cohort_str}"

    if not PROFILE_FILE.exists():
        if print_report:
            print(f"[!] Lỗi: Không tìm thấy file hồ sơ sinh viên: {PROFILE_FILE}")
        return None

    df_prof = pd.read_csv(PROFILE_FILE, dtype={"student_id": str})
    df_prof["student_id"] = df_prof["student_id"].astype(str).str.strip()

    if STUDENT_FILE.exists():
        df_stu = pd.read_csv(STUDENT_FILE, dtype={"student_id": str, "cohort": str})
        df_stu["student_id"] = df_stu["student_id"].astype(str).str.strip()
        df_stu["cohort"] = df_stu["cohort"].astype(str).str.strip().str.upper()
        merged = df_prof.merge(df_stu[["student_id", "cohort"]], on="student_id", how="left")
    else:
        merged = df_prof.copy()
        merged["cohort"] = merged["student_id"].apply(
            lambda sid: f"K{sid[:2]}" if len(sid) >= 2 else "UNKNOWN"
        )

    k_df = merged[merged["cohort"] == cohort_str].copy()
    if k_df.empty:
        prefix = cohort_str.removeprefix("K")
        if prefix.isdigit() and len(prefix) == 2:
            k_df = merged[merged["student_id"].str.startswith(prefix)].copy()

    if k_df.empty:
        if print_report:
            known_cohorts = sorted([c for c in merged["cohort"].dropna().unique() if str(c).startswith("K")])
            print(f"[!] Không tìm thấy sinh viên nào thuộc khóa {cohort_str}.")
            if known_cohorts:
                print(f"    Các khóa có trong hệ thống: {', '.join(known_cohorts)}")
        return None

    student_records = []
    sem_records = []

    for _, row in k_df.iterrows():
        sid = row["student_id"]
        name = row.get("name", "")
        raw = row.get("ctxh_days_by_semester", "")
        items = []
        if pd.notna(raw) and str(raw).strip():
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    items = parsed
            except Exception:
                items = []

        if items:
            final_days = int(items[-1].get("cumulative_days", 0))
            prev_days = 0
            for item in items:
                sem = item.get("semester", "")
                cur_days = int(item.get("cumulative_days", 0))
                inc = max(cur_days - prev_days, 0)
                sem_records.append({
                    "student_id": sid,
                    "semester": sem,
                    "cumulative_days": cur_days,
                    "increment": inc,
                })
                prev_days = cur_days
        else:
            final_days = 0

        student_records.append({
            "student_id": sid,
            "name": name,
            "final_days": final_days,
            "has_records": bool(items),
        })

    df_students = pd.DataFrame(student_records)
    total_students = len(df_students)
    active_students = df_students[df_students["has_records"]]

    if active_students.empty:
        if print_report:
            print(f"\n{'='*75}")
            print(f" PHÂN PHỐI NGÀY CÔNG TÁC XÃ HỘI (CTXH) - KHÓA {cohort_str} ".center(75, "="))
            print(f"{'='*75}")
            print(f"Tổng số sinh viên khóa {cohort_str}: {total_students}")
            print(f"[i] Khóa này chưa có dữ liệu học kỳ mô phỏng hoặc chưa tích lũy ngày CTXH.\n")
        return {
            "cohort": cohort_str,
            "total_students": total_students,
            "has_data": False,
        }

    s_days = active_students["final_days"]
    mean_val = float(s_days.mean())
    median_val = float(s_days.median())
    std_val = float(s_days.std()) if len(s_days) > 1 else 0.0
    min_val = int(s_days.min())
    max_val = int(s_days.max())
    q25 = float(s_days.quantile(0.25))
    q75 = float(s_days.quantile(0.75))

    thesis_count = int((s_days >= 12).sum())
    thesis_pct = (thesis_count / total_students) * 100
    grad_count = int((s_days >= 15).sum())
    grad_pct = (grad_count / total_students) * 100
    below_thesis_count = total_students - thesis_count
    below_thesis_pct = (below_thesis_count / total_students) * 100

    bins = [-1, 4, 8, 11, 14, 19, 999]
    labels = [
        "0 - 4 ngày (Bắt đầu / Ít)",
        "5 - 8 ngày (Đang tích lũy)",
        "9 - 11 ngày (Cận chuẩn KLTN)",
        "12 - 14 ngày (Đạt chuẩn KLTN)",
        "15 - 19 ngày (Đạt chuẩn Tốt nghiệp)",
        ">= 20 ngày (Vượt chuẩn)",
    ]
    df_students["bin"] = pd.cut(df_students["final_days"], bins=bins, labels=labels)
    bin_counts = df_students["bin"].value_counts(sort=False)

    df_sem = pd.DataFrame(sem_records)
    sem_summary = None
    if not df_sem.empty:
        sem_summary = df_sem.groupby("semester", sort=False).agg(
            mean_cum=("cumulative_days", "mean"),
            median_cum=("cumulative_days", "median"),
            min_cum=("cumulative_days", "min"),
            max_cum=("cumulative_days", "max"),
            mean_inc=("increment", "mean"),
            thesis_count=("cumulative_days", lambda s: int((s >= 12).sum())),
            grad_count=("cumulative_days", lambda s: int((s >= 15).sum())),
            student_count=("student_id", "nunique"),
        ).reset_index()

    result = {
        "cohort": cohort_str,
        "total_students": total_students,
        "active_students": len(active_students),
        "has_data": True,
        "stats": {
            "mean": mean_val,
            "median": median_val,
            "std": std_val,
            "min": min_val,
            "max": max_val,
            "q25": q25,
            "q75": q75,
        },
        "benchmarks": {
            "thesis_eligible_count": thesis_count,
            "thesis_eligible_pct": thesis_pct,
            "graduation_eligible_count": grad_count,
            "graduation_eligible_pct": grad_pct,
            "below_thesis_count": below_thesis_count,
            "below_thesis_pct": below_thesis_pct,
        },
        "distribution_bins": bin_counts,
        "semester_progression": sem_summary,
        "student_records": df_students,
    }

    if print_report:
        print(f"\n{'='*82}")
        print(f" PHÂN PHỐI NGÀY CÔNG TÁC XÃ HỘI (CTXH) - KHÓA {cohort_str} ".center(82, "="))
        print(f"{'='*82}")
        print(f"Tổng số sinh viên trong khóa:    {total_students} sinh viên")
        print(f"Sinh viên có dữ liệu CTXH:       {len(active_students)} sinh viên ({(len(active_students)/total_students)*100:.1f}%)")

        print(f"\n>>> THỐNG KÊ TỔNG QUÁT (TÍCH LŨY HIỆN TẠI) <<<")
        print(f"  Trung bình (Mean):     {mean_val:.2f} ngày     | Trung vị (Median):  {median_val:.1f} ngày")
        print(f"  Độ lệch chuẩn (Std):   {std_val:.2f}          | Tứ phân vị (Q1-Q3): {q25:.1f} - {q75:.1f} ngày")
        print(f"  Thấp nhất (Min):       {min_val} ngày           | Cao nhất (Max):     {max_val} ngày")

        print(f"\n>>> MỨC ĐỘ ĐẠT CHUẨN QUY ĐỊNH HỌC VỤ <<<")
        print(f"  - Đủ chuẩn làm KLTN   (>= 12 ngày): {thesis_count:>4} sinh viên ({thesis_pct:5.1f}%)")
        print(f"  - Đủ chuẩn Tốt nghiệp (>= 15 ngày): {grad_count:>4} sinh viên ({grad_pct:5.1f}%)")
        print(f"  - Chưa đạt chuẩn KLTN  (< 12 ngày): {below_thesis_count:>4} sinh viên ({below_thesis_pct:5.1f}%)")

        print(f"\n{'-'*82}")
        print(" PHÂN BỐ THEO KHOẢNG NGÀY CTXH TÍCH LŨY ".center(82, "-"))
        print(f"{'-'*82}")
        print(f"{'Khoảng ngày':<35} | {'Số lượng':<8} | {'Tỷ lệ (%)':<10} | Biểu đồ")
        print(f"{'-'*82}")
        for label, count in bin_counts.items():
            pct = (count / total_students) * 100
            bar = "█" * int(round(pct / 3))
            print(f"{str(label):<35} | {count:<8} | {pct:>7.1f}%   | {bar}")

        if sem_summary is not None and not sem_summary.empty:
            print(f"\n{'-'*82}")
            print(" TIẾN ĐỘ TÍCH LŨY CTXH THEO TỪNG HỌC KỲ ".center(82, "-"))
            print(f"{'-'*82}")
            print(f"{'Học kỳ':<7} | {'TB tích lũy':<11} | {'Trung vị':<8} | {'Min-Max':<7} | {'TB tăng':<7} | {'>=12 ngày (KLTN)':<16} | {'>=15 ngày (TN)':<14}")
            print(f"{'-'*82}")
            for _, r in sem_summary.iterrows():
                hk = str(r["semester"])
                t_count = int(r["thesis_count"])
                t_pct = (t_count / total_students) * 100
                g_count = int(r["grad_count"])
                g_pct = (g_count / total_students) * 100
                print(
                    f"{hk:<7} | {r['mean_cum']:>9.2f}   | {r['median_cum']:>6.1f}   | "
                    f"{int(r['min_cum']):>2}-{int(r['max_cum']):<2}   | +{r['mean_inc']:>5.2f} | "
                    f"{t_count:>4} ({t_pct:4.1f}%)    | {g_count:>4} ({g_pct:4.1f}%)"
                )
        print(f"{'='*82}\n")

    return result


analyze_ctxh_distribution = view_ctxh_distribution

