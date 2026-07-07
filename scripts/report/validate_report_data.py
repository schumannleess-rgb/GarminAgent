"""
报表数据校验脚本

从 Garmin API 获取真实数据，对比报表构建结果，检查数据逻辑是否合理。
QA 检查 UI 是否正常，这个脚本检查数据是否正确。

用法:
    python validate_report_data.py          # 校验全部
    python validate_report_data.py --morning  # 仅校验晨间报告
    python validate_report_data.py --daily    # 仅校验训练复盘
    python validate_report_data.py --weekly   # 仅校验周报
    python validate_report_data.py --monthly  # 仅校验月报
    python validate_report_data.py --race     # 仅校验赛事报告
"""

import sys
import re
import argparse
import io
from pathlib import Path
from datetime import date, datetime

# Windows 终端 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_aggregator import DataAggregator
from inject_real_data import ReportDataBuilder, format_pace, pace_to_sec


# ==========================================
# 校验规则
# ==========================================

class ValidationResult:
    def __init__(self, name):
        self.name = name
        self.checks = []  # [(check_name, passed, detail)]

    def check(self, name, passed, detail=""):
        self.checks.append((name, passed, detail))
        icon = "✓" if passed else "✗"
        print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))

    @property
    def passed(self):
        return sum(1 for _, p, _ in self.checks if p)

    @property
    def failed(self):
        return sum(1 for _, p, _ in self.checks if not p)

    @property
    def total(self):
        return len(self.checks)

    def summary(self):
        icon = "✓ PASS" if self.failed == 0 else "✗ FAIL"
        print(f"\n  [{icon}] {self.name}: {self.passed}/{self.total} passed")
        if self.failed > 0:
            print(f"  失败项:")
            for name, p, detail in self.checks:
                if not p:
                    print(f"    - {name}: {detail}")


def validate_time_not_zero(time_str, label):
    """时间不能是 00:00"""
    if not time_str:
        return False, f"{label} 为空"
    if "00:00" in time_str:
        return False, f"{label} 是 00:00"
    # 检查是否包含合理的时间格式
    match = re.search(r"(\d{1,2}):(\d{2})", time_str)
    if not match:
        return False, f"{label} 格式异常: {time_str}"
    h, m = int(match.group(1)), int(match.group(2))
    if h > 23 or m > 59:
        return False, f"{label} 时间超出范围: {h}:{m:02d}"
    return True, ""


def parse_pace_any(pace_str):
    """解析多种配速格式，返回秒数"""
    # 格式1: 5'29" 或 5′29″
    try:
        return pace_to_sec(pace_str)
    except Exception:
        pass
    # 格式2: 7:43 /km 或 7:43/km
    import re
    m = re.match(r"(\d+):(\d+)", pace_str)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return 0


def validate_pace(pace_str):
    """配速合理性检查 (3'00" ~ 12'00")"""
    if pace_str == "--":
        return True, "无配速数据"
    sec = parse_pace_any(pace_str)
    if sec <= 0:
        return False, f"配速解析失败: {pace_str}"
    if sec < 180:  # < 3'00"
        return False, f"配速异常快: {pace_str} ({sec}s/km)"
    if sec > 720:  # > 12'00"
        return False, f"配速异常慢: {pace_str} ({sec}s/km)"
    return True, ""


def validate_distance(dist_km):
    """距离合理性"""
    if dist_km <= 0:
        return False, f"距离为 0 或负数: {dist_km}"
    if dist_km > 100:
        return False, f"距离异常大: {dist_km} km"
    return True, ""


def validate_hrv(hrv):
    """HRV 合理性 (20-200ms)"""
    if hrv <= 0:
        return False, f"HRV 为 0 或负数: {hrv}"
    if hrv < 15:
        return False, f"HRV 异常低: {hrv} ms"
    if hrv > 200:
        return False, f"HRV 异常高: {hrv} ms"
    return True, ""


def validate_sleep_score(score):
    """睡眠评分 (0-100)"""
    if score < 0 or score > 100:
        return False, f"睡眠评分超出范围: {score}"
    return True, ""


