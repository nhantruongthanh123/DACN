import hashlib
import os
import pandas as pd
import numpy as np
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

# ==========================================
# 1. ĐỌC DỮ LIỆU ĐÃ CHUẨN BỊ
# ==========================================
df_student = pd.read_csv(ROOT_DIR / 'data' / 'people' / 'student_base_score.csv')
df_class = pd.read_csv(ROOT_DIR / 'generated' / 'classes' / 'class_hk231.csv')
df_assessment = pd.read_csv(ROOT_DIR / 'data' / 'catalog' / 'assessment.csv')

# BỔ SUNG: Đọc thêm file course.csv để lấy cột độ khó (difficulty)
if (ROOT_DIR / 'data' / 'catalog' / 'course.csv').exists():
    df_course = pd.read_csv(ROOT_DIR / 'data' / 'catalog' / 'course.csv')
    if 'difficulty' in df_course.columns:
        difficulty_dict = dict(zip(df_course['course_code'], df_course['difficulty']))
    else:
        difficulty_dict = {}
else:
    difficulty_dict = {}

# Đảm bảo chỉ lấy sinh viên K23
df_k23 = df_student[df_student['student_id'].astype(str).str.startswith('231')].copy()

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
# 2. HÀM KIỂM TRA SKIP TIẾNG ANH 1
# ==========================================
def can_skip_la1003(student_id, base_score):
    digest = hashlib.sha256(
        f"{student_id}:{base_score}".encode('utf-8')
    ).hexdigest()
    rand_val = int(digest[:8], 16) / 0xFFFFFFFF
    if base_score >= 8.0:      
        return True
    elif base_score >= 7.0:    
        return rand_val < 0.70
    elif base_score >= 5.0:    
        return rand_val < 0.15
    return False               

# ==========================================
# 3. THỰC THI PHÂN BỔ & TÍNH ĐIỂM THÀNH PHẦN
# ==========================================
enrollment_data = []
enrollment_id_counter = 1

courses = df_class['course_code'].unique()

for course in courses:
    # Lấy hệ số độ khó của môn học hiện tại (mặc định 0.0 nếu chưa cấu hình)
    difficulty_index = difficulty_dict.get(course, 0.0)

    if course == 'LA1003':
        mask_take_english = df_k23.apply(
            lambda row: not can_skip_la1003(row['student_id'], row['base_score']),
            axis=1,
        )
        students_for_course = df_k23[mask_take_english].copy()
    else:
        students_for_course = df_k23.copy()
        
    if students_for_course.empty:
        continue
        
    students_for_course = students_for_course.sample(frac=1).reset_index(drop=True)
    
    class_ids = df_class[df_class['course_code'] == course]['class_id'].tolist()
    num_classes = len(class_ids)
    if num_classes == 0:
        continue
    
    split_indices = np.array_split(np.arange(len(students_for_course)), num_classes)
    
    comps = course_assessments.get(course, [])
    
    if not comps:
        comps = [{'name': 'cuoi_ky', 'weight': 1.0}]
    
    for class_id, index_chunk in zip(class_ids, split_indices):
        chunk = students_for_course.iloc[index_chunk]
        for student in chunk.itertuples(index=False):
            
            record = {
                'enrollment_id': enrollment_id_counter,
                'student_id': student.student_id,
                'class_id': class_id
            }
            
            final_score = 0.0
            
            for comp in comps:
                noise = np.random.normal(0, 1.2) 
                
                # CẬP NHẬT: Tích hợp hệ số độ khó vào học lực nền để thay đổi tỷ lệ qua môn
                dynamic_difficulty = difficulty_index + np.random.uniform(0, 0.3)
                
                # Kết hợp: Điểm nền + Độ khó động
                effective_base = student.base_score + dynamic_difficulty
                
                comp_score = round(max(0.0, min(effective_base + noise, 10.0)), 1)
                
                record[comp['name']] = comp_score
                final_score += comp_score * comp['weight']
            
            final_score = round(final_score, 1)
            record['final_score'] = final_score
            record['status'] = 'Pass' if final_score >= 5.0 else 'Fail'
            
            enrollment_data.append(record)
            enrollment_id_counter += 1

# ==========================================
# 4. XUẤT FILE & BÁO CÁO
# ==========================================
df_enrollment = pd.DataFrame(enrollment_data)

base_cols = ['enrollment_id', 'student_id', 'class_id']
end_cols = ['final_score', 'status']
component_cols = [col for col in df_enrollment.columns if col not in base_cols + end_cols]
df_enrollment = df_enrollment[base_cols + component_cols + end_cols]

output_file = ROOT_DIR / 'generated' / 'enrollments' / 'enrollment_hk231.csv'
df_enrollment.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"=== ĐÃ TẠO THÀNH CÔNG BẢNG ĐĂNG KÝ HỌC PHẦN: {output_file} ===")
print(f"Tổng số bản ghi điểm: {len(df_enrollment)}")

df_merged = pd.merge(df_enrollment, df_class, on='class_id')
stats = df_merged.groupby('course_name')['student_id'].count() / df_merged.groupby('course_name')['class_id'].nunique()
print("\n=== THỐNG KÊ SĨ SỐ TRUNG BÌNH THEO MÔN HỌC ===")
print(stats.round(1).astype(str) + ' sinh viên/lớp')

print("\n=== XEM TRƯỚC DỮ LIỆU ĐIỂM (NaN nghĩa là môn đó không có điểm thành phần này) ===")
print(df_enrollment.head().to_string())