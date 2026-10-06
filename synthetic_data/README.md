# Dữ liệu mô phỏng quản lý đào tạo

`synthetic_data` là bộ dữ liệu mô phỏng cho bài toán quản lý đào tạo ngành Computer Science: danh mục môn học, chương trình, sinh viên, giảng viên, lớp học phần, đăng ký và điểm theo học kỳ. Toàn bộ dữ liệu là **dữ liệu tổng hợp**, không phải dữ liệu học vụ thực tế.

## Cấu trúc thư mục

```text
synthetic_data/
├── data/        # Dữ liệu nguồn
├── config/      # Cấu hình hồ sơ, điểm và độ khó theo môn
├── rules/       # Quy tắc chương trình và học vụ
├── generators/  # Script sinh lớp, enrollment và điểm
├── generated/   # Kết quả sinh ra
└── tools/       # Script chuẩn bị dữ liệu và điều phối
```

| Thư mục | Vai trò | Tài liệu chi tiết |
| --- | --- | --- |
| `data/` | Dữ liệu nguồn về học kỳ, danh mục môn, sinh viên và giảng viên. | [data/README.MD](data/README.MD) |
| `config/` | Phân phối hồ sơ/điểm, difficulty theo môn và chính sách CTXH, tiếng Anh, tốt nghiệp, dropout. | [config/generator_config.json](config/generator_config.json) |
| `rules/` | Xét môn học, tiên quyết, học lại, điều kiện đồ án và mô phỏng điểm. | [rules/README.MD](rules/README.MD) |
| `generators/` | Tạo lớp, phân sinh viên vào lớp và mô phỏng điểm từ HK231 đến HK261. | [generators/README.MD](generators/README.MD) |
| `tools/` | Tạo điểm nền, phân bộ môn giảng viên, cập nhật độ khó và chạy generator. | [tools/README.MD](tools/README.MD) |
| `generated/` | File đầu ra có thể tạo lại, không phải dữ liệu nguồn. | Xem phần dưới. |

## Dữ liệu nguồn: `data/`

`data/` có ba nhóm lớn.

### `data/academic/` — mốc thời gian

- `semester.csv`: danh sách học kỳ, gồm mã kỳ (`semester_code`), niên khóa và số thứ tự kỳ. Mã như `HK131`, `HK142` xuất hiện trong tên file class và enrollment.

### `data/catalog/` — chương trình đào tạo và môn học

- `course.csv`: danh mục môn chuẩn (`course_code`, tên, tín chỉ, `difficulty`).
- `assessment.csv`: cơ cấu điểm theo môn, gồm trọng số `quiz`, `lab`, `btl`, `giua_ky`, `cuoi_ky`.
- `course_prerequisite.csv`: quan hệ môn học; logic hiện tại bắt buộc quan hệ `TQ` khi xét đăng ký.
- `curriculum_computer_science.csv`: môn theo khung chương trình HK1–HK8.
- `additional_course_rules.csv`: môn bổ sung/học sớm và điều kiện áp dụng.
- `elective_courses.csv`, `management_electives.csv`, `group_c_electives.csv`: môn tự chọn theo nhóm.

### `data/people/` — sinh viên và giảng viên

- `student.csv`: hồ sơ sinh viên gốc, gồm mã sinh viên, khóa, ngành và thông tin liên hệ.
- `student_base_score.csv`: profile cũ, chỉ làm fallback trước khi tạo profile mới.
- `lecture.csv`: hồ sơ giảng viên gốc.
- `lecturer_for_class.csv`: giảng viên đã gắn bộ môn `Triet`, `DaiCuong` hoặc `ChuyenNganh` để generator phân công lớp.

Xem [data/README.MD](data/README.MD) để biết vai trò và cấu trúc cột của từng CSV.

## Dữ liệu được sinh: `generated/`

| Loại file | Mẫu tên | Nội dung chính |
| --- | --- | --- |
| Profile sinh viên | `generated/student_profile/student_profiles.csv` | Background, personality, academic/subject ability và điểm nền cho sinh viên nguồn khóa 2013 trở đi. |
| Lớp học phần | `generated/classes/class_hk*.csv` | `class_id`, mã/tên môn, học kỳ, nhóm lớp và giảng viên phụ trách. |
| Đăng ký/điểm | `generated/enrollments/enrollment_hk*.csv` | Sinh viên, lớp/môn, điểm thành phần, grade, GPA môn/học kỳ và GPA tích lũy. |
| Metric | `generated/metrics/` | Tiến độ sinh viên, trạng thái tốt nghiệp/dropout, phân phối điểm và tổng hợp toàn trường. |

Các file liên kết qua `class_id`: enrollment ghi lớp sinh viên được xếp, còn file class xác định môn và giảng viên. Nhờ vậy lịch sử enrollment có thể được ghép với class để xác định sinh viên đã học, đậu hoặc trượt môn nào.