def validate_duration(distance_km, duration_sec, pace_str):
    """时长与距离/配速一致性"""
    if distance_km <= 0 or duration_sec <= 0:
        return True, "无数据，跳过"

    # 用距离和配速推算时长
    pace_sec = pace_to_sec(pace_str) if pace_str != "--" else 0
    if pace_sec <= 0:
        return True, "无配速，跳过"

    expected_duration = distance_km * pace_sec
    diff_pct = abs(duration_sec - expected_duration) / expected_duration * 100

    if diff_pct > 10:
        return False, f"时长与距离/配速不匹配: 实际 {duration_sec:.0f}s, 预期 {expected_duration:.0f}s (差 {diff_pct:.0f}%)"
    return True, ""


def validate_weekly_consistency(weekly_data):
    """周报内部一致性"""
    results = ValidationResult("周报一致性")

    summary = weekly_data["summary"]
    daily = weekly_data["daily_breakdown"]

    # 每日距离之和 ≈ 总距离
    total_from_daily = sum(db.get("distance", 0) for db in daily if db.get("distance"))
    total_distance = summary.get("total_distance", 0)

    if total_distance > 0:
        diff_pct = abs(total_from_daily - total_distance) / total_distance * 100
        results.check(
            "每日跑量之和 ≈ 总距离",
            diff_pct < 15,
            f"每日合计 {total_from_daily/1000:.1f}km, 总计 {total_distance/1000:.1f}km (差 {diff_pct:.0f}%)"
        )
    else:
        results.check("每日跑量之和 ≈ 总距离", True, "无跑量数据")

    # 平均配速合理性
    avg_pace = summary.get("avg_pace", "--")
    ok, detail = validate_pace(avg_pace)
    results.check("平均配速合理", ok, detail or avg_pace)

    # 训练天数 ≤ 7
    training_days = summary.get("training_days", 0)
    results.check("训练天数 ≤ 7", 0 <= training_days <= 7, f"训练天数: {training_days}")

    return results


# ==========================================
# 主校验流程
# ==========================================

def validate_morning(agg, builder):
    """校验晨间报告数据"""
    print("\n=== 晨间报告 ===")
    result = ValidationResult("晨间报告")

    # 获取原始数据
    raw = agg.get_morning_call_data()
    health = raw["health"]
    advice = raw["training_advice"]

    # 获取构建后的数据
    built = builder.build_morning()

    # 1. 时间不能是 00:00
    ok, detail = validate_time_not_zero(built["ts"], "ts 时间")
    result.check("时间不为 00:00", ok, detail)

    # 2. HRV 合理性
    hrv = agg._extract_hrv(health)
    ok, detail = validate_hrv(hrv)
    result.check("HRV 合理性", ok, detail or f"{hrv} ms")

    # 3. 睡眠评分
    sleep_score = agg._extract_sleep_score(health)
    ok, detail = validate_sleep_score(sleep_score)
    result.check("睡眠评分范围", ok, detail or f"{sleep_score} 分")

    # 4. 准备度分数 0-100
    score = advice.get("readiness_score", -1)
    result.check("准备度分数范围", 0 <= score <= 100, f"{score} 分")

    # 5. HRV 基线与实际值的差异合理性
    hrv_baseline = agg._calc_hrv_baseline(raw.get("week_health_trend", []))
    if hrv_baseline > 0:
        diff_pct = abs(hrv - hrv_baseline) / hrv_baseline * 100
        result.check(
            "HRV 波动幅度合理",
            diff_pct < 50,
            f"今日 {hrv}, 基线 {hrv_baseline:.0f}, 差 {diff_pct:.0f}%"
        )
    else:
        result.check("HRV 波动幅度合理", True, "无基线数据")

    # 6. ring_offset 与 score 对应
    expected_offset = 289.0 * (1 - score / 100)
    actual_offset = float(built["ring_offset"])
    result.check(
        "圆环偏移量与分数一致",
        abs(expected_offset - actual_offset) < 1,
        f"期望 {expected_offset:.1f}, 实际 {actual_offset:.1f}"
    )

    result.summary()
    return result


