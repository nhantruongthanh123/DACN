# Quy tắc chương trình và học vụ

Thư mục `rules` chứa hai module dùng chung cho các generator trong
`synthetic_data/generators/`. Chúng không trực tiếp tạo CSV lớp học hoặc điểm;
chúng cung cấp quy tắc để generator quyết định **môn nào được mở/đăng ký** và
**điểm được mô phỏng theo độ khó nào**.

```text
catalog CSV ──> curriculum_rules.py ──> generator class/enrollment
history CSV ──> academic_rules.py   ──> generator class/enrollment
                                              │
                                              └──> generated/classes,
                                                   generated/enrollments
```

## `curriculum_rules.py` — quy tắc chương trình đào tạo

Module này đọc dữ liệu từ `synthetic_data/data/catalog/` và trả về danh sách
môn học, nhóm tự chọn, số tín chỉ và độ khó. Nó là nguồn quy tắc chung để các
generator class và enrollment dùng cùng một chương trình đào tạo.

### Dữ liệu đầu vào

| File | Vai trò |
| --- | --- |
| `curriculum_computer_science.csv` | Môn bắt buộc theo học kỳ và thứ tự ưu tiên. |
| `additional_course_rules.csv` | Môn có thể học bổ sung và điều kiện áp dụng. |
| `elective_courses.csv` | Danh sách tự chọn tự do (`FREE`). |
| `management_electives.csv` | Danh sách tự chọn quản lý (`MANAGEMENT`). |
| `group_c_electives.csv` | Danh sách môn nhóm C (`GROUP_C`). |
| `course.csv` | Tên môn, số tín chỉ và `difficulty`. |

### Hàm quan trọng

- `curriculum_courses(semester)`: trả các môn bắt buộc của một học kỳ, theo
  `course_order`.
- `additional_courses(semester)`: trả môn có thể học thêm tại học kỳ đó; mặc
  định không lấy rule chỉ dành cho lộ trình tốt nghiệp sớm.
- `free_elective_courses()`, `management_elective_courses()` và
  `group_c_elective_courses()`: trả các lựa chọn môn tự chọn tương ứng.
- `course_catalog()`: tạo ba ánh xạ `course_code → course_name`, `credits` và
  `difficulty`. Generator enrollment sử dụng `difficulty` để điều chỉnh điểm
  mô phỏng: độ khó cao hơn làm điểm thành phần có xu hướng thấp hơn.
- `get_department(course_code)`: phân môn về `Triet`, `DaiCuong` hoặc
  `ChuyenNganh`; generator class dùng kết quả này để chọn giảng viên phù hợp.

### Hằng số chính

- `MAX_CREDITS = 22`: trần tín chỉ mỗi sinh viên trong một học kỳ.
- `TUITION_BASELINE_CREDITS = 18`: mốc tín chỉ generator cố gắng bổ sung cho
  sinh viên đủ điều kiện.

## `academic_rules.py` — quy tắc học vụ và điều kiện đăng ký

Module này ghép lịch sử enrollment với lớp đã tạo để biết môn học, đọc kết quả
`Pass`/`Fail`, rồi chọn danh sách môn một sinh viên có thể đăng ký trong học kỳ
tiếp theo. Các generator class và enrollment gọi cùng hàm này để danh sách lớp
mở và dữ liệu đăng ký không mâu thuẫn.

Module cũng cung cấp rule dùng chung để tạo hồ sơ sinh viên, tính điểm môn,
noise, grade và GPA. Tham số được đọc từ
`synthetic_data/config/generator_config.json`; generator lớp/đăng ký dùng chung
một cấu hình để điều chỉnh nhất quán giữa các học kỳ.

### Cấu hình hồ sơ và điểm

- Phân phối `family_income`, `financial_pressure`, `living_condition`,
  personality và academic level có thể chỉnh trong JSON. Các phân phối phải
  không âm và tổng bằng `1.0`.
