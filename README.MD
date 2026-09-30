# Synthetic Academic Data Generator

Repository này tạo dữ liệu học vụ **mô phỏng** cho ngành Computer Science. Hệ
thống sinh danh mục lớp học phần, phân công giảng viên, đăng ký môn học, điểm
thành phần và kết quả học tập theo nhiều học kỳ. Dữ liệu phục vụ phát triển,
kiểm thử và phân tích tiến độ học tập; không chứa dữ liệu học vụ thực tế.

## Chức năng chính

- Chuẩn bị điểm năng lực nền cho sinh viên và bộ môn cho giảng viên.
- Xét môn được đăng ký theo khóa, chương trình, tiên quyết, học lại, môn tự
  chọn và giới hạn tín chỉ.
- Mở lớp theo nhu cầu, chia sĩ số và gán giảng viên phù hợp.
- Sinh enrollment, điểm thành phần, điểm tổng kết và trạng thái `Pass`/`Fail`.
- Tổng hợp bảng điểm, môn còn thiếu, danh sách rớt và danh sách lớp.

## Cấu trúc repository

```text
.
├── README.MD
├── requirements.txt
└── synthetic_data/
    ├── data/        # Dữ liệu nguồn: học kỳ, danh mục, sinh viên, giảng viên
    ├── rules/       # Rule chương trình đào tạo và học vụ
    ├── generators/  # Generator class/enrollment cho HK231 đến HK261
    ├── generated/   # CSV class và enrollment được sinh ra
    ├── tools/       # Script chuẩn bị dữ liệu và chạy toàn bộ pipeline
    └── analysis/    # Hàm xem bảng điểm, tiến độ và lớp học
```

## Bắt đầu nhanh

Tạo môi trường ảo và cài dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Trên Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

Sinh toàn bộ dữ liệu theo thứ tự học kỳ HK231 → HK261:

```bash
python synthetic_data/tools/run_all.py
```

Lệnh này tự chạy các cặp generator class/enrollment đúng thứ tự và ghi đè các
file trong `synthetic_data/generated/`.

## Quy trình dữ liệu

```text
student.csv ──> add_base_score.py ──> student_base_score.csv
lecture.csv ──> add_lecture_dep.py ──> lecturer_for_class.csv
catalog + people + rules ──> generate_class_hk*.py ──> class_hk*.csv
class + history + assessment ──> generate_enrollment_hk*.py ──> enrollment_hk*.csv
```

Các file đầu vào quan trọng trước khi chạy generator:

- `synthetic_data/data/people/student_base_score.csv`
- `synthetic_data/data/people/lecturer_for_class.csv`
- `synthetic_data/data/catalog/course.csv`
- `synthetic_data/data/catalog/assessment.csv`
- `synthetic_data/data/catalog/course_prerequisite.csv`

Nếu cần tạo lại hai file dẫn xuất đầu tiên, chạy:

```bash
python synthetic_data/tools/add_base_score.py
python synthetic_data/tools/add_lecture_dep.py
```

## Kết quả tạo ra

| Loại | Vị trí | Nội dung |
| --- | --- | --- |
| Lớp học phần | `synthetic_data/generated/classes/class_hk*.csv` | Mã lớp, môn học, học kỳ, nhóm lớp và giảng viên. |
| Đăng ký/điểm | `synthetic_data/generated/enrollments/enrollment_hk*.csv` | Sinh viên, lớp, điểm thành phần, `final_score`, `status`. |

`status` có giá trị `Pass` nếu `final_score >= 5`, ngược lại là `Fail`. HK261
mô phỏng học kỳ chưa kết thúc nên `final_score` và `status` được để trống.

## Phân tích dữ liệu

`synthetic_data/analysis/analysis.py` chứa các hàm để:

- `summarize_required_courses(student_id)`: liệt kê môn bắt buộc/học lại và
  tiến độ nhóm tự chọn.
- `view_student_results(student_id)`: in bảng điểm theo học kỳ, gồm tín chỉ và
  số môn đậu.
- `view_fail_result()`: thống kê kết quả rớt.
- `get_class_roster(semester, class_id)`: xem danh sách sinh viên trong lớp.

File hiện có sẵn lời gọi minh họa cho mã sinh viên `2310009`; chạy trực tiếp để
xem báo cáo mẫu:

```bash
python synthetic_data/analysis/analysis.py
```

Đổi mã sinh viên trong các lời gọi minh họa hoặc import các hàm này vào script
riêng khi cần phân tích người học khác.

## Tài liệu chi tiết

- [Tổng quan dữ liệu nguồn](synthetic_data/README.md)
- [Cấu trúc và vai trò từng CSV](synthetic_data/data/README.MD)
- [Quy tắc chương trình và học vụ](synthetic_data/rules/README.MD)
- [Generator theo từng học kỳ](synthetic_data/generators/README.MD)
- [Các công cụ hỗ trợ](synthetic_data/tools/README.MD)

## Lưu ý

- Dữ liệu trong repository là dữ liệu tổng hợp; không dùng để suy luận về cá
  nhân thật.
- `student_id` và `course_code` là các khóa liên kết chính giữa những CSV.
- Khi thay đổi danh mục môn, cơ cấu điểm, tiên quyết hoặc điểm nền, nên chạy lại
  `synthetic_data/tools/run_all.py` để lịch sử học tập giữa các kỳ đồng nhất.