def validate_daily(agg, builder):
    """校验训练复盘数据"""
    print("\n=== 训练复盘 ===")
    result = ValidationResult("训练复盘")

    raw = agg.get_post_run_data()
    activity = raw["activity"]
    built = builder.build_daily()

    # 1. 时间不为 00:00
    ok, detail = validate_time_not_zero(built["subtitle"], "subtitle 时间")
    result.check("时间不为 00:00", ok, detail)

    # 2. 距离合理性
    dist_km = built["distance"]
    ok, detail = validate_distance(dist_km)
    result.check("距离合理", ok, detail or f"{dist_km} km")

    # 3. 配速合理性
    pace = built["pace"]
    ok, detail = validate_pace(pace)
    result.check("配速合理", ok, detail or pace)

    # 4. 时长与距离/配速一致性
    duration_sec = activity.get("duration", 0)
    ok, detail = validate_duration(dist_km, duration_sec, pace)
    result.check("时长与距离/配速一致", ok, detail)

    # 5. 活动名称非空
    result.check("活动名称非空", bool(built["name"].strip()), built["name"])

    # 6. pace_data 数据点数合理
    import json
    pace_data = json.loads(built["pace_data"])
    expected_points = max(1, int(dist_km))
    result.check(
        "配速数据点数合理",
        len(pace_data) > 0,
        f"期望 ~{expected_points} 个, 实际 {len(pace_data)} 个"
    )

    # 7. 训练类型合理
    valid_types = {"轻松跑", "高强度", "长距离跑", "赛事", "恢复跑", "间歇跑"}
    result.check(
        "训练类型有效",
        built["type"] in valid_types,
        f"'{built['type']}'"
    )

    result.summary()
    return result


def validate_weekly(agg, builder):
    """校验周报数据"""
    print("\n=== 周报 ===")
    result = ValidationResult("周报")

    raw = agg.get_weekly_data()
    built = builder.build_weekly()

    # 1. 距离合理性
    total_km = built["total_km"]
    ok, detail = validate_distance(total_km)
    result.check("总距离合理", ok, detail or f"{total_km} km")

    # 2. 配速合理性
    avg_pace = raw["summary"].get("avg_pace", "--")
    ok, detail = validate_pace(avg_pace)
    result.check("平均配速合理", ok, detail or avg_pace)

    # 3. 训练天数
    days = built["training_days"]
    result.check("训练天数 0-7", 0 <= days <= 7, f"{days} 天")

    # 4. 每日跑量数据点 = 7
    import json
    daily = json.loads(built["daily_breakdown"])
    result.check("每日跑量数据点 = 7", len(daily) == 7, f"{len(daily)} 个")

    # 5. HRV sparkline 有数据
    result.check("HRV sparkline 有数据", "," in built["hrv_sparkline"], built["hrv_sparkline"][:30])

    # 6. 每日跑量之和 ≈ 总距离
    daily_km_sum = sum(d["km"] for d in daily)
    diff_pct = abs(daily_km_sum - total_km) / total_km * 100 if total_km > 0 else 0
    result.check(
        "每日跑量之和 ≈ 总距离",
        diff_pct < 15,
        f"每日合计 {daily_km_sum:.1f}km, 总计 {total_km:.1f}km (差 {diff_pct:.0f}%)"
    )

    # 7. 训练类型占比总和 ≈ 100%
    type_total = sum(t["pct"] for t in built["training_types"])
    result.check(
        "训练类型占比总和 ≈ 100%",
        95 <= type_total <= 105,
        f"总计 {type_total}%"
    )

    result.summary()
    return result


