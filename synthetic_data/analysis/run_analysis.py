import argparse
import sys
from pathlib import Path

# Add current directory to path to import helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))

from analysis_helpers import (
    analyze_ctxh_distribution,
    get_available_semesters,
    get_sample_student_id,
    get_class_roster,
    summarize_cohort_results,
    summarize_required_courses,
    view_cohort_status,
    view_ctxh_distribution,
    view_fail_result,
    view_student_results,
)


def run_demo(student_id=None):
    """Run a comprehensive demonstration report."""
    target_id = student_id or get_sample_student_id()
    available_semesters = get_available_semesters()
    latest_sem = available_semesters[-1] if available_semesters else "HK162"

    print("\n" + "#" * 80)
    print(" BÁO CÁO PHÂN TÍCH HỌC VỤ MINH HỌA (DEMO ANALYSIS REPORT) ".center(80, "#"))
    print("#" * 80)
    print(f"Các học kỳ đã mô phỏng trong hệ thống: {', '.join(available_semesters)}")
    print(f"Mã sinh viên được chọn phân tích:       {target_id}")

    # 1. Bảng điểm chi tiết
    view_student_results(target_id, print_report=True)

    # 2. Môn còn thiếu & tự chọn
    try:
        summarize_required_courses(target_id, print_report=True)
    except Exception as e:
        print(f"[!] Không thể tổng kết môn còn thiếu cho {target_id}: {e}")

    # 3. Phân phối môn rớt ở kỳ mới nhất
    print(f"\n[DEMO] Thống kê tỷ lệ rớt môn học kỳ gần nhất ({latest_sem}):")
    view_fail_result(latest_sem, print_report=True)

    # 4. Phân phối CTXH theo khóa của sinh viên
    target_cohort = f"K{str(target_id)[:2]}" if str(target_id)[:2].isdigit() else "K13"
    print(f"\n[DEMO] Phân tích phân phối số ngày CTXH của khóa {target_cohort}:")
    view_ctxh_distribution(target_cohort, print_report=True)

    # 5. Tổng kết kết quả học vụ của khóa (tốt nghiệp, thôi học, tiếp tục học)
    print(f"\n[DEMO] Tổng kết kết quả học vụ của khóa {target_cohort}:")
    summarize_cohort_results(target_cohort, print_report=True)


def main():
    parser = argparse.ArgumentParser(
        description="Công cụ phân tích và tra cứu dữ liệu học vụ mô phỏng (Academic Data Analysis CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  python run_analysis.py --transcript 1309714
  python run_analysis.py --remaining 1309714
  python run_analysis.py --roster HK162 HK162_CO4337_L01
  python run_analysis.py --fails HK162
  python run_analysis.py --ctxh K13
  python run_analysis.py --summary K13
  python run_analysis.py --semesters
  python run_analysis.py --demo 1309714
  python run_analysis.py (chạy demo mặc định)
        """,
    )

    parser.add_argument(
        "-t",
        "--transcript",
        metavar="STUDENT_ID",
        help="In bảng điểm chi tiết theo từng học kỳ của sinh viên",
    )
    parser.add_argument(
        "-r",
        "--remaining",
        metavar="STUDENT_ID",
        help="Tổng kết môn bắt buộc cần học/học lại và tiến độ tín chỉ tự chọn",
    )
    parser.add_argument(
        "-c",
        "--roster",
        nargs=2,
        metavar=("SEMESTER", "CLASS_ID"),
        help="Tra cứu giảng viên và danh sách sinh viên của một lớp học phần (VD: HK162 HK162_CO4337_L01)",
    )
    parser.add_argument(
        "-f",
        "--fails",
        nargs="?",
        const="",
        metavar="SEMESTER",
        help="Xem thống kê phân phối số môn rớt của một học kỳ (mặc định: kỳ mới nhất)",
    )
    parser.add_argument(
        "-k",
        "--ctxh",
        dest="ctxh_cohort",
        metavar="COHORT",
        help="Xem phân phối số ngày CTXH của một khóa sinh viên (VD: K13, K14)",
    )
    parser.add_argument(
        "-u",
        "--summary",
        "--cohort-status",
        dest="summary_cohort",
        metavar="COHORT",
        help="Tổng kết kết quả học vụ của một khóa (tốt nghiệp, thôi học, tiếp tục học)",
    )
    parser.add_argument(
        "-s",
        "--semesters",
        action="store_true",
        help="Liệt kê danh sách tất cả các học kỳ có dữ liệu trong hệ thống",
    )
    parser.add_argument(
        "-d",
        "--demo",
        nargs="?",
        const="",
        metavar="STUDENT_ID",
        help="Chạy báo cáo minh họa tổng hợp (bảng điểm, môn còn thiếu, phân phối điểm rớt, CTXH, tổng kết khóa)",
    )

    args = parser.parse_args()

    # If no arguments provided, run demo with usage guide
    if len(sys.argv) == 1:
        print("[*] Không có tham số được chỉ định. Chạy báo cáo demo minh họa:")
        run_demo()
        print("[i] Gợi ý: Chạy 'python run_analysis.py --help' để xem các tùy chọn tra cứu khác.")
        return

    if args.semesters:
        semesters = get_available_semesters()
        print(f"\nDanh sách các học kỳ có dữ liệu ({len(semesters)} kỳ):")
        for sem in semesters:
            print(f" - {sem}")
        print()
        return

    if args.transcript:
        view_student_results(args.transcript)

    if args.remaining:
        try:
            summarize_required_courses(args.remaining)
        except Exception as e:
            print(f"[!] Lỗi: {e}")

    if args.roster:
        sem, class_id = args.roster
        get_class_roster(sem, class_id)

    if args.fails is not None:
        sem = args.fails if args.fails else None
        view_fail_result(sem)

    if args.ctxh_cohort:
        view_ctxh_distribution(args.ctxh_cohort)

    if args.summary_cohort:
        summarize_cohort_results(args.summary_cohort)

    if args.demo is not None:
        target = args.demo if args.demo else None
        run_demo(target)


if __name__ == "__main__":
    main()