- `academic.base_scores` ánh xạ academic level 1–5 sang điểm nền; `math_level`
  và `english_level` được sinh từ `academic_level` cộng nhiễu Normal rồi giới
  hạn trong khoảng 1–5.
- `personality_weights` là trọng số cho discipline, motivation, stress và
  social activity sau khi chuẩn hóa trait về `[-1, 1]`. Mặc định social activity
  không ảnh hưởng trực tiếp tới điểm.
- `difficulty.course_overrides` cho phép đặt difficulty từng `course_code` theo
  thang 1–5. Môn không có override dùng cột `difficulty` trong `course.csv`,
  chuẩn hóa theo `catalog_min`/`catalog_max`. Difficulty trừ điểm; mức trừ giảm
  khi academic/personality strength cao (academic level, discipline, motivation
  cao hoặc stress thấp).
- Ví dụ: đặt `"CO1005": 4` trong `course_overrides` để gán môn CO1005 mức 4
  (mức 5 là khó nhất). Để giữ mức danh mục, không thêm môn vào map override.
- `calibration_targets` chỉ là khoảng để đánh giá kết quả GPA sau khi sinh,
  không ép sinh viên vào nhóm GPA.
- `noise` điều chỉnh tỷ lệ Normal/high-deviation, sigma và hướng lệch. `seed`
  giúp hồ sơ sinh viên có thể tái tạo giữa các lần chạy.
- `grade_scale` dùng khoảng lower-inclusive, upper-exclusive; riêng mốc tối đa
  được tính vào grade cuối. F dưới 4.0 là trượt; từ 4.0 trở lên là qua môn.
  `retake_bonus` mặc định bằng 0.

Chạy `python synthetic_data/tools/add_base_score.py` để tạo lại
`student_base_score.csv` cùng các trường hồ sơ. Khi thay đổi rule hoặc config,
chạy `python synthetic_data/tools/run_all.py` để sinh lại các học kỳ nhất quán.

### Điều kiện tiến độ, đồ án và dropout

`student_progress` cấu hình các kỳ được theo dõi, kỳ bắt đầu theo khóa, ngưỡng
CTXH, xác suất đạt tiếng Anh và chính sách dropout/tốt nghiệp. Profile xuất ra
`english_pass` dạng boolean và `ctxh_days_by_semester` dạng JSON array với ngày
CTXH cộng dồn. Ngày tăng theo từng kỳ với kỳ vọng phụ thuộc discipline,
motivation, social activity và stress.

Các môn đồ án trong `thesis_course_codes` bị loại khỏi eligibility nếu tiếng
Anh chưa đạt hoặc CTXH tích lũy trước kỳ học chưa đủ 12 ngày. Tốt nghiệp yêu cầu
15 ngày CTXH, tiếng Anh, các môn `required` trong curriculum và mã đồ án tốt
nghiệp cấu hình. Nếu đến kỳ có môn đồ án nhưng chưa đủ điều kiện, profile có
xác suất cấu hình được (mặc định 80%) không đăng ký môn nào trong kỳ đó, mô
phỏng việc phải chờ và tốt nghiệp trễ. Tốt nghiệp chuẩn sau 8 học kỳ; buộc thôi
học khi đã qua 12 học kỳ hoặc có hai kỳ liên tiếp dưới 10 tín chỉ pass. Dropout
tự nguyện dùng xác suất 30% trong nhóm background/học lực thấp và trọng số
nguyên nhân background 95%, academic 5%.

`generate_academic_metrics.py` tạo tiến độ từng kỳ, metric từng sinh viên,
phân phối điểm theo course/toàn trường và tổng hợp dropout/tốt nghiệp. Mẫu số
chỉ gồm sinh viên có enrollment trong các kỳ đã sinh; điểm chưa chấm ở kỳ đang
diễn ra bị loại khỏi phân phối điểm.

### Lịch sử học tập

`load_history(semesters)` đọc các cặp file sau, sau đó ghép theo `class_id` để
bổ sung `course_code` cho mỗi đăng ký:

