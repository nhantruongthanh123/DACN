# Generator tạo lớp và điểm theo học kỳ

Mỗi học kỳ có một cặp script:

1. `generate_class_hk*.py` mở lớp theo nhu cầu đăng ký.
2. `generate_enrollment_hk*.py` xếp sinh viên vào lớp và sinh điểm.

Chạy toàn bộ theo đúng thứ tự bằng:

```bash
source .venv/bin/activate
python synthetic_data/tools/run_all.py
```

Không chạy enrollment trước class của cùng kỳ. Các kỳ sau đọc lịch sử của kỳ
trước, nên chạy sai thứ tự có thể làm sai danh sách môn được đăng ký.

## Dữ liệu và kết quả

Các đường dẫn sau tính từ thư mục gốc dự án:

| Nhóm | Đường dẫn | Vai trò |
| --- | --- | --- |
| Sinh viên nguồn | `synthetic_data/data/people/student.csv` | Danh sách sinh viên, phân bổ vào khóa K13–K26. |
| Profile | `synthetic_data/generated/student_profile/student_profiles.csv` | Background, personality, năng lực học tập, tiếng Anh boolean, ngày CTXH tích lũy theo kỳ và `base_score`. |
| Giảng viên | `synthetic_data/data/people/lecturer_for_class.csv` | Giảng viên và bộ môn để phân công lớp. |
| Danh mục | `synthetic_data/data/catalog/` | Môn học, tín chỉ, độ khó, cấu trúc điểm, tiên quyết và chương trình. |
| Cấu hình | `synthetic_data/config/generator_config.json` | Phân phối profile, noise, grade/difficulty theo môn và điều kiện tốt nghiệp/dropout. |
| Lớp sinh ra | `synthetic_data/generated/classes/class_hk*.csv` | Đầu vào trực tiếp của generator enrollment. |
| Điểm sinh ra | `synthetic_data/generated/enrollments/enrollment_hk*.csv` | Lịch sử để xét các kỳ tiếp theo. |

Quy tắc chọn môn, học lại, tiên quyết và tín chỉ được trình bày ở
[`../rules/README.MD`](../rules/README.MD).

## Cách tạo lớp

Từ HK232 trở đi, generator class thực hiện các bước sau:

1. Đọc sinh viên, giảng viên và lịch sử enrollment/class các kỳ trước.
2. Gọi `calculate_eligibility_for_schedule()` để lấy các môn mỗi sinh viên có
   thể học: học lại trước, sau đó môn theo chương trình, môn tự chọn và môn bổ
   sung; chỉ chọn môn thỏa tiên quyết và không vượt 22 tín chỉ.
3. Đếm số sinh viên đăng ký mỗi môn để tính nhu cầu (`demand`).
4. Mở số lớp tối thiểu cần thiết, chia sĩ số gần đều và không lớp nào vượt quá
   120 sinh viên. Khi nhu cầu từ 40 trở lên, cách chia này tránh các lớp dưới
   40 sinh viên nếu có thể; dưới 40 thì giữ một lớp.
5. Phân loại môn thành `Triet`, `DaiCuong` hoặc `ChuyenNganh`, rồi gán luân
   phiên giảng viên cùng bộ môn.

File class gồm: `class_id`, `course_code`, `course_name`, `semester`,
`class_group`, `lecturer_id`, `lecturer_name`.

HK231 là kỳ khởi tạo: lớp được tạo từ chương trình HK1 của K23, chưa cần đọc
lịch sử kết quả.

## Cách tạo enrollment và điểm

Generator enrollment lấy danh sách sinh viên đủ điều kiện, trộn có seed rồi
chia gần đều vào các lớp cùng môn. Từ HK232, seed được tạo từ SHA-256 của học
kỳ/môn/mã sinh viên nên cùng đầu vào sẽ cho phân lớp và điểm ổn định.

`assessment.csv` quyết định cột điểm thành phần và trọng số. Với mỗi thành
phần, điểm được mô phỏng theo công thức cấu hình dùng chung:

```text
clip(academic ability + personality effect + subject effect
     - student-adjusted course difficulty + noise, 0, 10)
```

-   Profile lấy từ `generated/student_profile/student_profiles.csv`;
  `add_base_score.py` sinh profile từ sinh viên nguồn theo config và seed ổn định
  theo mã sinh viên. Các công cụ phân tích sẽ ưu tiên profile mới và vẫn có thể
  dùng file cũ `data/people/student_base_score.csv` khi profile mới chưa được tạo.
- Difficulty mặc định lấy từ `course.csv`; một course override trong config dùng
  thang 1–5. Difficulty càng cao càng trừ điểm, nhưng profile academic/personality
  mạnh sẽ làm mức trừ nhỏ hơn.
- Noise gồm Normal thông thường và high-deviation theo tỷ lệ, sigma và hướng
  được cấu hình. Điểm luôn được giới hạn trong [0, 10].
- `final_score` là tổng có trọng số. Grade được quy đổi theo `grade_scale`;
  F (<4.0) là `Fail`, từ D/4.0 trở lên là `Pass`.
- Enrollment đã chấm điểm có `course_id`, `semester`, `retaken`,
  `letter_grade`, `gpa_4`, `passed`, `semester_gpa_4` và `final_gpa_4`;
  `status` vẫn có để tương thích lịch sử. GPA học kỳ tính theo tín chỉ đăng ký;
  GPA tích lũy chỉ tính môn đã qua và mỗi course_code một lần.

Nếu không có cấu hình assessment cho một môn, các kỳ HK231–HK252 mặc định dùng
`cuoi_ky` với trọng số 100%.

