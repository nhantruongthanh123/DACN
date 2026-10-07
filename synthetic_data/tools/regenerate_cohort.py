import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT_DIR / "generated"
OBSERVED_SEMESTERS = [
    "HK131",
    "HK132",
    "HK141",
    "HK142",
    "HK151",
    "HK152",
    "HK161",
    "HK162",
]


def _write_bytes_atomically(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(contents)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _write_frame_atomically(frame, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            dir=path.parent,
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            frame.to_csv(temp_file, index=False)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _existing_frame(path, dtype):
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=dtype)


def _merge_generated_classes(existing, generated, semester):
    if generated.empty:
        return existing
    if "class_id" not in generated or "course_code" not in generated:
        raise ValueError(f"{semester} class output is missing required columns")
    if generated["class_id"].duplicated().any():
        raise ValueError(f"{semester} class output contains duplicate class IDs")
    if existing.empty:
        return generated
    if existing["class_id"].duplicated().any():
        raise ValueError(f"{semester} existing classes contain duplicate IDs")
    overlapping = existing.merge(
        generated[["class_id", "course_code"]],
        on="class_id",
        how="inner",
        suffixes=("_existing", "_generated"),
    )
    conflicts = overlapping[
        overlapping["course_code_existing"]
        != overlapping["course_code_generated"]
    ]
    if not conflicts.empty:
        raise ValueError(
            f"{semester} regenerated class IDs changed course assignment"
        )
    new_classes = generated[
        ~generated["class_id"].isin(existing["class_id"])
    ]
    return pd.concat([existing, new_classes], ignore_index=True)


def _merge_generated_enrollments(existing, generated, cohort):
    if "student_id" not in generated:
        raise ValueError("Generated enrollment output is missing student_id")
    cohort_ids = generated["student_id"].astype(str).str.startswith(cohort)
    if not cohort_ids.all():
        raise ValueError(
            "Cohort-filtered generator emitted enrollment rows for another cohort"
        )
    untouched = (
        existing.loc[
            ~existing["student_id"].astype(str).str.startswith(cohort)
        ].copy()
        if "student_id" in existing
        else existing
    )
    if "enrollment_id" in generated:
        existing_ids = (
            pd.to_numeric(untouched["enrollment_id"], errors="coerce")
            if "enrollment_id" in untouched
            else pd.Series(dtype=float)
        )
        first_id = int(existing_ids.max()) + 1 if existing_ids.notna().any() else 1
        generated = generated.copy()
        generated["enrollment_id"] = range(
            first_id, first_id + len(generated)
        )
    return pd.concat([untouched, generated], ignore_index=True, sort=False)


def _run_and_merge(script, target, cohort, merge):
    original_bytes = target.read_bytes() if target.exists() else None
    existing = _existing_frame(target, {"class_id": str, "student_id": str})
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["SYNTHETIC_DATA_COHORT_FILTER"] = cohort
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            check=False,
            env=environment,
        )
        if result.returncode:
            raise RuntimeError(
                f"Generator failed ({result.returncode}): {script.name}"
            )
        generated = _existing_frame(
            target, {"class_id": str, "student_id": str}
        )
        merged = merge(existing, generated)
        _write_frame_atomically(merged, target)
    except Exception:
        if original_bytes is None:
            if target.exists():
                target.unlink()
        else:
            _write_bytes_atomically(target, original_bytes)
        raise


def regenerate_cohort(cohort):
    if len(cohort) != 2 or not cohort.isdigit():
        raise ValueError("Cohort must be a two-digit year such as 13")
    if cohort != "13":
        raise ValueError("This semester-generator sequence currently supports K13 only")
    if not (ROOT_DIR / "generated" / "student_profile" / "student_profiles.csv").exists():
        raise FileNotFoundError("Generate student profiles before cohort data")

    for semester in OBSERVED_SEMESTERS:
        suffix = semester.lower()
        class_script = (
            ROOT_DIR / "generators" / "classes"
            / f"generate_class_{suffix}.py"
        )
        enrollment_script = (
            ROOT_DIR / "generators" / "enrollments"
            / f"generate_enrollment_{suffix}.py"
        )
        class_output = GENERATED_DIR / "classes" / f"class_{suffix}.csv"
        enrollment_output = (
            GENERATED_DIR / "enrollments" / f"enrollment_{suffix}.csv"
        )
        _run_and_merge(
            class_script,
            class_output,
            cohort,
            lambda existing, generated: _merge_generated_classes(
                existing, generated, semester
            ),
        )
        _run_and_merge(
            enrollment_script,
            enrollment_output,
            cohort,
            lambda existing, generated: _merge_generated_enrollments(
                existing, generated, cohort
            ),
        )

    metrics_script = ROOT_DIR / "tools" / "generate_academic_metrics.py"
    subprocess.run(
        [sys.executable, str(metrics_script), "--cohort", cohort],
        check=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Regenerate one cohort while preserving other cohorts."
    )
    parser.add_argument("--cohort", required=True, help="Two-digit cohort year")
    args = parser.parse_args()
    regenerate_cohort(args.cohort)
