import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
import numpy as np
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent

# 1. Đọc dữ liệu sinh viên từ file gốc
df_student = pd.read_csv(ROOT_DIR / 'data' / 'people' / 'student.csv')

# (Tùy chọn) Nếu file của bạn đang tách họ và tên, hãy gộp lại thành 1 cột 'name' bằng lệnh dưới đây:
# df_student['name'] = df_student['last_name'] + ' ' + df_student['first_name']

def generate_base_score(num_students):
    scores = []
    
    # Khai báo nhóm và tỷ lệ bạn đã chốt
    tiers = ['Gioi', 'Kha', 'TrungBinh', 'Yeu']
    probabilities = [0.12, 0.33, 0.40, 0.15]
    
    # Bốc thăm nhóm ngẫu nhiên theo đúng tỷ lệ trên
    assigned_tiers = np.random.choice(tiers, size=num_students, p=probabilities)
    
    # Random điểm số nằm trong khoảng của nhóm đã bốc trúng
    for tier in assigned_tiers:
        if tier == 'Gioi':
            score = np.random.uniform(8.0, 10)
        elif tier == 'Kha':
            score = np.random.uniform(7.0, 7.9)
        elif tier == 'TrungBinh':
            score = np.random.uniform(5.5, 6.9)
        else: # Yeu
            score = np.random.uniform(4.0, 5.4)
            
        scores.append(round(score, 1)) # Làm tròn 1 chữ số thập phân
        
    return scores

# 2. Tạo một DataFrame mới chỉ lấy 2 cột cần thiết
# Lưu ý: Sửa tên cột 'student_id' và 'name' cho khớp với header trong file student_2.csv của bạn
df_result = df_student[['student_id', 'name']].copy()

# 3. Gán điểm base_score
df_result['base_score'] = generate_base_score(len(df_result))

# 4. Xuất ra file CSV mới
output_file = ROOT_DIR / 'data' / 'people' / 'student_base_score.csv'
df_result.to_csv(output_file, index=False, encoding='utf-8-sig')

# 5. In báo cáo kiểm tra tỷ lệ
print(f"Xong! Đã tạo file: {output_file}")
print("\n--- KIỂM TRA LẠI TỶ LỆ PHÂN BỐ SAU KHI RANDOM ---")
# Cắt điểm thành các khoảng để đếm lại xem code chạy có chuẩn tỷ lệ không
bins = [0, 4.9, 6.9, 7.9, 10.0]
labels = ['Yếu (3.0-4.9)', 'Trung Bình (5.0-6.9)', 'Khá (7.0-7.9)', 'Giỏi (8.0-9.5)']
df_result['tier'] = pd.cut(df_result['base_score'], bins=bins, labels=labels)

distribution = df_result['tier'].value_counts(normalize=True) * 100
print(distribution.round(2).astype(str) + ' %')