- `synthetic_data/generated/enrollments/enrollment_hk*.csv`
- `synthetic_data/generated/classes/class_hk*.csv`

Vì vậy, khi chạy theo thứ tự thời gian, học kỳ trước phải được sinh xong trước
học kỳ sau. `tools/run_all.py` đã thực hiện đúng thứ tự này.

### Hàm xét môn chính

`calculate_eligibility_for_schedule(...)` là hàm được các generator học kỳ
sau sử dụng nhiều nhất. Với từng sinh viên, hàm:

1. Tách môn đã đậu và môn trượt từ lịch sử điểm.
2. Đưa môn trượt cần học lại vào ưu tiên đầu tiên.
3. Bổ sung môn theo kế hoạch của khóa (`scheduled_courses`).
4. Chỉ chọn môn thỏa tiên quyết (`relation_type = "TQ"` trong
   `course_prerequisite.csv`) và không vượt 22 tín chỉ.
5. Hoàn thành yêu cầu tín chỉ tự chọn bắt buộc, nếu generator truyền các nhóm
   và mốc tín chỉ vào.
6. Có thể thêm môn quản lý, tự chọn tự do hoặc nhóm C để tiến gần mốc 18 tín
   chỉ, với lựa chọn xác định theo mã sinh viên.

Hàm trả về:

```python
eligibility, failed
```

- `eligibility`: `{student_id: [course_code, ...]}` — danh sách môn được phép
  đăng ký ở học kỳ đang sinh.
- `failed`: `{student_id: {course_code, ...}}` — các môn trượt, dùng để xác
  định học lại và điều chỉnh cách sinh điểm ở một số generator.

`calculate_eligibility(...)` là phiên bản cũ, chuyên cho bối cảnh HK241; các
generator mới nên ưu tiên `calculate_eligibility_for_schedule(...)`.

### Các ngoại lệ và tính lặp lại

- Sinh viên có thể được miễn `LA1003` theo `can_skip_la1003()` dựa trên điểm
  nền và một giá trị băm từ mã sinh viên.
- `wants_acceleration()` xác định sinh viên có xu hướng học nhanh khi
  `base_score` từ 8.0 trở lên.
- Các hàm chọn môn tự chọn sử dụng SHA-256 từ `student_id`; vì thế cùng dữ liệu
  đầu vào sẽ tạo lựa chọn ổn định qua các lần chạy, không thay đổi ngẫu nhiên.

## Liên hệ với tạo lớp và sinh điểm

| Giai đoạn | Rule được dùng | Kết quả |
| --- | --- | --- |
| Tạo class | Cả hai module | Chọn môn cần mở theo chương trình và sinh viên đủ điều kiện; phân bộ môn để gán giảng viên. |
| Tạo enrollment | Cả hai module | Chọn sinh viên/môn, kiểm tra học lại, tiên quyết và tín chỉ. |
| Sinh điểm | `academic_rules.py` và `generator_config.json` | Dùng profile academic/personality, subject ability, difficulty đã chuẩn hóa, noise cấu hình được, grade scale và trạng thái học lại. |

Enrollment mới bổ sung `course_id`, `semester`, `retaken`, `letter_grade`,
`gpa_4`, `passed`, `semester_gpa_4` và `final_gpa_4`; `status` vẫn được giữ để
các rule lịch sử tiếp tục hoạt động. GPA học kỳ được tính theo tín chỉ đăng ký;
GPA tích lũy chỉ tính môn đã qua, theo tín chỉ và không đếm lặp course_code.
HK261 đang diễn ra nên grade/GPA học kỳ để trống, GPA tích lũy vẫn phản ánh các
học kỳ đã hoàn tất.

Khi thay đổi CSV danh mục, file config hoặc logic trong hai module này, hãy chạy lại
`python synthetic_data/tools/run_all.py` để tái tạo dữ liệu class và enrollment
nhất quán.
