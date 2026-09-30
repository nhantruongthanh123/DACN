import pandas as pd
import numpy as np
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

# 1. Đọc dữ liệu từ file lecture.csv (chứa lecture_id, name, email...)
df_lecture = pd.read_csv(ROOT_DIR / 'data' / 'people' / 'lecture.csv')

# 2. Định nghĩa các nhóm bộ môn và tỷ lệ phân bổ
departments_list = ['ChuyenNganh', 'DaiCuong', 'Triet']
probabilities = [0.60, 0.20, 0.20]

# 3. Phân bổ ngẫu nhiên department cho toàn bộ giảng viên theo tỷ lệ
np.random.seed(42) # Cố định seed để nếu chạy lại thì chuyên môn của GV không bị thay đổi
assigned_departments = np.random.choice(
    departments_list, 
    size=len(df_lecture), 
    p=probabilities
)

# 4. Lọc và đổi tên cột để tạo file mới chỉ gồm 3 trường dữ liệu cần thiết
df_class_setup = pd.DataFrame({
    'lecturer_id': df_lecture['lecture_id'],
    'lecturer_name': df_lecture['name'],
    'departments': assigned_departments
})

# 5. Lưu kết quả ra file CSV mới dùng cho việc xếp lớp
output_file = ROOT_DIR / 'data' / 'people' / 'lecturer_for_class.csv'
df_class_setup.to_csv(output_file, index=False, encoding='utf-8-sig')

# 6. In báo cáo kiểm tra trực quan
print(f"Đã tạo thành công file: {output_file}")
print("\n=== THỐNG KÊ TỶ LỆ PHÂN BỔ BỘ MÔN ===")
distribution = df_class_setup['departments'].value_counts(normalize=True) * 100
print(distribution.round(1).astype(str) + ' %')

print("\n=== MẪU DỮ LIỆU ĐỂ TẠO LỚP ===")
print(df_class_setup.head())