HK161 là kỳ cuối của chuỗi mô phỏng; enrollment vẫn sinh đầy đủ
`final_score`, grade và `status` như các kỳ trước.

## Quy trình tạo dữ liệu

```text
student.csv ──> add_base_score.py ──> generated/student_profile/student_profiles.csv
lecture.csv ──> add_lecture_dep.py ──> lecturer_for_class.csv
catalog CSV + people CSV + rules ──> generator class ──> class_hk*.csv
class_hk*.csv + lịch sử + assessment ──> generator enrollment ──> enrollment_hk*.csv
profile + classes + enrollments ──> generate_academic_metrics.py ──> generated/metrics/
```

Chạy quy trình đầy đủ từ thư mục gốc dự án:

```bash
source .venv/bin/activate
python synthetic_data/tools/run_all.py
```

Lệnh tạo profile trước, sau đó chạy theo từng cặp class → enrollment trong thứ
tự HK131 → HK161 và ghi đè CSV trong `synthetic_data/generated/`. Không thể
tạo toàn bộ class của các kỳ trước enrollment vì nhu cầu lớp ở kỳ sau phụ thuộc
lịch sử enrollment các kỳ trước.

`student_progress` trong `config/generator_config.json` cấu hình điều kiện CTXH,
tiếng Anh, tốt nghiệp và dropout. Mỗi profile có `ctxh_days_by_semester` dạng
JSON array với ngày tích lũy theo kỳ và trường boolean `english_pass`. Môn
`CO4029` và `CO4337` chỉ được đăng ký khi sinh viên đã tích lũy ít nhất 12 ngày
CTXH trước kỳ học và đạt điều kiện tiếng Anh. Tốt nghiệp cần ít nhất 15 ngày
CTXH, tiếng Anh, hoàn thành các môn bắt buộc trong curriculum và `CO4337`;
ngưỡng phân loại GPA4 cũng được cấu hình.

Dropout tự nguyện dùng xác suất 30% cho nhóm rủi ro (background thấp hoặc
academic level thấp), với trọng số nguyên nhân background/academic 95%/5%.
Buộc thôi học nếu có hai kỳ liên tiếp dưới 10 tín chỉ pass hoặc đã qua 12 học
kỳ mà chưa tốt nghiệp. Kỳ không đăng ký được ghi rõ trong `student_progress.csv`.

Metric học tập chỉ tính sinh viên có enrollment trong các kỳ đã cấu hình và
được sinh. K13–K22 chưa có lịch sử lớp/enrollment nên không bị tính là bỏ học
hoặc đưa vào mẫu số. HK261 đang diễn ra; điểm chưa chấm không tham gia phân
phối điểm và tỷ lệ grade. Khi chưa có sinh viên tốt nghiệp trong dữ liệu quan
sát, các tỷ lệ tốt nghiệp/phân loại có mẫu số 0 và giá trị 0.

Nguồn dữ liệu hiện có 9.890 sinh viên, thuộc khóa 2013–2016 (mã bắt đầu
`13`–`16`). `tools/generate_student_cohorts.py` giữ nguyên tên và các trường
khác, phân bổ lại danh sách theo trọng số tăng dần từ 8% cho K13 tới 14,5% cho
K26 (chuẩn hóa tổng trọng số thành 100%), đồng thời cập nhật MSSV/email. Sĩ số
theo khóa được làm tròn để tổng vẫn là 9.890; K26 nhận khoảng 910 sinh viên.
Profile được sinh cho tất cả các khóa K13–K26. Lịch sử lớp/đăng ký chỉ được
sinh cho những khóa có lịch học được khai báo trong generator.

## Quy ước quan trọng

- `student_id` có dạng `YY` + 5 chữ số, ví dụ `2301234`; phần `YY` nhận biết khóa. Phần số cuối được tạo bằng dãy modulo với bước nguyên tố cùng nhau với 100.000, nên không trùng trong một khóa mà không cần quét danh sách hiện có.
- `course_code` là mã liên kết chính giữa danh mục môn, class, tiên quyết và enrollment.
- `credits` được dùng để giữ số tín chỉ đăng ký không vượt 22 trong một kỳ.
- `status` là `Pass` nếu grade khác F (điểm từ 4.0), ngược lại là `Fail`.
- Difficulty override theo môn chỉnh trong
  `config/generator_config.json`; sinh viên có tổng academic/personality strength
  cao sẽ bị difficulty làm giảm điểm ít hơn.
- `calibration_targets` trong config là mục tiêu để so sánh phân phối GPA, không
  phải nhãn hard-code hay tỷ lệ bị ép vào đầu ra.
- Đường dẫn trong tài liệu được viết từ thư mục gốc dự án.
