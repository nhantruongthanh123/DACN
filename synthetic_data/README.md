# Dữ liệu mô phỏng quản lý đào tạo

`synthetic_data` là bộ dữ liệu mô phỏng cho bài toán quản lý đào tạo ngành Computer Science: danh mục môn học, chương trình, sinh viên, giảng viên, lớp học phần, đăng ký và điểm theo học kỳ. Toàn bộ dữ liệu là **dữ liệu tổng hợp**, không phải dữ liệu học vụ thực tế.

## Cấu trúc thư mục

```text
synthetic_data/
├── data/        # Dữ liệu nguồn
├── rules/       # Quy tắc chương trình và học vụ
├── generators/  # Script sinh lớp, enrollment và điểm
├── generated/   # Kết quả sinh ra
└── tools/       # Script chuẩn bị dữ liệu và điều phối
```

| Thư mục | Vai trò | Tài liệu chi tiết |
| --- | --- | --- |
| `data/` | Dữ liệu nguồn về học kỳ, danh mục môn, sinh viên và giảng viên. | [data/README.MD](data/README.MD) |
| `rules/` | Xét môn học, tiên quyết, học lại, tự chọn, tín chỉ và độ khó môn. | [rules/README.MD](rules/README.MD) |
| `generators/` | Tạo lớp, phân sinh viên vào lớp và mô phỏng điểm từ HK231 đến HK261. | [generators/README.MD](generators/README.MD) |
| `tools/` | Tạo điểm nền, phân bộ môn giảng viên, cập nhật độ khó và chạy generator. | [tools/README.MD](tools/README.MD) |
| `generated/` | File đầu ra có thể tạo lại, không phải dữ liệu nguồn. | Xem phần dưới. |

## Dữ liệu nguồn: `data/`

`data/` có ba nhóm lớn.

### `data/academic/` — mốc thời gian

- `semester.csv`: danh sách học kỳ, gồm mã kỳ (`semester_code`), niên khóa và số thứ tự kỳ. Mã như `HK231`, `HK242` xuất hiện trong tên file class và enrollment.

### `data/catalog/` — chương trình đào tạo và môn học

- `course.csv`: danh mục môn chuẩn (`course_code`, tên, tín chỉ, `difficulty`).
- `assessment.csv`: cơ cấu điểm theo môn, gồm trọng số `quiz`, `lab`, `btl`, `giua_ky`, `cuoi_ky`.
- `course_prerequisite.csv`: quan hệ môn học; logic hiện tại bắt buộc quan hệ `TQ` khi xét đăng ký.
- `curriculum_computer_science.csv`: môn theo khung chương trình HK1–HK8.
- `additional_course_rules.csv`: môn bổ sung/học sớm và điều kiện áp dụng.
- `elective_courses.csv`, `management_electives.csv`, `group_c_electives.csv`: môn tự chọn theo nhóm.

### `data/people/` — sinh viên và giảng viên

- `student.csv`: hồ sơ sinh viên gốc, gồm mã sinh viên, khóa, ngành và thông tin liên hệ.
- `student_base_score.csv`: điểm năng lực nền trên thang 10; là đầu vào chính để mô phỏng điểm.
- `lecture.csv`: hồ sơ giảng viên gốc.
- `lecturer_for_class.csv`: giảng viên đã gắn bộ môn `Triet`, `DaiCuong` hoặc `ChuyenNganh` để generator phân công lớp.

Xem [data/README.MD](data/README.MD) để biết vai trò và cấu trúc cột của từng CSV.

## Dữ liệu được sinh: `generated/`

| Loại file | Mẫu tên | Nội dung chính |
| --- | --- | --- |
| Lớp học phần | `generated/classes/class_hk*.csv` | `class_id`, mã/tên môn, học kỳ, nhóm lớp và giảng viên phụ trách. |
| Đăng ký/điểm | `generated/enrollments/enrollment_hk*.csv` | Sinh viên, lớp được xếp, điểm thành phần, `final_score`, `status`. |

Các file liên kết qua `class_id`: enrollment ghi lớp sinh viên được xếp, còn file class xác định môn và giảng viên. Nhờ vậy lịch sử enrollment có thể được ghép với class để xác định sinh viên đã học, đậu hoặc trượt môn nào.

HK261 là ngoại lệ: enrollment được tạo cho học kỳ đang diễn ra nên `final_score` và `status` chưa có giá trị.

## Quy trình tạo dữ liệu

```text
student.csv ──> add_base_score.py ──> student_base_score.csv
lecture.csv ──> add_lecture_dep.py ──> lecturer_for_class.csv
catalog CSV + people CSV + rules ──> generator class ──> class_hk*.csv
class_hk*.csv + lịch sử + assessment ──> generator enrollment ──> enrollment_hk*.csv
```

Chạy quy trình đầy đủ từ thư mục gốc dự án:

```bash
source .venv/bin/activate
python synthetic_data/tools/run_all.py
```

Lệnh chạy các kỳ theo thứ tự HK231 → HK261 và ghi đè CSV trong `synthetic_data/generated/`. Khi thay đổi dữ liệu nguồn, cấu trúc điểm hoặc quy tắc học vụ, hãy chạy lại toàn bộ chuỗi để lịch sử các kỳ nhất quán.

## Quy ước quan trọng

- `student_id` có tiền tố như `231`, `241`, `251`, `261` để nhận biết khóa; rule dùng tiền tố này khi chọn chương trình phù hợp.
- `course_code` là mã liên kết chính giữa danh mục môn, class, tiên quyết và enrollment.
- `credits` được dùng để giữ số tín chỉ đăng ký không vượt 22 trong một kỳ.
- `status` là `Pass` nếu `final_score >= 5`, ngược lại là `Fail`.
- Đường dẫn trong tài liệu được viết từ thư mục gốc dự án.
