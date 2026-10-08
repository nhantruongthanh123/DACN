import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

# Danh sách các file cần chạy theo đúng thứ tự
scripts = [
    "../tools/add_base_score.py",
    "classes/generate_class_hk131.py",
    "enrollments/generate_enrollment_hk131.py",
    "classes/generate_class_hk132.py",
    "enrollments/generate_enrollment_hk132.py",
    "classes/generate_class_hk141.py",
    "enrollments/generate_enrollment_hk141.py",
    "classes/generate_class_hk142.py",
    "enrollments/generate_enrollment_hk142.py",
    "classes/generate_class_hk151.py",
    "enrollments/generate_enrollment_hk151.py",
    "classes/generate_class_hk152.py",
    "enrollments/generate_enrollment_hk152.py",
    "classes/generate_class_hk161.py",
    "enrollments/generate_enrollment_hk161.py",
    "classes/generate_class_hk162.py",
    "enrollments/generate_enrollment_hk162.py",
    "classes/generate_class_hk171.py",
    "enrollments/generate_enrollment_hk171.py",
    "classes/generate_class_hk172.py",
    "enrollments/generate_enrollment_hk172.py",
    "classes/generate_class_hk181.py",
    "enrollments/generate_enrollment_hk181.py",
    "classes/generate_class_hk182.py",
    "enrollments/generate_enrollment_hk182.py",
    "../tools/generate_academic_metrics.py",
]

for script in scripts:
    print(f"Running {script}...")
    script_path = (ROOT_DIR / "generators" / script).resolve()
    child_environment = os.environ.copy()
    child_environment["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(script_path)],
        check=False,
        env=child_environment,
    )
    if result.returncode != 0:
        print(f"Failed: {script}. Stopping the pipeline.")
        raise SystemExit(result.returncode)

    print(f"Finished {script}\n")

print("All generators completed.")