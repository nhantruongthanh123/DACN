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
| Sinh viên | `synthetic_data/data/people/student_base_score.csv` | Năng lực nền (`base_score`) cho từng sinh viên. |
| Giảng viên | `synthetic_data/data/people/lecturer_for_class.csv` | Giảng viên và bộ môn để phân công lớp. |
| Danh mục | `synthetic_data/data/catalog/` | Môn học, tín chỉ, độ khó, cấu trúc điểm, tiên quyết và chương trình. |
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
4. Mở lớp 40 sinh viên cho môn bắt đầu bằng `LA` hoặc `PH`; các môn khác tối đa
   120 sinh viên/lớp.
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
phần, điểm được mô phỏng theo công thức:

```text
clip(base_score + difficulty + lệch độ khó + cộng học lại + nhiễu, 0, 10)
```

- `difficulty` lấy từ `course.csv`; generator cộng thêm độ lệch 0–0.3.
- Sinh viên học lại nhận điểm cộng 1.0–1.8.
- Nhiễu có phân phối chuẩn với độ lệch chuẩn 1.2.
- `final_score` là tổng có trọng số; `Pass` khi điểm từ 5 trở lên, ngược lại là
  `Fail`.

Nếu không có cấu hình assessment cho một môn, các kỳ HK231–HK252 mặc định dùng
`cuoi_ky` với trọng số 100%.

File enrollment thường gồm `enrollment_id`, `student_id`, `class_id`, các cột
điểm thành phần động, `final_score` và `status`.

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
