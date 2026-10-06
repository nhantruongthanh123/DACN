import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

# Danh sách các file cần chạy theo đúng thứ tự
scripts = [
    "../tools/add_base_score.py",
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
    "generate_enrollment_hk261.py",
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