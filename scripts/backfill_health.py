#!/usr/bin/env python3
"""
backfill_health: 补全 daily_health.json 中的历史数据断档

用法:
    python scripts/backfill_health.py                        # 自动检测断档并补全
    python scripts/backfill_health.py --start 2026-03-28     # 指定起始日期
    python scripts/backfill_health.py --end 2026-07-06       # 指定结束日期
    python scripts/backfill_health.py --days 100             # 补全最近 N 天的断档
"""
import json
import sys
import logging
from datetime import date, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from garmin_agent.config import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("backfill")


def _health_json_path() -> Path:
    return DATA_DIR / "daily_health.json"


def _load_health_json() -> dict:
    path = _health_json_path()
    if not path.exists():
        return {"metadata": {"version": "1.0", "last_sync": None, "total_days": 0}, "days": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_health_json(data: dict):
    path = _health_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def detect_gap(days: dict, max_gap_days: int = 5) -> list:
    """检测数据断档区间。连续缺失超过 max_gap_days 天的视为断档。"""
    if not days:
        return []

    dates = sorted(days.keys())
    gaps = []
    gap_start = None

    for i in range(len(dates) - 1):
        d1 = date.fromisoformat(dates[i])
        d2 = date.fromisoformat(dates[i + 1])
        delta = (d2 - d1).days

        if delta > max_gap_days:
            # 检查 d2 之后是否也有缺失（连续的大间隔）
            gap_start = d1 + timedelta(days=1)
            # 继续看下一个间隔是否紧接着
            if i + 2 < len(dates):
                d3 = date.fromisoformat(dates[i + 2])
                if (d3 - d2).days > max_gap_days:
                    # 多个连续大间隔，合并
                    continue
            gaps.append((gap_start, d2 - timedelta(days=1)))

    # 检查最新日期到今天之间是否有缺口
    latest = date.fromisoformat(dates[-1])
    today = date.today()
    if (today - latest).days > max_gap_days + 1:
        # 只报告到 latest 之后第一个有数据的日期（如果有的话）
        # 否则报告到 today
        end = latest + timedelta(days=1)
        # Check if there's a later date in the data
        # Actually, latest is the last date, so gap goes to today
        gaps.append((latest + timedelta(days=1), today))

    return gaps


def fetch_day_data(client, date_str: str) -> dict:
    """从 Garmin API 获取单日健康数据（逻辑同 sync_health）。"""
    day_entry = {}

    # 睡眠
    try:
        sleep = client.get_sleep_data(date_str)
        if sleep and isinstance(sleep, dict):
            daily = sleep.get("dailySleepDTO", {}) or {}
            sleep_time = daily.get("sleepTimeSeconds", 0) or 0
            deep = daily.get("deepSleepSeconds", 0) or 0
            rem = daily.get("remSleepSeconds", 0) or 0
            light = daily.get("lightSleepSeconds", 0) or 0
            awake_sec = daily.get("awakeSleepSeconds", 0) or 0
            awake_cnt = int(daily.get("awakeCount") or 0)
            score = None
            ss = daily.get("sleepScores", {})
            if isinstance(ss, dict):
                ov = ss.get("overall", {})
                if isinstance(ov, dict):
                    score = ov.get("value")
            if sleep_time or deep or rem:
                day_entry.update({
                    "sleep_seconds": sleep_time or None,
                    "deep_sleep_seconds": deep or None,
                    "rem_sleep_seconds": rem or None,
                    "light_sleep_seconds": light or None,
                    "awake_sleep_seconds": awake_sec or None,
                    "awake_count": awake_cnt,
                    "sleep_hours": round(sleep_time / 3600, 2) if sleep_time else None,
                    "deep_sleep_hours": round(deep / 3600, 2) if deep else None,
                    "rem_sleep_hours": round(rem / 3600, 2) if rem else None,
                    "light_sleep_hours": round(light / 3600, 2) if light else None,
                    "awake_hours": round(awake_sec / 3600, 2) if awake_sec else None,
                    "sleep_score": score,
                })
    except Exception as e:
        logger.warning(f"  睡眠数据 [{date_str}]: {e}")

    # HRV
    try:
        hrv = client.get_hrv_data(date_str)
        if hrv and isinstance(hrv, dict):
            hs = hrv.get("hrvSummary", {}) or {}
            bl = hs.get("baseline", {}) or {}
            day_entry.update({
                "hrv_last_night_avg": hs.get("lastNightAvg"),
                "hrv_weekly_avg": hs.get("weeklyAvg"),
                "hrv_status": hs.get("status"),
                "hrv_last_night_5min_high": hs.get("lastNight5MinHigh"),
                "hrv_baseline_low": bl.get("balancedLow"),
                "hrv_baseline_high": bl.get("balancedUpper"),
            })
    except Exception as e:
        logger.warning(f"  HRV数据 [{date_str}]: {e}")

    # 静息心率
    try:
        rhr = client.get_rhr_day(date_str)
        if rhr and isinstance(rhr, dict):
            mm = rhr.get("allMetrics", {}).get("metricsMap", {})
            rhr_val = None
            for k, v in mm.items():
                if "RESTING" in k and v and isinstance(v, list):
                    rhr_val = v[0].get("value")
                    break
            if rhr_val:
                day_entry["resting_hr"] = int(rhr_val)
    except Exception as e:
        logger.warning(f"  静息心率 [{date_str}]: {e}")

    # 训练准备度
    try:
        readiness = client.get_training_readiness(date_str)
        if readiness and isinstance(readiness, list) and len(readiness) > 0:
            r = readiness[0]
            score = r.get("score") or r.get("trainingReadinessScore", "N/A")
            level = r.get("level") or r.get("trainingReadinessLevel", "")
            if score != "N/A" and score:
                day_entry["training_readiness_score"] = int(score)
            if level:
                day_entry["training_readiness_level"] = level
    except Exception as e:
        logger.warning(f"  训练准备度 [{date_str}]: {e}")

    # 压力
    try:
        stress = client.get_stress_data(date_str)
        if stress:
            day_entry["avg_stress_level"] = stress.get("avgStressLevel")
            day_entry["max_stress_level"] = stress.get("maxStressLevel")
    except Exception as e:
        logger.warning(f"  压力数据 [{date_str}]: {e}")

    return day_entry


def backfill(start_date: date, end_date: date, batch_size: int = 14):
    """补全指定日期范围内的健康数据。"""
    from garmin_agent.client import GarminClient

    # 加载现有数据
    health_data = _load_health_json()
    days = health_data.setdefault("days", {})

    # 计算需要补全的日期
    current = start_date
    to_fetch = []
    while current <= end_date:
        ds = current.isoformat()
        if ds not in days or not any(days[ds].get(f) for f in [
            "sleep_seconds", "hrv_last_night_avg", "resting_hr",
            "training_readiness_score", "avg_stress_level",
        ]):
            to_fetch.append(ds)
        current += timedelta(days=1)

    if not to_fetch:
        print(f"✅ 指定范围 [{start_date} ~ {end_date}] 数据已完整，无需补全")
        return

    print(f"📋 检测到 {len(to_fetch)} 天需要补全数据")
    print(f"   范围: {to_fetch[0]} ~ {to_fetch[-1]}")

    # 连接 Garmin
    print("\n🔐 连接 Garmin...")
    client = GarminClient()
    if not client.connect():
        print("❌ Garmin 连接失败！")
        sys.exit(1)
    print("✅ 连接成功")

    # 分批补全
    success = 0
    empty = 0
    errors = 0

    for i, date_str in enumerate(to_fetch):
        print(f"  [{i+1}/{len(to_fetch)}] 获取 {date_str}...", end=" ", flush=True)

        day_entry = fetch_day_data(client, date_str)

        # 检查是否有核心数据
        _CORE = ["sleep_seconds", "hrv_last_night_avg", "resting_hr",
                 "training_readiness_score", "avg_stress_level"]
        has_core = any(day_entry.get(f) for f in _CORE)

        if has_core:
            day_entry["synced_at"] = date.today().isoformat()
            day_entry["backfilled"] = True
            days[date_str] = day_entry
            success += 1
            core_vals = [f"{k}={str(v)[:20]}" for k, v in day_entry.items()
                         if v is not None and k not in (
                             "synced_at", "backfilled",
                             "sleep_hours", "deep_sleep_hours",
                             "rem_sleep_hours", "light_sleep_hours",
                             "awake_hours")]
            print(f"  ✅ ({', '.join(core_vals[:3])}...)")
        else:
            empty += 1
            print("⚠️  无数据")

    # 保存
    health_data["metadata"]["last_sync"] = date.today().isoformat()
    health_data["metadata"]["total_days"] = len(days)
    _save_health_json(health_data)

    print(f"\n{'='*60}")
    print(f"📊 补全结果:")
    print(f"  成功写入: {success} 天")
    print(f"  无数据:    {empty} 天（设备未同步或当日无数据）")
    print(f"  错误:      {errors} 天")
    print(f"  总天数:    {len(days)} 天")
    print(f"  💾 已写入 {_health_json_path()}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="补全 daily_health.json 历史数据断档")
    parser.add_argument("--start", type=str, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--days", type=int, help="补全最近 N 天的断档")
    parser.add_argument("--auto", action="store_true", help="自动检测断档并补全")
    args = parser.parse_args()

    print("🏃 Garmin Agent - 历史数据补全工具")

    # 加载数据，检测断档
    health_data = _load_health_json()
    days = health_data.get("days", {})

    if not days:
        print("❌ daily_health.json 为空或不存在，请先运行 sync_data.py")
        sys.exit(1)

    dates = sorted(days.keys())
    print(f"📊 当前数据: {len(dates)} 天")
    print(f"   最早: {dates[0]}")
    print(f"   最新: {dates[-1]}")

    # 检测断档
    gaps = detect_gap(days)
    if gaps:
        print(f"\n⚠️  检测到 {len(gaps)} 个数据断档区间:")
        for start, end in gaps:
            gap_days = (end - start).days + 1
            print(f"   {start} ~ {end} (缺失约 {gap_days} 天)")

    # 确定补全范围
    if args.start and args.end:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    elif args.days:
        end_date = date.today()
        start_date = end_date - timedelta(days=args.days)
    elif args.auto and gaps:
        # 补全最大的断档区间
        largest_gap = max(gaps, key=lambda g: (g[1] - g[0]).days)
        start_date, end_date = largest_gap
    elif gaps:
        # 默认补全所有断档
        start_date = min(g[0] for g in gaps)
        end_date = max(g[1] for g in gaps)
    else:
        print("\n✅ 未检测到数据断档")
        sys.exit(0)

    print(f"\n🎯 补全范围: {start_date} ~ {end_date}")
    backfill(start_date, end_date)


if __name__ == "__main__":
    main()
