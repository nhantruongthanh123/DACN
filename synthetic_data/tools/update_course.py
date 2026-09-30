import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

# 1. Đọc file course.csv hiện tại
file_path = ROOT_DIR / 'data' / 'catalog' / 'course.csv'
df_course = pd.read_csv(file_path)

# 2. Định nghĩa từ điển độ khó theo mã môn học (Course Code)
# Bạn có thể thêm/bớt các môn và chỉnh sửa hệ số tùy ý
course_difficulty = {
    # Môn khó (trừ điểm)
    'MT1003':  0,  # Giải tích 1
    'MT1005': -0.1,  # Giải tích 2
    'PH1003': -0.1,  # Vật lý 1
    'MT1007': -0.2,  # Đại số tuyến tính
    'CO1007': 0,  # Cấu trúc rời rạc
    
    # Môn bình thường
    'CO1027': 0.3,   # Kỹ thuật lập trình
    'MI1003': 0,   # Triết học
    
    # Môn dễ, kéo điểm (cộng điểm)
    'LA1003': 1,   # Anh văn 1
    'LA1005': 0.9,   # Anh văn 2
    'CO1005': 0.8,   # Nhập môn điện toán
    'CH1003': 0.8,   # Hóa đại cương
    'PH1007': 1.2    # Thí nghiệm Vật lý
}

# 3. Tạo cột mới 'difficulty' bằng cách map theo 'course_code'
# Những môn không có trong từ điển trên sẽ mặc định nhận giá trị 0.0
df_course['difficulty'] = df_course['course_code'].map(course_difficulty).fillna(0.0)

# 4. Ghi đè lại vào file course.csv
df_course.to_csv(file_path, index=False, encoding='utf-8-sig')

print(f"Đã cập nhật thành công cột 'difficulty' vào {file_path}")
print("\nDữ liệu mẫu sau khi cập nhật:")
print(df_course.head(10).to_string(index=False))