File enrollment thường gồm `enrollment_id`, `student_id`, `class_id`, các cột
điểm thành phần động, `final_score` và `status`.

Enrollment chỉ được tạo khi sinh viên đủ điều kiện theo chương trình/tiên
quyết và có lớp đúng môn. Mỗi roster được chia cân bằng, không vượt quá 120;
nếu thiếu lớp hoặc dữ liệu lớp không thể chứa hết sinh viên đủ điều kiện,
generator dừng với lỗi thay vì âm thầm bỏ sinh viên hay tạo lớp quá tải.

## Điều kiện đồ án, CTXH và tốt nghiệp

`add_base_score.py` bổ sung `english_pass` (boolean) dựa trên background,
`english_level`, academic level và personality theo trọng số cấu hình. Profile
có `ctxh_days_by_semester` là JSON array; mỗi phần tử gồm mã học kỳ và tổng ngày
CTXH cộng dồn. Sinh viên có personality engagement thấp thường tích lũy ít
ngày hơn.

Các mã trong `student_progress.graduation.thesis_course_codes` chỉ được đăng ký
nếu trước đầu học kỳ người học đạt `english_pass=true` và đủ
`ctxh.minimum_for_thesis` ngày CTXH (mặc định 12). Để tốt nghiệp, metric kiểm tra
ít nhất 15 ngày CTXH, tiếng Anh, toàn bộ môn `required` trong curriculum và môn
đồ án tốt nghiệp cấu hình (`CO4337`). Chuẩn tốt nghiệp là 8 học kỳ; buộc thôi
học nếu đạt quá 12 học kỳ hoặc có hai học kỳ liên tiếp dưới 10 tín chỉ đã đậu.

Dropout tự nguyện được bốc với xác suất 30% trong nhóm background thấp hoặc
academic level thấp; nguyên nhân được gán theo trọng số 95% background/5%
academic. Generator cho phép sinh viên hoàn tất học kỳ dropout nhưng không xếp
môn sau học kỳ đó.

`run_all.py` gọi `generate_academic_metrics.py` ở cuối. Các file metric nằm
trong `synthetic_data/generated/metrics/`; metric chỉ bao phủ sinh viên có
enrollment trong các học kỳ đã sinh. K13–K22 chưa có lịch sử và HK261 chưa có
điểm cuối kỳ, nên lần lượt không bị suy đoán trạng thái dropout và không tham
gia phân phối điểm.

## Các học kỳ

| Kỳ | Class | Enrollment/điểm | Điểm khác biệt |
| --- | --- | --- | --- |
| HK231 | `generate_class_hk231.py` | `generate_enrollment_hk231.py` | K23 học HK1. Sinh viên được miễn LA1003 không được xếp vào môn này. |
| HK232 | `generate_class_hk232.py` | `generate_enrollment_hk232.py` | Dùng lịch sử HK231; K23 học HK2, bắt đầu có học lại và môn bổ sung. |
| HK241 | `generate_class_hk241.py` | `generate_enrollment_hk241.py` | K23 học HK3, K24 học HK1; xét lịch sử HK231–HK232. |
| HK242 | `generate_class_hk242.py` | `generate_enrollment_hk242.py` | K23 HK4, K24 HK2; có tự chọn quản lý và tự chọn tự do. |
| HK251 | `generate_class_hk251.py` | `generate_enrollment_hk251.py` | K23 HK5, K24 HK3, K25 HK1; hỗ trợ nhóm quản lý, tự do và nhóm C. |
| HK252 | `generate_class_hk252.py` | `generate_enrollment_hk252.py` | K23 chọn một môn dự án liên ngành và phải tích lũy 3 tín chỉ quản lý. |
| HK261 | `generate_class_hk261.py` | `generate_enrollment_hk261.py` | K23 HK7, K24 HK5, K25 HK3, K26 HK1; xét yêu cầu FREE 3 và GROUP_C 6 tín chỉ cho K23. |

### HK252: lựa chọn môn dự án

Với K23, rule chọn một môn khả dụng trong `CO3107`, `CO3109`, `CO3111` dựa vào
mã băm của sinh viên. Do đó không phải mọi sinh viên đều học cùng một môn dự
án.

### HK261: chưa có điểm cuối kỳ

HK261 vẫn tạo đăng ký và một số điểm thành phần, nhưng cố ý để `final_score`
và `status` là `NA`; cột `cuoi_ky` cũng không được sinh. Điều này thể hiện học
kỳ đang diễn ra. Không nên dùng HK261 làm lịch sử đậu/rớt cho kỳ sau cho tới khi
bổ sung điểm cuối kỳ.

Danh sách sinh viên được phân bổ từ K13 đến K26; profile bao gồm toàn bộ các
khóa. Các generator học vụ hiện chỉ có lịch cho K23–K26, nên K13–K22 không có
class/enrollment lịch sử được tạo. MSSV theo dạng `YY` + 5 chữ số; các chữ số
cuối dùng dãy modulo bảo đảm duy nhất trong từng khóa.

## Chạy một học kỳ riêng lẻ

Ví dụ tạo lại HK242:

```bash
python synthetic_data/generators/generate_class_hk242.py
python synthetic_data/generators/generate_enrollment_hk242.py
```

Hai lệnh ghi đè `class_hk242.csv` và `enrollment_hk242.csv` trong
`synthetic_data/generated/`. Nếu thay đổi dữ liệu đầu vào, tiên quyết,
assessment hoặc rule, nên chạy lại `tools/run_all.py` để các kỳ sau sử dụng
lịch sử đồng nhất.
