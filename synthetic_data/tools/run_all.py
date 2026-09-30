import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

# Danh sách các file cần chạy theo đúng thứ tự
scripts = [
    "generate_class_hk231.py",
    "generate_enrollment_hk231.py",
    "generate_class_hk232.py",
    "generate_enrollment_hk232.py",
    "generate_class_hk241.py",
    "generate_enrollment_hk241.py",
    "generate_class_hk242.py",
    "generate_enrollment_hk242.py",
    "generate_class_hk251.py",
    "generate_enrollment_hk251.py",
    "generate_class_hk252.py",
    "generate_enrollment_hk252.py",
    "generate_class_hk261.py",
    "generate_enrollment_hk261.py"

]

for script in scripts:
    print(f"⏳ Đang chạy {script}...")
    
    # Lệnh chạy file. Thay "python" bằng "python3" nếu bạn dùng macOS/Linux
    result = subprocess.run([sys.executable, str(ROOT_DIR / "generators" / script)])
    
    # Kiểm tra xem file có chạy thành công không (returncode == 0 là thành công)
    if result.returncode != 0:
        print(f"❌ Có lỗi xảy ra ở file {script}. Dừng tiến trình!")
        break
        
    print(f"✅ Đã chạy xong {script}\n")

print("🎉 Hoàn tất toàn bộ!")