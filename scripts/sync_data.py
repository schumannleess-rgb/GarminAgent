"""
Garmin Agent - 数据同步脚本

同步 Garmin Connect 数据到本地缓存：
1. 活动分类缓存（同步活动列表、心率区间、圈数据、训练类型分类）
2. 健康数据（当日睡眠、HRV、静息心率、训练准备度）
3. 训练状态和能力数据

用法:
    cd GarminAgent && python scripts/sync_data.py
    cd GarminAgent && python scripts/sync_data.py --full    # 强制全量同步
    cd GarminAgent && python scripts/sync_data.py --health  # 仅同步健康数据
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import date, datetime
from dotenv import load_dotenv

# Windows encoding fix
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file)

from garmin_agent.config import DATA_DIR, RUNTIME_DIR

runtime_env_file = RUNTIME_DIR / ".env"
if runtime_env_file.exists():
    load_dotenv(runtime_env_file, override=False)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sync")

# Suppress verbose library logs
logging.getLogger("garminconnect").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def bold(s: str) -> str:
    return f"\033[1m{s}\033[0m"


def green(s: str) -> str:
    return f"\033[92m{s}\033[0m"


def yellow(s: str) -> str:
    return f"\033[93m{s}\033[0m"


def red(s: str) -> str:
    return f"\033[91m{s}\033[0m"


def fmt_dt(ts) -> str:
    """Format timestamp for display."""
    if not ts:
        return "N/A"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return str(ts)[:19]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Garmin Agent 数据同步")
    parser.add_argument("--full", action="store_true", help="强制全量同步（忽略缓存年龄）")
    parser.add_argument("--health", action="store_true", help="仅同步健康数据")
    args = parser.parse_args()

    print(bold("\n🏃 Garmin Agent - 数据同步"))
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ── Step 1: 连接 Garmin ──
    section("Step 1: 连接 Garmin")
    print("  正在连接 Garmin Connect...")

    from login.garmin_login import garmin_login
    from garmin_agent.client import GarminClient

    try:
        client = GarminClient()
        if not client.connect():
            print(red("  ❌ Garmin 连接失败！"))
            print("  提示: TOKEN 可能已过期，请运行 agent 交互登录更新 TOKEN。")
            sys.exit(1)
        print(green("  ✅ Garmin 连接成功"))
    except Exception as e:
        print(red(f"  ❌ 连接异常: {e}"))
        sys.exit(1)

    if args.health:
        sync_health(client)
        return 0

    # ── Step 2: 同步活动分类缓存 ──
    section("Step 2: 同步活动分类缓存")

    from garmin_agent.cache_manager import ActivityClassificationCache
    from garmin_agent.cache_sync import CacheSyncManager

    cache = ActivityClassificationCache()
    sync_mgr = CacheSyncManager(client, cache)

    # 显示缓存当前状态
    try:
        stats = cache.get_stats()
        total = stats["total_count"]
        age = stats.get("cache_age_hours")
        last_sync = stats.get("last_sync")
        print(f"  缓存状态:")
        print(f"    - 现有活动: {total} 条")
        print(f"    - 上次同步: {fmt_dt(last_sync)}")
        if age is not None:
            age_days = age / 24
            print(f"    - 缓存年龄: {age:.1f}h ({age_days:.1f} 天)")
        else:
            print(f"    - 缓存年龄: 无（全新）")
        print(f"    - 数据类型分布: {json.dumps(stats.get('type_distribution', {}), ensure_ascii=False)}")
    except Exception as e:
        print(yellow(f"  ⚠️ 无法读取缓存状态: {e}"))

    # 执行同步
    print(f"\n  正在同步活动数据...")
    try:
        if args.full:
            print(yellow("  ⚡ 强制全量同步模式"))
            result = sync_mgr.full_sync()
        else:
            result = sync_mgr.sync_on_login()

        status = result.get("status", "unknown")
        if status == "skipped":
            reason = result.get("reason", "")
            age_h = result.get("cache_age_hours", 0)
            print(green(f"  ⏭️  跳过同步 (缓存仍在有效期内: {age_h:.1f}h / 24h)"))
        elif status == "success":
            new = result.get("new_count", 0)
            total = result.get("total_count", 0)
            elapsed = result.get("elapsed_seconds", 0)
            if new == 0:
                print(green(f"  ✅ 同步完成，无新活动 (缓存共 {total} 条, 耗时 {elapsed:.1f}s)"))
            else:
                print(green(f"  ✅ 同步完成: 新增 {new} 条, 缓存共 {total} 条 (耗时 {elapsed:.1f}s)"))
        else:
            print(red(f"  ❌ 同步失败: {result.get('error', '未知错误')}"))

    except Exception as e:
        print(red(f"  ❌ 同步异常: {e}"))
        logger.exception("Sync error")

    # 显示同步后缓存统计
    section("缓存统计 (同步后)")
    try:
        stats = cache.get_stats()
        total = stats["total_count"]
        last_sync = stats.get("last_sync")
        type_dist = stats.get("type_distribution", {})
        print(f"  总活动数: {bold(str(total))}")
        print(f"  上次同步: {fmt_dt(last_sync)}")
        print(f"\n  训练类型分布:")
        for t, count in sorted(type_dist.items(), key=lambda x: -x[1]):
            print(f"    {t:20s}: {count}")
    except Exception as e:
        print(yellow(f"  ⚠️ 无法获取缓存统计: {e}"))

    # ── Step 3: 同步健康数据 ──
    section("Step 3: 健康数据快照")
    sync_health(client)

    # ── Step 4: 训练状态 ──
    section("Step 4: 训练状态")
    try:
        status = client.get_training_status()
        if status:
            # Flatten the nested structure
            if isinstance(status, dict):
                summary = {}
                for k, v in status.items():
                    if isinstance(v, dict):
                        for sk, sv in v.items():
                            summary[f"{k}.{sk}"] = sv
                    else:
                        summary[k] = v
                for k, v in summary.items():
                    print(f"    {k:30s}: {v}")
    except Exception as e:
        print(yellow(f"  ⚠️ 无法获取训练状态: {e}"))

    print(f"\n{bold(green('✅ 同步完成!'))}")
    print(f"  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return 0


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


def sync_health(client):
    """同步健康数据：打印 + 写入 data/daily_health.json"""
    today = date.today().strftime("%Y-%m-%d")
    health_data = _load_health_json()
    days = health_data.setdefault("days", {})
    day_entry = {}

    # 睡眠
    try:
        sleep = client.get_sleep_data(today)
        if sleep and isinstance(sleep, dict):
            daily = sleep.get("dailySleepDTO", {}) or {}
            sleep_time = daily.get("sleepTimeSeconds", 0) or 0
            deep = daily.get("deepSleepSeconds", 0) or 0
            rem = daily.get("remSleepSeconds", 0) or 0
            light = daily.get("lightSleepSeconds", 0) or 0
            awake_sec = daily.get("awakeSleepSeconds", 0) or 0
            score = None
            ss = daily.get("sleepScores", {})
            if isinstance(ss, dict):
                ov = ss.get("overall", {})
                if isinstance(ov, dict):
                    score = ov.get("value")
            print(f"  睡眠:")
            print(f"    - 总时长: {sleep_time//3600}h{(sleep_time%3600)//60}m" if sleep_time else "    - 总时长: N/A")
            print(f"    - 深睡: {deep//60}m" if deep else "")
            print(f"    - REM: {rem//60}m" if rem else "")
            print(f"    - 浅睡: {light//60}m" if light else "")
            print(f"    - 睡眠评分: {score}")
            day_entry.update({
                "sleep_seconds": sleep_time or None,
                "deep_sleep_seconds": deep or None,
                "rem_sleep_seconds": rem or None,
                "light_sleep_seconds": light or None,
                "awake_sleep_seconds": awake_sec or None,
                "sleep_hours": round(sleep_time / 3600, 2) if sleep_time else None,
                "deep_sleep_hours": round(deep / 3600, 2) if deep else None,
                "rem_sleep_hours": round(rem / 3600, 2) if rem else None,
                "light_sleep_hours": round(light / 3600, 2) if light else None,
                "awake_hours": round(awake_sec / 3600, 2) if awake_sec else None,
                "sleep_score": score,
            })
    except Exception as e:
        print(yellow(f"  ⚠️ 睡眠数据: {e}"))

    # HRV
    try:
        hrv = client.get_hrv_data(today)
        if hrv and isinstance(hrv, dict):
            hs = hrv.get("hrvSummary", {}) or {}
            weekly_avg = hs.get("weeklyAvg", "N/A")
            last_night = hs.get("lastNightAvg", "N/A")
            status = hs.get("status", "N/A")
            bl = hs.get("baseline", {}) or {}
            print(f"  HRV:")
            print(f"    - 昨晚: {last_night}")
            print(f"    - 周均值: {weekly_avg}")
            if status and status != "N/A":
                print(f"    - 状态: {status}")
            day_entry.update({
                "hrv_last_night_avg": hs.get("lastNightAvg"),
                "hrv_weekly_avg": hs.get("weeklyAvg"),
                "hrv_status": hs.get("status"),
                "hrv_last_night_5min_high": hs.get("lastNight5MinHigh"),
                "hrv_baseline_low": bl.get("balancedLow"),
                "hrv_baseline_high": bl.get("balancedUpper"),
            })
    except Exception as e:
        print(yellow(f"  ⚠️ HRV数据: {e}"))

    # 静息心率
    try:
        rhr = client.get_rhr_day(today)
        if rhr and isinstance(rhr, dict):
            mm = rhr.get("allMetrics", {}).get("metricsMap", {})
            rhr_val = None
            for k, v in mm.items():
                if "RESTING" in k and v and isinstance(v, list):
                    rhr_val = v[0].get("value")
                    break
            print(f"  静息心率: {rhr_val}")
            day_entry["resting_hr"] = int(rhr_val) if rhr_val else None
    except Exception as e:
        print(yellow(f"  ⚠️ 静息心率: {e}"))

    # 训练准备度
    try:
        readiness = client.get_training_readiness(today)
        if readiness and isinstance(readiness, list) and len(readiness) > 0:
            r = readiness[0]
            score = r.get("score") or r.get("trainingReadinessScore", "N/A")
            level = r.get("level") or r.get("trainingReadinessLevel", "")
            print(f"  训练准备度: {score} ({level})")
            day_entry["training_readiness_score"] = int(score) if score != "N/A" else None
            day_entry["training_readiness_level"] = level or None
    except Exception as e:
        print(yellow(f"  ⚠️ 训练准备度: {e}"))

    # 压力
    try:
        stress = client.get_stress_data(today)
        if stress:
            day_entry["avg_stress_level"] = stress.get("avgStressLevel")
            day_entry["max_stress_level"] = stress.get("maxStressLevel")
    except Exception as e:
        print(yellow(f"  ⚠️ 压力数据: {e}"))

    # 写入 JSON
    if day_entry:
        day_entry["synced_at"] = date.today().isoformat()
        day_entry["updated_at"] = date.today().isoformat()
        days[today] = day_entry
        health_data["metadata"]["last_sync"] = date.today().isoformat()
        health_data["metadata"]["total_days"] = len(days)
        _save_health_json(health_data)
        print(f"  💾 已写入 {_health_json_path()} ({len(days)} 天)")
    else:
        print(f"  ℹ️  今日无新数据，跳过写入")


if __name__ == "__main__":
    sys.exit(main())
