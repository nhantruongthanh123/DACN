import hashlib
import pandas as pd
import numpy as np
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "rules"))

from academic_rules import (
    add_gpa_summaries,
    allocate_course_rosters,
    can_skip_la1003,
    load_student_profiles,
    score_course_components,
    semester_index,
)

# ==========================================
# 1. ĐỌC DỮ LIỆU ĐÃ CHUẨN BỊ
# ==========================================
df_student = load_student_profiles()
df_class = pd.read_csv(ROOT_DIR / 'generated' / 'classes' / 'class_hk131.csv')
df_assessment = pd.read_csv(ROOT_DIR / 'data' / 'catalog' / 'assessment.csv')

# BỔ SUNG: Đọc thêm file course.csv để lấy cột độ khó (difficulty)
if (ROOT_DIR / 'data' / 'catalog' / 'course.csv').exists():
    df_course = pd.read_csv(ROOT_DIR / 'data' / 'catalog' / 'course.csv')
    if 'difficulty' in df_course.columns:
        difficulty_dict = dict(zip(df_course['course_code'], df_course['difficulty']))
    else:
        difficulty_dict = {}
    course_credits = dict(zip(df_course['course_code'], df_course['credits']))
else:
    difficulty_dict = {}
    course_credits = {}

# Đảm bảo chỉ lấy sinh viên K13
df_k13 = df_student[df_student['student_id'].astype(str).str.startswith('13')].copy()

# Xử lý cấu trúc điểm từ file assessment.csv thực tế của bạn
course_assessments = {}
component_columns = ['quiz', 'lab', 'btl', 'giua_ky', 'cuoi_ky']

for _, row in df_assessment.iterrows():
    course = row['course_id']  
    comps = []
    
    for col in component_columns:
        if col in df_assessment.columns:
            weight = row[col]
            if pd.notna(weight) and float(weight) > 0:
                comps.append({
                    'name': col,
                    'weight': float(weight) / 100.0  
                })
    course_assessments[course] = comps

# ==========================================
# 3. THỰC THI PHÂN BỔ & TÍNH ĐIỂM THÀNH PHẦN
# ==========================================
enrollment_data = []
enrollment_id_counter = 1

students_by_course = {}
for course in df_class['course_code'].unique():
    if course == 'LA1003':
        mask_take_english = df_k13.apply(
            lambda row: not can_skip_la1003(row['student_id'], row['base_score']),
            axis=1,
        )
        students_for_course = df_k13[mask_take_english].copy()
    else:
        students_for_course = df_k13.copy()
    students_by_course[course] = students_for_course['student_id'].tolist()

course_rosters = allocate_course_rosters(students_by_course, df_class)
students_by_id = df_student.set_index('student_id')

for course, assignments in course_rosters.items():
    difficulty_index = difficulty_dict.get(course, 0.0)
    comps = course_assessments.get(course, [])
    if not comps:
        comps = [{'name': 'cuoi_ky', 'weight': 1.0}]
    for class_id, student_ids in assignments:
        for student_id in student_ids:
            student = students_by_id.loc[student_id]
            record = {
                'enrollment_id': enrollment_id_counter,
                'student_id': student_id,
                'class_id': class_id,
                'course_id': course,
                'semester': semester_index("HK131"),
                'retaken': False,
            }
            rng = np.random.default_rng(int(hashlib.sha256(
                f"{student_id}:{course}".encode("utf-8")
            ).hexdigest()[:8], 16))
            component_scores, final_score, letter, gpa = score_course_components(
                student,
                course,
                [(comp["name"], comp["weight"]) for comp in comps],
                difficulty_index,
                rng,
                student_id=student_id,
            )
            record.update(component_scores)
            record['final_score'] = final_score
            record['letter_grade'] = letter
            record['gpa_4'] = gpa
            record['passed'] = letter != "F"
            record['status'] = 'Pass' if record['passed'] else 'Fail'
            
            enrollment_data.append(record)
            enrollment_id_counter += 1

# ==========================================
# 4. XUẤT FILE & BÁO CÁO
# ==========================================
df_enrollment = pd.DataFrame(enrollment_data)
df_enrollment = add_gpa_summaries(
    df_enrollment,
    pd.DataFrame(columns=["student_id", "course_code", "final_score"]),
    course_credits,
)

base_cols = [
    'enrollment_id',
    'student_id',
    'class_id',
    'course_id',
    'semester',
    'retaken',
]
end_cols = [
    'final_score',
    'letter_grade',
    'gpa_4',
    'passed',
    'semester_gpa_4',
    'final_gpa_4',
    'status',
]
component_cols = [col for col in df_enrollment.columns if col not in base_cols + end_cols]
df_enrollment = df_enrollment[base_cols + component_cols + end_cols]

output_file = ROOT_DIR / 'generated' / 'enrollments' / 'enrollment_hk131.csv'
df_enrollment.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"=== ĐÃ TẠO THÀNH CÔNG BẢNG ĐĂNG KÝ HỌC PHẦN: {output_file} ===")
print(f"Tổng số bản ghi điểm: {len(df_enrollment)}")

df_merged = pd.merge(df_enrollment, df_class, on='class_id')
stats = df_merged.groupby('course_name')['student_id'].count() / df_merged.groupby('course_name')['class_id'].nunique()
print("\n=== THỐNG KÊ SĨ SỐ TRUNG BÌNH THEO MÔN HỌC ===")
print(stats.round(1).astype(str) + ' sinh viên/lớp')

print("\n=== XEM TRƯỚC DỮ LIỆU ĐIỂM (NaN nghĩa là môn đó không có điểm thành phần này) ===")
print(df_enrollment.head().to_string())