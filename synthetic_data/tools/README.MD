# Công cụ chuẩn bị và sinh dữ liệu

Thư mục `tools` chứa các script hỗ trợ chuẩn bị dữ liệu nguồn và chạy chuỗi
sinh lớp học/phân công đăng ký học phần. Chạy lệnh từ thư mục gốc dự án để các
đường dẫn tương đối và môi trường ảo được sử dụng nhất quán.

```bash
source .venv/bin/activate
python synthetic_data/tools/<ten_file>.py
```

Trên Windows, kích hoạt môi trường bằng `.venv\\Scripts\\activate`.

## Thứ tự sử dụng đề xuất

1. Chuẩn bị `synthetic_data/data/people/student.csv`, `synthetic_data/data/people/lecture.csv` và các file
   danh mục trong `synthetic_data/data/catalog/`.
2. Chạy `add_base_score.py` để tạo dữ liệu năng lực nền của sinh viên.
3. Chạy `add_lecture_dep.py` để tạo dữ liệu giảng viên phục vụ phân lớp.
4. Chạy `update_course.py` nếu cần cập nhật cột `difficulty` trong danh mục
   môn học.
5. Chạy `run_all.py` để sinh lớp và đăng ký học phần cho toàn bộ học kỳ.
6. (Tuỳ chọn) Chạy `generate_student_progress.py` để xuất kế hoạch học tập
   chuẩn theo khóa.

## Các file

### `add_base_score.py`

Đọc `synthetic_data/data/people/student.csv`, tạo điểm năng lực nền ngẫu nhiên và ghi
`synthetic_data/data/people/student_base_score.csv`. Điểm được phân theo bốn nhóm: Giỏi,
Khá, Trung bình và Yếu. File này là đầu vào của các generator lớp và đăng ký.

```bash
python synthetic_data/tools/add_base_score.py
```

Chạy lại script sẽ tạo lại điểm ngẫu nhiên, nên có thể làm thay đổi kết quả
sinh enrollment ở các lần sau.

### `add_lecture_dep.py`

Đọc `synthetic_data/data/people/lecture.csv`, gán bộ môn cho giảng viên và ghi
`synthetic_data/data/people/lecturer_for_class.csv`. Script dùng seed cố định nên phân bổ giữ
nguyên khi dữ liệu đầu vào không đổi.

```bash
python synthetic_data/tools/add_lecture_dep.py
```

### `update_course.py`

Đọc rồi ghi đè `synthetic_data/data/catalog/course.csv`, thêm/cập nhật cột `difficulty` theo
từ điển `course_difficulty` trong mã nguồn. Giá trị dương thường làm môn dễ
hơn khi sinh điểm; giá trị âm làm môn khó hơn.

```bash
python synthetic_data/tools/update_course.py
```

Hãy sao lưu hoặc commit `course.csv` trước khi chạy nếu cần giữ cấu hình cũ.

### `run_all.py`

Chạy lần lượt generator class và enrollment từ HK231 đến HK261. Script dừng
ngay khi một generator lỗi, do đó cần xử lý lỗi rồi chạy lại toàn bộ chuỗi.
Nó sử dụng `sys.executable`, vì vậy tự dùng đúng Python/môi trường ảo đã gọi
script.

```bash
python synthetic_data/tools/run_all.py
```

Kết quả được ghi vào:

- `synthetic_data/generated/classes/class_hk*.csv`
- `synthetic_data/generated/enrollments/enrollment_hk*.csv`

Lưu ý: chạy lệnh này sẽ ghi đè các file generated hiện có.

### `generate_student_progress.py`

Đọc `synthetic_data/data/catalog/course.csv` và xuất kế hoạch môn học đề xuất theo khóa vào
`synthetic_data/student_curriculum_plan.csv`. Đây là khung chương trình chuẩn, không phải
lịch sử điểm hoặc danh sách đăng ký thực tế của từng sinh viên.

```bash
python synthetic_data/tools/generate_student_progress.py
```

Nếu mã môn trong `CURRICULUM_PLAN` không tồn tại trong `course.csv`, script sẽ
dừng và báo mã môn bị thiếu.

## Kiểm tra nhanh đầu vào

Trước khi chạy `run_all.py`, tối thiểu cần có các file sau:

- `synthetic_data/data/people/student_base_score.csv`
- `synthetic_data/data/people/lecturer_for_class.csv`
- `synthetic_data/data/catalog/course.csv`
- `synthetic_data/data/catalog/assessment.csv`
- `synthetic_data/data/catalog/course_prerequisite.csv`

