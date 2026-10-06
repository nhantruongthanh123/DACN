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
2. Chạy `generate_student_cohorts.py` để phân bổ lại danh sách vào K13–K26.
   Script giữ nguyên tên và mọi trường khác ngoài MSSV, email và cohort.
3. Chỉnh `synthetic_data/config/generator_config.json` nếu cần; chạy
   `add_base_score.py` để tạo profile cùng điểm nền theo cấu hình.
4. Chạy `add_lecture_dep.py` để tạo dữ liệu giảng viên phục vụ phân lớp.
5. Chạy `update_course.py` nếu cần cập nhật cột `difficulty` trong danh mục
   môn học.
6. Chạy `run_all.py` để sinh lớp, đăng ký, tiến độ và metric cho toàn bộ học kỳ.
7. (Tuỳ chọn) Chạy `generate_student_progress.py` để xuất kế hoạch học tập
   chuẩn theo khóa.

## Các file

### `add_base_score.py`

Đọc `synthetic_data/data/people/student.csv`, tạo background,
personality, academic/subject ability và `base_score` theo
`synthetic_data/config/generator_config.json`, rồi ghi
`synthetic_data/generated/student_profile/student_profiles.csv`. Sinh viên
được chọn theo mã có tiền tố năm từ `13` trở lên; file
`synthetic_data/data/people/student_base_score.csv` cũ vẫn được dùng làm fallback
cho đến khi profile mới tồn tại. Seed theo mã sinh viên giúp profile tái tạo
được khi config và danh sách sinh viên không đổi.

```bash
python synthetic_data/tools/add_base_score.py
```

Chạy lại script sau khi thay đổi config sẽ tạo lại profile và có thể làm thay
đổi kết quả enrollment ở các lần sau.

### `add_lecture_dep.py`

Đọc `synthetic_data/data/people/lecture.csv`, gán bộ môn cho giảng viên và ghi
`synthetic_data/data/people/lecturer_for_class.csv`. Script dùng seed cố định nên phân bổ giữ
nguyên khi dữ liệu đầu vào không đổi.

```bash
python synthetic_data/tools/add_lecture_dep.py
```

### `update_course.py`

Đọc rồi ghi đè `synthetic_data/data/catalog/course.csv`, thêm/cập nhật cột `difficulty` theo
từ điển `course_difficulty` trong mã nguồn. Giá trị được chuẩn hóa theo
`difficulty.catalog_min`/`catalog_max` và làm giảm điểm. Để chỉnh độ khó từng
môn mà không sửa danh mục, đặt mã môn và mức 1–5 trong
`difficulty.course_overrides`; override được ưu tiên hơn `course.csv`.

```bash
python synthetic_data/tools/update_course.py
```

Hãy sao lưu hoặc commit `course.csv` trước khi chạy nếu cần giữ cấu hình cũ.

### `run_all.py`

Tạo profile trước, sau đó chạy lần lượt generator class và enrollment theo
từng học kỳ từ HK231 đến HK261, cuối cùng tổng hợp metric. Không tạo trước tất
cả class của các kỳ vì nhu cầu lớp ở kỳ sau phụ thuộc lịch sử enrollment ở kỳ
trước. Script dừng ngay khi một generator lỗi và dùng `sys.executable`, do đó
tự dùng đúng Python/môi trường ảo đã gọi script.

```bash
python synthetic_data/tools/run_all.py
```

Kết quả được ghi vào:

- `synthetic_data/generated/classes/class_hk*.csv`
- `synthetic_data/generated/enrollments/enrollment_hk*.csv`
- `synthetic_data/generated/student_profile/student_profiles.csv`
- `synthetic_data/generated/metrics/`

Lưu ý: chạy lệnh này sẽ ghi đè các file generated hiện có.

### `generate_academic_metrics.py`

Đọc profile cùng các enrollment/class thuộc `student_progress.observed_semesters`
trong config, rồi tạo các báo cáo:

- `student_progress.csv`: mỗi sinh viên–học kỳ, có đăng ký hay không, tín chỉ
  đăng ký/đậu và CTXH tích lũy.
- `student_metrics.csv`: profile, GPA/tín chỉ đã đậu, điều kiện đồ án/tốt
  nghiệp, phân loại bằng và nguyên nhân dropout.
- `university_metrics.csv`: tỷ lệ dropout, tiếng Anh/đồ án/tốt nghiệp, phân loại
  bằng, điểm trung bình và tỷ lệ letter grade.
- `score_distribution.csv`: phân phối điểm theo môn và toàn trường trên hệ 10
  và hệ 4.
- `letter_grade_distribution.csv`: số lượng/tỷ lệ A+, A, B+, B, C+, C, D+, D, F
  theo môn và toàn trường.

Metric chỉ bao gồm sinh viên có lịch sử enrollment trong các kỳ đã sinh.
Điểm `NA` ở kỳ đang diễn ra không tham gia phân phối điểm; kỳ không có enrollment
được giữ thành dòng tiến độ với 0 tín chỉ.

Có thể chạy riêng sau khi các file class/enrollment đã tồn tại:

```bash
python synthetic_data/tools/generate_academic_metrics.py
```

### `generate_student_progress.py`

Đọc `synthetic_data/data/catalog/course.csv` và xuất kế hoạch môn học đề xuất theo khóa vào
`synthetic_data/student_curriculum_plan.csv`. Đây là khung chương trình chuẩn, không phải
lịch sử điểm hoặc danh sách đăng ký thực tế của từng sinh viên.

```bash
python synthetic_data/tools/generate_student_progress.py
```

Nếu mã môn trong `CURRICULUM_PLAN` không tồn tại trong `course.csv`, script sẽ
dừng và báo mã môn bị thiếu.

### `generate_student_cohorts.py`

Phân bổ lại các dòng hiện có trong `student.csv` vào khóa K13–K26 theo trọng
số tăng dần 8%, 8,5%, ..., 14,5%, sau đó chuẩn hóa theo tổng để không thêm/bớt
sinh viên. Với 9.890 dòng, sĩ số tăng từ 502 (K13) đến 910 (K26). Script chỉ
đổi `student_id`, `email` và `cohort`; các cột khác được giữ nguyên.

MSSV được tạo bằng dãy `(start + index * step) % 100000`, với `step` được chọn
để nguyên tố cùng nhau với 100.000. Dãy có chu kỳ đầy đủ nên các MSSV duy nhất
trong mỗi khóa, không cần kiểm tra va chạm trên toàn danh sách.

```bash
python synthetic_data/tools/generate_student_cohorts.py
```

Lệnh cập nhật trực tiếp `student.csv`; chạy lại sẽ tái tạo cùng kết quả do seed
cố định. Sau đó chạy `run_all.py` để cập nhật profile và dữ liệu class/
enrollment. Các học kỳ hiện chỉ có lịch học cho K23–K26.

## Kiểm tra nhanh đầu vào

Trước khi chạy `run_all.py`, tối thiểu cần có các file sau:

- `synthetic_data/data/people/student.csv`
- `synthetic_data/data/people/lecturer_for_class.csv`
- `synthetic_data/data/catalog/course.csv`
- `synthetic_data/data/catalog/assessment.csv`
- `synthetic_data/data/catalog/course_prerequisite.csv`
- `synthetic_data/config/generator_config.json`