def validate_monthly(agg, builder):
    """校验月报数据"""
    print("\n=== 月报 ===")
    result = ValidationResult("月报")

    raw = agg.get_monthly_data()
    built = builder.build_monthly()

    # 1. 距离合理性
    total_km = built["total_km"]
    ok, detail = validate_distance(total_km)
    result.check("总距离合理", ok, detail or f"{total_km} km")

    # 2. 训练天数合理
    days = built["training_days"]
    result.check("训练天数 ≥ 0", days >= 0, f"{days} 天")

    # 3. 心率区间百分比总和 ≈ 100%
    zone_total = sum(z["pct"] for z in built["hr_zones"])
    result.check(
        "心率区间总和 ≈ 100%",
        95 <= zone_total <= 105,
        f"总计 {zone_total}%"
    )

    # 4. 每日距离数据点
    import json
    daily = json.loads(built["daily_distances"])
    result.check(
        "每日距离有数据",
        len(daily) > 0,
        f"{len(daily)} 个数据点"
    )

    # 5. PB 记录格式
    pb = built["pb_records"]
    result.check("PB 记录数 = 4", len(pb) == 4, f"{len(pb)} 条")

    result.summary()
    return result


def validate_race(agg, builder):
    """校验赛事报告数据"""
    print("\n=== 赛事报告 ===")
    result = ValidationResult("赛事报告")

    raw = agg.get_race_data()
    built = builder.build_race()

    # 如果没有赛事数据，检查占位符是否正确
    if built.get("_no_race"):
        result.check("无赛事时显示占位符", True, "显示'未找到赛事记录'")
        result.check("占位符有提示信息", bool(built.get("narrative")), built.get("narrative", "")[:50])
        result.summary()
        return result

    # 1. 距离合理性
    dist = built["distance"]
    ok, detail = validate_distance(dist)
    result.check("距离合理", ok, detail or f"{dist} km")

    # 2. 配速合理性
    pace = built["avg_pace"]
    ok, detail = validate_pace(pace)
    result.check("配速合理", ok, detail or pace)

    # 3. 完赛时间非空
    result.check("完赛时间非空", built["finish_time"] != "--", built["finish_time"])

    # 4. 前后半程距离之和 ≈ 总距离
    half_sum = built["first_half_km"] + built["second_half_km"]
    diff = abs(half_sum - dist)
    result.check(
        "前后半程距离之和 ≈ 总距离",
        diff < 1,
        f"前 {built['first_half_km']} + 后 {built['second_half_km']} = {half_sum:.1f} (差 {diff:.1f})"
    )

    # 5. pace_data 有数据
    import json
    pace_data = json.loads(built["pace_data"])
    result.check("配速数据点非空", len(pace_data) > 0, f"{len(pace_data)} 个")

    # 6. 四维评分 0-100
    for dim in built["dimensions"]:
        result.check(
            f"四维评分合理: {dim['name']}",
            0 <= dim["score"] <= 100,
            f"{dim['score']} 分"
        )

    result.summary()
    return result


# ==========================================
# CLI 入口
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="报表数据校验")
    parser.add_argument("--morning", action="store_true")
    parser.add_argument("--daily", action="store_true")
    parser.add_argument("--weekly", action="store_true")
    parser.add_argument("--monthly", action="store_true")
    parser.add_argument("--race", action="store_true")
    args = parser.parse_args()

    generate_all = not (args.morning or args.daily or args.weekly or args.monthly or args.race)

    agg = DataAggregator(mock=False)
    builder = ReportDataBuilder(agg)

    all_results = []

    if generate_all or args.morning:
        all_results.append(validate_morning(agg, builder))
    if generate_all or args.daily:
        all_results.append(validate_daily(agg, builder))
    if generate_all or args.weekly:
        all_results.append(validate_weekly(agg, builder))
    if generate_all or args.monthly:
        all_results.append(validate_monthly(agg, builder))
    if generate_all or args.race:
        all_results.append(validate_race(agg, builder))

    # 汇总
    total_pass = sum(r.passed for r in all_results)
    total_fail = sum(r.failed for r in all_results)
    total_checks = sum(r.total for r in all_results)

    print("\n" + "=" * 50)
    print(f"汇总: {total_pass}/{total_checks} passed, {total_fail} failed")
    if total_fail == 0:
        print("✓ 全部校验通过")
    else:
        print("✗ 存在异常数据，请检查上方详情")
    print("=" * 50)

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
