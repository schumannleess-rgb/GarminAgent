"""
报表 CLI 入口

用法:
    python run_report.py morning [--mock]
    python run_report.py daily [--activity-id ID] [--mock]
    python run_report.py weekly [--weeks-ago N] [--mock]
    python run_report.py monthly [--months-ago N] [--mock]
    python run_report.py race [--activity-id ID] [--mock]
    python run_report.py all [--mock]
"""

import sys
import argparse
from pathlib import Path

# 确保 report 包路径正确
sys.path.insert(0, str(Path(__file__).resolve().parent))


def cmd_morning(args):
    from morning_report import MorningReport
    mr = MorningReport(mock=args.mock)
    path = mr.generate()
    print(f"[OK] Morning Report: {path}")
    return path


def cmd_daily(args):
    from daily_report import DailyReport
    dr = DailyReport(mock=args.mock)
    path = dr.generate(activity_id=args.activity_id)
    print(f"[OK] Daily Report: {path}")
    return path


def cmd_weekly(args):
    from weekly_report_v2 import WeeklyReportV2
    wr = WeeklyReportV2(mock=args.mock)
    path = wr.generate(weeks_ago=args.weeks_ago)
    print(f"[OK] Weekly Report: {path}")
    return path


def cmd_monthly(args):
    from monthly_report import MonthlyReport
    mr = MonthlyReport(mock=args.mock)
    path = mr.generate(months_ago=args.months_ago)
    print(f"[OK] Monthly Report: {path}")
    return path


def cmd_race(args):
    from race_report import RaceReport
    rr = RaceReport(mock=args.mock)
    path = rr.generate(activity_id=args.activity_id)
    print(f"[OK] Race Report: {path}")
    return path


def cmd_all(args):
    """生成所有 5 种报表"""
    results = []

    print("=== Generating All Reports ===")
    print()

    # Morning Report
    try:
        from morning_report import MorningReport
        mr = MorningReport(mock=args.mock)
        path = mr.generate()
        results.append(("Morning Report", path))
        print(f"  [OK] Morning Report: {path}")
    except Exception as e:
        print(f"  [FAIL] Morning Report: {e}")

    # Daily Report
    try:
        from daily_report import DailyReport
        dr = DailyReport(mock=args.mock)
        path = dr.generate()
        results.append(("Daily Report", path))
        print(f"  [OK] Daily Report: {path}")
    except Exception as e:
        print(f"  [FAIL] Daily Report: {e}")

    # Weekly Report
    try:
        from weekly_report_v2 import WeeklyReportV2
        wr = WeeklyReportV2(mock=args.mock)
        path = wr.generate()
        results.append(("Weekly Report", path))
        print(f"  [OK] Weekly Report: {path}")
    except Exception as e:
        print(f"  [FAIL] Weekly Report: {e}")

    # Monthly Report
    try:
        from monthly_report import MonthlyReport
        mr = MonthlyReport(mock=args.mock)
        path = mr.generate()
        results.append(("Monthly Report", path))
        print(f"  [OK] Monthly Report: {path}")
    except Exception as e:
        print(f"  [FAIL] Monthly Report: {e}")

    # Race Report
    try:
        from race_report import RaceReport
        rr = RaceReport(mock=args.mock)
        path = rr.generate()
        results.append(("Race Report", path))
        print(f"  [OK] Race Report: {path}")
    except Exception as e:
        print(f"  [FAIL] Race Report: {e}")

    print()
    print(f"Generated {len(results)} reports")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Garmin Training Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_report.py morning               # Morning Report (mock)
  python run_report.py daily                  # Daily Report (mock)
  python run_report.py weekly                 # Weekly Report (mock)
  python run_report.py monthly                # Monthly Report (mock)
  python run_report.py race                   # Race Report (mock)
  python run_report.py all                    # Generate all 5 reports
  python run_report.py daily --no-mock        # Use real Garmin data
        """,
    )
    parser.add_argument(
        "--no-mock", dest="mock", action="store_false",
        default=True, help="Use real Garmin data (default: mock)"
    )

    sub = parser.add_subparsers(dest="command", help="Report type")

    # morning
    sub.add_parser("morning", help="Generate Morning Report")

    # daily
    p_daily = sub.add_parser("daily", help="Generate Daily Report")
    p_daily.add_argument("--activity-id", type=int, default=None, help="Activity ID (default: latest)")

    # weekly
    p_weekly = sub.add_parser("weekly", help="Generate Weekly Report")
    p_weekly.add_argument("--weeks-ago", type=int, default=0, help="Weeks ago (0=this week)")

    # monthly
    p_monthly = sub.add_parser("monthly", help="Generate Monthly Report")
    p_monthly.add_argument("--months-ago", type=int, default=0, help="Months ago (0=this month)")

    # race
    p_race = sub.add_parser("race", help="Generate Race Report")
    p_race.add_argument("--activity-id", type=int, default=None, help="Activity ID (default: latest)")

    # all
    sub.add_parser("all", help="Generate all 5 reports")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "morning": cmd_morning,
        "daily": cmd_daily,
        "weekly": cmd_weekly,
        "monthly": cmd_monthly,
        "race": cmd_race,
        "all": cmd_all,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
