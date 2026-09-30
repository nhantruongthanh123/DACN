# Dữ liệu nguồn của `synthetic_data`

Thư mục `data` chứa dữ liệu đầu vào cho toàn bộ quy trình sinh lớp,
enrollment và điểm. Dữ liệu được chia thành ba nhóm:

```text
data/
├── academic/  # Mốc thời gian và học kỳ
├── catalog/   # Môn học, chương trình, tiên quyết, cấu trúc điểm
└── people/    # Sinh viên và giảng viên
```

Các generator chỉ tạo dữ liệu trong `synthetic_data/generated/`; các file ở
đây là dữ liệu nguồn. Khi chỉnh sửa dữ liệu nguồn, nên chạy lại
`python synthetic_data/tools/run_all.py` để tái tạo dữ liệu nhất quán.

## 1. `academic/` — thông tin học kỳ

### `semester.csv`

Danh mục các học kỳ trong hệ thống. File này dùng để chuẩn hóa mã học kỳ, năm
học và thứ tự kỳ; ví dụ `HK231` là kỳ 1 của niên khóa 2023–2024.

| Cột | Kiểu/ý nghĩa |
| --- | --- |
| `semester_id` | Khóa số duy nhất của học kỳ. |
| `semester_code` | Mã học kỳ, ví dụ `HK231`, `HK232`, `HK241`. Đây là mã được dùng trong tên file class/enrollment. |
| `academic_year` | Niên khóa hiển thị, ví dụ `2023-2024`. |
| `term` | Số thứ tự học kỳ trong niên khóa. |

Hiện generator sinh dữ liệu cho HK231, HK232, HK241, HK242, HK251, HK252 và
HK261. Những học kỳ khác trong file vẫn hữu ích cho mở rộng dữ liệu sau này.

## 2. `catalog/` — danh mục và quy tắc đào tạo

Các file tại đây được `curriculum_rules.py`, `academic_rules.py` và các
generator dùng để quyết định môn nào mở, sinh viên được đăng ký môn nào và
cách tính điểm.

### `course.csv`

Danh mục môn học chuẩn; là file trung tâm được các generator class/enrollment
tra cứu.

| Cột | Kiểu/ý nghĩa |
| --- | --- |
| `course_id` | Khóa số nội bộ của môn học. |
| `course_code` | Mã môn học duy nhất, ví dụ `CO1005`; là khóa liên kết chính trong các rule. |
| `course_name` | Tên môn học. |
| `credits` | Số tín chỉ; dùng để giới hạn số tín chỉ đăng ký và tính tổng tín chỉ. |
| `difficulty` | Hệ số điều chỉnh điểm mô phỏng. Generator cộng hệ số này vào `base_score`; giá trị cao hơn có xu hướng làm điểm cao hơn theo logic hiện tại. |

`tools/update_course.py` có thể thêm/cập nhật cột `difficulty`.

### `assessment.csv`

Khai báo cơ cấu điểm của từng môn. Generator enrollment tạo các cột điểm có
trọng số lớn hơn 0 và tính `final_score` từ các trọng số này.

| Cột | Kiểu/ý nghĩa |
| --- | --- |
| `course_id` | Mã môn dùng để ghép cơ cấu điểm; trong dữ liệu hiện tại có cùng giá trị với `course_code`. |
| `course_name` | Tên môn, phục vụ đọc/kiểm tra dữ liệu. |
| `credits` | Số tín chỉ tham chiếu của môn. |
| `course_category` | Nhóm môn học, dùng để mô tả/phân loại. |
| `quiz` | Tỷ trọng điểm quiz, theo phần trăm. |
| `lab` | Tỷ trọng điểm thực hành/thí nghiệm, theo phần trăm. |
| `btl` | Tỷ trọng bài tập lớn, theo phần trăm. |
| `giua_ky` | Tỷ trọng điểm giữa kỳ, theo phần trăm. |
| `cuoi_ky` | Tỷ trọng điểm cuối kỳ, theo phần trăm. |

Với một môn, tổng các cột tỷ trọng nên là 100. Nếu một thành phần bằng 0,
generator không tạo cột điểm thành phần đó cho môn này.

### `course_prerequisite.csv`

Mô tả quan hệ giữa môn học và môn liên quan, chủ yếu để kiểm tra điều kiện
trước khi đăng ký.

| Cột | Kiểu/ý nghĩa |
| --- | --- |
| `course_prerequisite_id` | Khóa số duy nhất của quan hệ. |
| `course_code` | Môn được xét điều kiện/quan hệ. |
| `related_course_code` | Môn liên quan đến `course_code`. |
| `relation_type` | Mã loại quan hệ. Dữ liệu có `TQ`, `HT`, `KN`, `SHT`. Logic hiện tại chỉ bắt buộc quan hệ `TQ`; các mã còn lại được lưu để tham chiếu hoặc mở rộng. |

Để được chọn một môn có rule `TQ`, sinh viên phải đã đậu toàn bộ
`related_course_code` tương ứng.

### `curriculum_computer_science.csv`

Khung chương trình chuẩn ngành Computer Science theo học kỳ. Generator dùng
file này để lấy các môn dự kiến của từng khóa.

| Cột | Kiểu/ý nghĩa |
| --- | --- |
| `program_year` | Năm áp dụng chương trình. |
| `major` | Ngành đào tạo. |
| `semester` | Học kỳ trong chương trình, ví dụ `HK1` đến `HK8`. |
| `course_order` | Thứ tự ưu tiên/hiển thị môn trong học kỳ. |
| `course_code` | Mã môn học. |
| `course_name` | Tên môn học. |
| `credits` | Số tín chỉ theo khung chương trình. |
| `course_type` | Loại môn: `required` hoặc `elective`. |
| `elective_group` | Nhóm tự chọn nếu có, ví dụ `FREE`, `GROUP_A`…`GROUP_D`. |
| `elective_requirement` | Ghi chú hoặc yêu cầu tích lũy của nhóm tự chọn. |

