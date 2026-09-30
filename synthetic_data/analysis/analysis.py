import os
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT_DIR / "data" / "catalog"
PEOPLE_DIR = ROOT_DIR / "data" / "people"
CLASSES_DIR = ROOT_DIR / "generated" / "classes"
ENROLLMENTS_DIR = ROOT_DIR / "generated" / "enrollments"


INPUT_FILE = PEOPLE_DIR / "student_base_score.csv"
LECTURE_FILE = PEOPLE_DIR / "lecturer_for_class.csv"
ENROLLMENT_FILE_HK231 = ENROLLMENTS_DIR / "enrollment_hk231.csv"
ENROLLMENT_FILE_HK232 = ENROLLMENTS_DIR / "enrollment_hk232.csv"


def summarize_required_courses(student_id, print_report=True):
    """Summarize curriculum courses a student has not passed yet.

    Returns a dictionary with ``courses`` (a DataFrame of required/retake
    courses) and ``electives`` (credit progress for curriculum elective
    groups).  Results are based on all available enrollment history files.
    """
    data_dir = ROOT_DIR
    student_id = str(student_id).strip()
    students_file = PEOPLE_DIR / "student_base_score.csv"
    students = pd.read_csv(students_file, dtype={"student_id": str})
    if student_id not in students["student_id"].astype(str).str.strip().values:
        raise ValueError(f"Không tìm thấy sinh viên: {student_id}")

    passed = set()
    failed = set()
    for enrollment_file in sorted(ENROLLMENTS_DIR.glob("enrollment_hk*.csv")):
        semester = enrollment_file.stem.removeprefix("enrollment_")
        class_file = CLASSES_DIR / f"class_{semester}.csv"
        if not class_file.exists():
            continue
        enrollment = pd.read_csv(enrollment_file, dtype={"student_id": str})
        classes = pd.read_csv(class_file, dtype={"class_id": str})
        if not {"student_id", "class_id", "status"}.issubset(enrollment.columns):
            continue
        rows = enrollment[
            enrollment["student_id"].astype(str).str.strip() == student_id
        ].merge(
            classes[["class_id", "course_code", "course_name"]].drop_duplicates(
                "class_id"
            ),
            on="class_id",
            how="left",
        )
        for row in rows.itertuples(index=False):
            code = str(row.course_code)
            if str(row.status).strip().casefold() == "pass":
                passed.add(code)
            elif str(row.status).strip().casefold() == "fail":
                failed.add(code)

    curriculum_file = CATALOG_DIR / "curriculum_computer_science.csv"
    curriculum = pd.read_csv(curriculum_file, dtype={"course_code": "string"})
    catalog = pd.read_csv(CATALOG_DIR / "course.csv", dtype={"course_code": str})
    catalog_map = catalog.drop_duplicates("course_code").set_index("course_code")

    rows = []
    for item in curriculum.itertuples(index=False):
        code = str(item.course_code) if pd.notna(item.course_code) else ""
        if not code:
            continue
        if code in passed:
            continue
        rows.append({
            "semester": item.semester,
            "course_code": code,
            "course_name": getattr(item, "course_name", None),
            "credit": catalog_map.loc[code, "credits"] if code in catalog_map.index else item.credits,
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
        codes = set(options["course_code"].astype(str))
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
        option_credits = options["course_code"].map(
            catalog_map["credits"]
        ).dropna()
        typical_credits = (
            int(option_credits.mode().iloc[0])
            if not option_credits.empty
            else 0
        )
        is_course_count = group == "GROUP_B"
        required_courses = (
            curriculum_requirement if is_course_count else pd.NA
        )
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
        print(f"\n>>> CÁC MÔN CẦN HỌC - {student_id} <<<")
        if courses.empty:
            print("Không còn môn bắt buộc nào chưa đậu.")
        else:
            print(courses.to_string(index=False))
        if not electives.empty:
            print("\n>>> TIẾN ĐỘ MÔN TỰ CHỌN <<<")
            print(electives.to_string(index=False))
        print(f"\nTổng môn cần học/học lại: {len(courses)}")
        print(f"Tổng tín chỉ còn thiếu của nhóm tự chọn: "
              f"{electives['remaining_credits'].sum() if not electives.empty else 0:g}")
    return result

summarize_required_courses("2310009")


def view_student_results(student_id):
    student_id_str = str(student_id)
    data_dir = ROOT_DIR
    semester_frames = []
    course_file = CATALOG_DIR / "course.csv"
    try:
        courses = pd.read_csv(course_file, dtype={"course_code": str})
    except FileNotFoundError:
        print(f"[!] Không tìm thấy {course_file.name}; không thể thêm cột credit.")
        courses = pd.DataFrame(columns=["course_code", "credits"])

    for enrollment_file in sorted(ENROLLMENTS_DIR.glob("enrollment_hk*.csv")):
        semester = enrollment_file.stem.removeprefix("enrollment_").upper()
        class_file = CLASSES_DIR / f"class_{semester.lower()}.csv"
        if not class_file.exists():
            print(f"[!] Bỏ qua {semester}: thiếu {class_file.name}")
            continue

        enrollment = pd.read_csv(enrollment_file, dtype={"student_id": str})
        classes = pd.read_csv(class_file, dtype={"class_id": str})
        if "student_id" not in enrollment.columns or "class_id" not in enrollment.columns:
            print(f"[!] Bỏ qua {enrollment_file.name}: thiếu student_id hoặc class_id")
            continue

        enrollment["student_id"] = enrollment["student_id"].astype(str).str.strip()
        enrollment["class_id"] = enrollment["class_id"].astype(str).str.strip()
        classes["class_id"] = classes["class_id"].astype(str).str.strip()
        student_result = enrollment[enrollment["student_id"] == student_id_str].copy()
        if student_result.empty:
            continue

        class_columns = [
            column for column in ("class_id", "course_code", "course_name")
            if column in classes.columns
        ]
        student_result = student_result.merge(
            classes[class_columns].drop_duplicates("class_id"),
            on="class_id",
            how="left",
            suffixes=("", "_class"),
        )
        if set(("course_code", "credits")).issubset(courses.columns):
            student_result = student_result.merge(
                courses[["course_code", "credits"]].rename(
                    columns={"credits": "credit"}
                ).drop_duplicates(
                    "course_code"
                ),
                on="course_code",
                how="left",
            )
        else:
            student_result["credit"] = "-"
        student_result["Học kỳ"] = semester
        semester_frames.append(student_result)

    if not semester_frames:
        print(f"\n[!] Không tìm thấy bất kỳ dữ liệu nào cho sinh viên có mã: {student_id_str}")
        return

    df_all = pd.concat(semester_frames, ignore_index=True)

    # Tổ chức lại các cột để hiển thị chuyên nghiệp
    base_cols = ['Học kỳ', 'course_code', 'credit', 'course_name']
    end_cols = ['final_score', 'status']
    
    # Lấy động (dynamic) tất cả các cột điểm thành phần có trong data (btl, giua_ky, cuoi_ky, lab, quiz...)
    ignore_cols = ['Học kỳ', 'course_code', 'credit', 'course_name', 'final_score', 'status', 'class_id', 'student_id', 'enrollment_id']
    comp_cols = [c for c in df_all.columns if c not in ignore_cols]

    available_base_cols = [column for column in base_cols if column in df_all.columns]
    available_end_cols = [column for column in end_cols if column in df_all.columns]
    final_cols = available_base_cols + comp_cols + available_end_cols
    df_display = df_all[final_cols]
    
    # Điền dấu '-' vào các ô NaN (những môn không có điểm thành phần đó) để dễ nhìn
    df_display = df_display.fillna('-')

    # In báo cáo ra màn hình
    print(f"\n{'='*90}")
    print(f" BẢNG ĐIỂM CHI TIẾT - SINH VIÊN: {student_id_str} ".center(90, '='))
    print(f"{'='*90}")
    
    for hk in sorted(df_display['Học kỳ'].unique()):
        df_hk = df_display[df_display['Học kỳ'] == hk]
        if not df_hk.empty:
            print(f"\n>>> THỐNG KÊ {hk} <<<")
            # Ẩn cột 'Học kỳ' khi in vì đã có tiêu đề
            print(df_hk.drop(columns=['Học kỳ']).to_string(index=False))
            
            # Tính nhẩm nhanh số môn đậu/rớt trong kỳ
            tong_mon = len(df_hk)
            tong_tin_chi = pd.to_numeric(df_hk["credit"], errors="coerce").sum()
            print(f"Tổng số tín chỉ {hk}: {tong_tin_chi:g} tín chỉ.")
            if "status" in df_hk.columns:
                status = df_hk["status"].astype(str).str.strip().str.casefold()
                mon_dau = (status == "pass").sum()
                print(f"Tổng kết {hk}: Đậu {mon_dau}/{tong_mon} môn.")
            
    print(f"\n{'='*90}\n")



view_student_results("2310009")
# view_student_results("2411288")


def view_fail_result():
    try:
        df_enr = pd.read_csv(ENROLLMENTS_DIR / "enrollment_hk231.csv")
    except FileNotFoundError:
        print("Không tìm thấy file enrollment_hk231.csv")
        exit()

    # 2. Lọc danh sách các môn rớt
    df_fail = df_enr[df_enr['status'] == 'Fail']

    # 3. Đếm số lượng môn rớt trên từng sinh viên
    fail_counts_per_student = df_fail.groupby('student_id').size()

    # 4. Gom nhóm để đếm xem có bao nhiêu sinh viên rớt 1 môn, 2 môn, 3 môn...
    distribution = fail_counts_per_student.value_counts().sort_index()

    # 5. Tính toán các chỉ số tổng quan
    total_students = df_enr['student_id'].nunique()
    students_with_failures = len(fail_counts_per_student)
    students_passed_all = total_students - students_with_failures

    # 6. In báo cáo
    print(f"=== PHÂN PHỐI SỐ LƯỢNG MÔN RỚT - HK231 ===")
    print(f"Tổng số sinh viên: {total_students}")
    print(f"Số SV qua tất cả các môn: {students_passed_all} ({(students_passed_all/total_students)*100:.1f}%)")
    print("-" * 55)
    print(f"{'Số môn rớt':<15} | {'Số lượng sinh viên':<20} | {'Tỷ lệ (%)'}")
    print("-" * 55)

    # In số người rớt 0 môn
    print(f"{'0 môn':<15} | {students_passed_all:<20} | {(students_passed_all/total_students)*100:.1f}%")

    # In số người rớt từ 1 môn trở lên
    for num_fails, count in distribution.items():
        pct = (count / total_students) * 100
        print(f"{str(num_fails) + ' môn':<15} | {count:<20} | {pct:.1f}%")

    print("-" * 55)
    print(">>> CẢNH BÁO QUÁ TẢI (Rớt >= 3 môn):", distribution[distribution.index >= 3].sum(), "sinh viên")


# view_fail_result()



def get_class_roster(semester, class_id):
    """
    Tra cứu thông tin giảng viên và danh sách sinh viên của một lớp trong học kỳ chỉ định.
    
    Parameters:
        semester (str): Học kỳ cần tra cứu (VD: 'HK231', 'HK232', 'HK241')
        class_id (int or str): ID hoặc mã của lớp cần xem
        
    Returns:
        dict: Chứa thông tin giảng viên và DataFrame danh sách sinh viên
    """
    # 1. Xác định tên file dựa theo học kỳ
    class_file = CLASSES_DIR / f"class_{semester.lower()}.csv"
    enrollment_file = ENROLLMENTS_DIR / f"enrollment_{semester.lower()}.csv"
    student_file = PEOPLE_DIR / "student_base_score.csv"
    
    # Kiểm tra sự tồn tại của các file dữ liệu
    for f in [class_file, enrollment_file, student_file]:
        if not os.path.exists(f):
            print(f"[!] Lỗi: Không tìm thấy file dữ liệu '{f}' trong thư mục hiện tại.")
            return None

    # 2. Đọc dữ liệu
    df_class = pd.read_csv(class_file)
    df_enr = pd.read_csv(enrollment_file)
    df_student = pd.read_csv(student_file)
    
    # Đảm bảo kiểu dữ liệu class_id đồng bộ (string hoặc int tùy file của bạn)
    # Thường class_id trong class_csv là int hoặc str, ta ép về string để so sánh an toàn
    df_class['class_id'] = df_class['class_id'].astype(str)
    df_enr['class_id'] = df_enr['class_id'].astype(str)
    class_id_str = str(class_id)
    
    # 3. Lọc thông tin lớp học
    class_info = df_class[df_class['class_id'] == class_id_str]
    if class_info.empty:
        print(f"[!] Không tìm thấy lớp có ID '{class_id_str}' trong học kỳ {semester}.")
        return None
    
    # Lấy thông tin môn và giảng viên
    course_code = class_info['course_code'].values[0]
    course_name = class_info['course_name'].values[0] if 'course_name' in class_info.columns else "N/A"
    lecturer_id = class_info['lecturer_id'].values[0] if 'lecturer_id' in class_info.columns else "N/A"
    lecturer_name = class_info['lecturer_name'].values[0] if 'lecturer_name' in class_info.columns else "N/A"
    
    # 4. Lọc danh sách sinh viên đăng ký lớp này
    enrolled_students = df_enr[df_enr['class_id'] == class_id_str].copy()
    
    if enrolled_students.empty:
        print(f"[!] Lớp {class_id_str} ({course_code} - {course_name}) hiện chưa có sinh viên nào đăng ký.")
        return {
            'lecturer': {'id': lecturer_id, 'name': lecturer_name},
            'course': {'code': course_code, 'name': course_name},
            'students': pd.DataFrame()
        }
    
    # Ghép với bảng student_base_score để lấy thêm thông tin chi tiết (nếu có base_score,...)
    enrolled_students['student_id'] = enrolled_students['student_id'].astype(str)
    df_student['student_id'] = df_student['student_id'].astype(str)
    
    student_details = pd.merge(enrolled_students, df_student, on='student_id', how='left')
    
    # Trả về kết quả dạng cấu trúc dictionary tiện sử dụng
    result = {
        'semester': semester,
        'class_id': class_id_str,
        'course': {'code': course_code, 'name': course_name},
        'lecturer': {'id': lecturer_id, 'name': lecturer_name},
        'total_students': len(student_details),
        'students': student_details
    }
    
    print(f"\n=== DANH SÁCH SINH VIÊN LỚP {class_id_str} ({course_code} - {course_name}) - HỌC KỲ {semester} ===")
    print(f"Giảng viên: {lecturer_name} (ID: {lecturer_id})")
    print(f"Tổng số sinh viên: {len(student_details)}")
    print(student_details.to_string(index=False))
    return result


# get_class_roster('HK231', 1)