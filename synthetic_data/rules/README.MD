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
| Sinh điểm | `curriculum_rules.py` gián tiếp | Generator dùng `course_catalog().difficulty` cùng `base_score`, nhiễu ngẫu nhiên và điểm cộng học lại để sinh điểm thành phần/final score. |

Khi thay đổi CSV danh mục hoặc logic trong hai module này, hãy chạy lại
`python synthetic_data/tools/run_all.py` để tái tạo dữ liệu class và enrollment
nhất quán.