### `additional_course_rules.csv`

Quy tắc về các môn được phép học bổ sung/học sớm ngoài danh sách chuẩn của kỳ.
`academic_rules.py` dùng danh sách này khi sinh viên cần bổ sung tín chỉ hoặc
thuộc lộ trình học nhanh.

| Cột | Kiểu/ý nghĩa |
| --- | --- |
| `rule_id` | Mã duy nhất của rule. |
| `source_program` | Chương trình mà rule xuất phát. |
| `source_cohort` | Khóa nguồn của rule. |
| `applies_to_cohorts` | Các khóa được áp dụng, phân tách bằng `|`. |
| `available_from_semester` | Học kỳ sớm nhất được phép học môn bổ sung. |
| `course_code`, `course_name`, `credits` | Thông tin môn được bổ sung. |
| `activation_condition` | Điều kiện kích hoạt rule, ví dụ thiếu tín chỉ hoặc đủ điều kiện học nhanh. |
| `priority` | Thứ tự ưu tiên khi chọn môn. |
| `early_graduation_semester` | Mốc học kỳ dành cho rule tốt nghiệp sớm, nếu có. |
| `target_semester` | Học kỳ mục tiêu của rule, nếu có. |
| `prerequisite_policy` | Chính sách áp dụng tiên quyết, ví dụ `respect_TQ`. |
| `tuition_baseline_credits` | Mốc tín chỉ mục tiêu của rule. |
| `semester_credit_limit` | Trần tín chỉ áp dụng cho rule. |
| `notes` | Ghi chú nghiệp vụ. |

### `elective_courses.csv`

Danh sách tự chọn tự do (`FREE`). Các cột:
`course_code`, `course_name`, `credits`, `elective_group`,
`available_from_semester`, `priority`, `prerequisite_policy`, `department`.

`available_from_semester` xác định từ kỳ nào môn xuất hiện; `priority` quyết
định thứ tự xét; `department` hỗ trợ phân công giảng viên khi mở lớp.

### `management_electives.csv`

Danh sách tự chọn quản lý (`MANAGEMENT`). Cấu trúc giống
`elective_courses.csv`: mã/tên môn, tín chỉ, nhóm, kỳ được học, ưu tiên, chính
sách tiên quyết và bộ môn. Generator dùng nhóm này để đáp ứng yêu cầu tự chọn
quản lý của các khóa/kỳ có cấu hình.

### `group_c_electives.csv`

Danh sách tự chọn nhóm C (`GROUP_C`). Cấu trúc gồm:
`course_code`, `course_name`, `credits`, `elective_group`,
`available_from_semester`, `priority`, `prerequisite_policy`.

Ở HK261, rules có thể dùng nhóm này cùng với `FREE` để kiểm tra mốc tích lũy
tín chỉ tự chọn của K23.

## 3. `people/` — sinh viên và giảng viên

Các file trong nhóm này cung cấp thực thể gốc để mở lớp, xếp lớp và mô phỏng
điểm.

### `student.csv`

Hồ sơ gốc của sinh viên.

| Cột | Kiểu/ý nghĩa |
| --- | --- |
| `student_id` | Mã sinh viên duy nhất. Ba ký tự đầu, như `231`/`241`, xác định khóa trong các rule. |
| `name` | Họ và tên sinh viên. |
| `email` | Email liên hệ. |
| `role` | Vai trò bản ghi, hiện là `student`. |
| `title` | Bậc/chương trình học, ví dụ `undergraduate`. |
| `cohort` | Khóa học, ví dụ `K23`, `K24`. |
| `major` | Ngành học. |

### `student_base_score.csv`

Phiên bản rút gọn dùng trực tiếp khi mô phỏng kết quả học tập. File được tạo
bởi `tools/add_base_score.py` từ `student.csv`.

| Cột | Kiểu/ý nghĩa |
| --- | --- |
| `student_id` | Mã sinh viên, dùng để liên kết với enrollment và lịch sử. |
| `name` | Tên sinh viên, phục vụ nhận diện. |
| `base_score` | Điểm năng lực nền trên thang 10; là thành phần chính của công thức sinh điểm. |

Chạy lại `add_base_score.py` sẽ tạo lại giá trị ngẫu nhiên và làm thay đổi
điểm mô phỏng của các kỳ chạy sau.

### `lecture.csv`

Hồ sơ gốc của giảng viên.

| Cột | Kiểu/ý nghĩa |
| --- | --- |
| `lecture_id` | Mã giảng viên duy nhất. |
| `name` | Họ tên giảng viên. |
| `email` | Email liên hệ. |
| `role` | Vai trò bản ghi, hiện là `lecturer`. |
| `title` | Học hàm/học vị, ví dụ `master`, `professor`. |

### `lecturer_for_class.csv`

Danh sách giảng viên đã được gán bộ môn để generator class phân công giảng
viên. File được tạo bởi `tools/add_lecture_dep.py` từ `lecture.csv`.

| Cột | Kiểu/ý nghĩa |
| --- | --- |
| `lecturer_id` | Mã giảng viên, lấy từ `lecture_id`. |
| `lecturer_name` | Tên giảng viên. |
| `departments` | Bộ môn: `Triet`, `DaiCuong` hoặc `ChuyenNganh`. |

Generator chọn giảng viên có `departments` phù hợp với bộ môn suy ra từ mã môn
học và phân công luân phiên giữa các giảng viên phù hợp.
