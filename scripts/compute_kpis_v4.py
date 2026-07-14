#!/usr/bin/env python3
"""
compute_kpis_v4: 基于 Garmin API 实时查询 + V3 数据库历史基线，计算当日 KPI

流程:
  1. 尝试从 Garmin API 获取今日健康数据（HRV、RHR、睡眠、准备度）
  2. API 数据为空时，回退到 V3 数据库获取最新记录
  3. 从 V3 数据库计算历史基线（14d HRV、28d RHR、7d 睡眠）
  4. 应用同样的 KPI 评分公式，输出完整 JSON

用法:
  python scripts/compute_kpis_v4.py
  python scripts/compute_kpis_v4.py --pretty
  python scripts/compute_kpis_v4.py --date 2026-03-27
  python scripts/compute_kpis_v4.py --output result.json
"""

import json
import sys
import math
import logging
from pathlib import Path
from datetime import date, timedelta, datetime
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from garmin_agent.config import DATA_DIR

HEALTH_JSON = DATA_DIR / "daily_health.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("kpi_v4")


# ==========================================
# Scoring Functions (移植自 compute_all_kpis.py)
# ==========================================

def score_hrv_vars(last_night, weekly):
    result = {"last_night_ms": last_night, "weekly_avg_ms": weekly, "fallback_used": False}
    if last_night <= 0 or weekly <= 0:
        result.update({"score": 75, "zone": "FALLBACK", "fallback_used": True,
                       "ln_last_night": None, "ln_baseline": None,
                       "pct_change": None, "pct_change_pct": None})
        return result
    cl = math.log(last_night); bl = math.log(weekly)
    p = (cl - bl) / bl
    result.update({"ln_last_night": round(cl, 4), "ln_baseline": round(bl, 4),
                   "pct_change": round(p, 6), "pct_change_pct": round(p * 100, 2)})
    anchors = [(0.10, 70, "spike"), (0.05, 85, "green_high"), (0.00, 75, "green_normal_mid"),
               (-0.05, 60, "green_low_yellow_high"), (-0.08, 40, "yellow_low_red_high"),
               (-0.15, 10, "red_deep"), (-0.20, 0, "severe")]
    result["anchors"] = [{"pct_change": a, "score": s, "label": l} for a, s, l in anchors]
    if p > 0.10: s = 70; z = "SPIKE"
    elif p > 0.05: s = 85 + (p - 0.05) * (-300); z = "GREEN_HIGH"
    elif p >= 0: s = 75 + p * 200; z = "GREEN_NORMAL"
    elif p >= -0.05: s = 75 + p * 300; z = "GREEN_NORMAL"
    elif p > -0.08: s = 60 + (p + 0.05) * (2000 / 3); z = "YELLOW"
    elif p > -0.15: s = 40 + (p + 0.08) * (3000 / 7); z = "RED"
    elif p >= -0.20: s = 10 + (p + 0.15) * 200; z = "RED_DEEP"
    else: s = 0; z = "SEVERE"
    result["score"] = round(min(100, max(0, s))); result["zone"] = z
    return result


def score_rhr_vars(current_rhr, baseline_rhr_28d):
    result = {"current_bpm": current_rhr, "baseline_bpm": baseline_rhr_28d}
    d = current_rhr - baseline_rhr_28d
    result["deviation"] = d; result["deviation_bpm"] = f"{d:+d} bpm"
    anchors = [(-3, 95, "very_low"), (0, 75, "baseline"),
               (3, 55, "mild_fatigue"), (6, 30, "fatigue"), (10, 0, "severe")]
    result["anchors"] = [{"deviation_bpm": a, "score": s, "label": l} for a, s, l in anchors]
    if d < -3: s = 95; z = "VERY_LOW"
    elif d <= 0: s = 95 + (d + 3) * (-20 / 3); z = "NORMAL" if d >= -1 else "LOW"
    elif d <= 3: s = 75 + d * (-20 / 3); z = "NORMAL"
    elif d <= 6: s = 55 + (d - 3) * (-25 / 3); z = "MILD_FATIGUE"
    elif d <= 10: s = 30 + (d - 6) * (-7.5); z = "FATIGUE"
    else: s = 0; z = "SEVERE"
    result["score"] = round(min(100, max(0, s))); result["zone"] = z
    return result


def score_sleep_vars(total_sec, deep_sec, rem_sec, awake_cnt, gs=None):
    result = {"total_seconds": total_sec, "deep_seconds": deep_sec,
              "rem_seconds": rem_sec, "awake_count": awake_cnt}
    if gs is not None:
        result["garmin_score_used"] = True; result["score"] = gs; result["sub_scores"] = {}
        return result
    result["garmin_score_used"] = False
    th = total_sec / 3600; result["total_hours"] = round(th, 2)
    dp = (deep_sec / total_sec * 100) if total_sec > 0 else 0; result["deep_pct"] = round(dp, 2)
    rp = (rem_sec / total_sec * 100) if total_sec > 0 else 0; result["rem_pct"] = round(rp, 2)
    if th < 5: ds = 10; dz = "SEVERE_SHORT"
    elif th < 6: ds = round(10 + (th - 5) * 35, 1); dz = "SHORT"
    elif th < 7: ds = round(45 + (th - 6) * 35, 1); dz = "MODERATE"
    elif th <= 9: ds = round(80 + (th - 7) * 10, 1); dz = "IDEAL"
    else: ds = round(max(50, 100 - (th - 9) * 20), 1); dz = "EXCESS"
    if dp < 5: des = 20; dez = "SEVERE_LOW"
    elif dp < 10: des = round(20 + (dp - 5) * 8, 1); dez = "LOW"
    elif dp <= 25: des = round(60 + (dp - 10) * (40 / 15), 1); dez = "IDEAL"
    else: des = 90; dez = "HIGH"
    if rp < 10: res = round(30 + rp * 2, 1); rez = "LOW"
    elif rp < 18: res = round(50 + (rp - 10) * 2.5, 1); rez = "MODERATE"
    elif rp <= 25: res = round(70 + (rp - 18) * (30 / 7), 1); rez = "IDEAL"
    else: res = 85; rez = "HIGH"
    if awake_cnt == 0: aws = 100; az = "NONE"
    elif awake_cnt == 1: aws = 80; az = "ONCE"
    elif awake_cnt == 2: aws = 60; az = "TWICE"
    else: aws = round(max(0, 45 - (awake_cnt - 3) * 15), 1); az = "FRAGMENTED"
    result["sub_scores"] = {
        "duration": {"value": ds, "zone": dz, "weight": 0.30},
        "deep": {"value": des, "zone": dez, "weight": 0.35},
        "rem": {"value": res, "zone": rez, "weight": 0.15},
        "awake": {"value": aws, "zone": az, "weight": 0.20}
    }
    result["weights"] = {"duration": 0.30, "deep": 0.35, "rem": 0.15, "awake": 0.20}
    result["score"] = round(ds * 0.30 + des * 0.35 + res * 0.15 + aws * 0.20)
    return result


def score_readiness_vars(rscore):
    return {"original_score": rscore, "score": min(rscore, 100),
            "zone": "GREEN" if rscore >= 80 else "YELLOW" if rscore >= 60 else "RED"}


def cross_dimension_validation(hrv_pct, rhr_dev, sleep_hours, awake_cnt, deep_pct):
    patterns = [
        {"id": "IDEAL_RECOVERY", "label": "理想恢复",
         "condition_desc": "HRV↑↑ RHR↓→ 睡眠优", "ref": "[R2] Buchheit 2014",
         "match": hrv_pct >= -5 and abs(rhr_dev) <= 3 and sleep_hours >= 7 and awake_cnt <= 1},
        {"id": "SYMPATHETIC_FATIGUE", "label": "交感疲劳",
         "condition_desc": "HRV↓↓ RHR↑↑ 睡眠差", "ref": "[R10] Plews 2013",
         "match": hrv_pct < -8 and rhr_dev > 3 and (sleep_hours < 6 or awake_cnt >= 3)},
        {"id": "PARASYMPATHETIC_REBOUND", "label": "副交感反弹",
         "condition_desc": "HRV↑↑↑ RHR↓↓ 睡眠中", "ref": "[R9] Recovery Tower Spike",
         "match": hrv_pct > 10 and rhr_dev < -3},
        {"id": "SLEEP_DEBT", "label": "睡眠债务疲劳",
         "condition_desc": "HRV↓ RHR→ 睡眠差·短", "ref": "[R16] Ohayon 2004",
         "match": -8 <= hrv_pct < -5 and abs(rhr_dev) <= 3 and (sleep_hours < 6 or deep_pct < 10)},
        {"id": "HIGH_LOAD_ADAPTATION", "label": "高负荷适应",
         "condition_desc": "HRV↓ RHR↑ 睡眠中", "ref": "[R22] Chalencon 2012",
         "match": hrv_pct < -5 and 0 < rhr_dev <= 3}
    ]
    matched = [p for p in patterns if p["match"]]
    return {"num_patterns_checked": len(patterns), "patterns_checked": patterns,
            "num_matched": len(matched), "matched_patterns": matched}


def compute_recovery(hrv_score, sleep_score, rhr_score, readiness_score):
    w = {"hrv": 0.35, "sleep": 0.30, "rhr": 0.20, "readiness": 0.15}
    score = round(hrv_score * 0.35 + sleep_score * 0.30 + rhr_score * 0.20 + readiness_score * 0.15)
    if score >= 85: grade, label, zone = "A", "🟢 状态极佳", "EXCELLENT"
    elif score >= 70: grade, label, zone = "B", "🔵 状态良好", "GOOD"
    elif score >= 55: grade, label, zone = "C", "🟡 需要注意", "CAUTION"
    elif score >= 40: grade, label, zone = "D", "🟠 恢复不足", "POOR"
    else: grade, label, zone = "F", "🔴 需要休息", "CRITICAL"
    steps = [
        f"HRV: {hrv_score} x 0.35 = {hrv_score * 0.35:.2f}",
        f"Sleep: {sleep_score} x 0.30 = {sleep_score * 0.30:.2f}",
        f"RHR: {rhr_score} x 0.20 = {rhr_score * 0.20:.2f}",
        f"Readiness: {readiness_score} x 0.15 = {readiness_score * 0.15:.2f}",
        f"Total: {hrv_score * 0.35 + sleep_score * 0.30 + rhr_score * 0.20 + readiness_score * 0.15:.2f} -> {score}"
    ]
    return {"recovery_score": score, "weights": w, "grade": grade, "label": label,
            "zone": zone, "calculation_steps": steps,
            "formula": "recovery = HRV x 0.35 + Sleep x 0.30 + RHR x 0.20 + Readiness x 0.15",
            "reference": "§4.6, [R2] Buchheit 2014, [R16] Ohayon 2004, [R12] Bosquet 2003"}


# ==========================================
# Data Sources
# ==========================================


def fetch_from_api(target_date: str, client) -> dict:
    """从 Garmin API 获取今日健康数据"""
    from garmin_agent.client import GarminClient

    logger.info(f"[API] 获取 {target_date} 健康数据...")

    # 睡眠
    sleep_raw = {"total_seconds": 0, "deep_seconds": 0, "rem_seconds": 0,
                 "awake_count": 0, "garmin_sleep_score": None}
    try:
        sleep = client.get_sleep_data(target_date)
        if sleep and isinstance(sleep, dict):
            dto = sleep.get("dailySleepDTO", {}) or {}
            total_sec = dto.get("sleepTimeSeconds") or 0
            if total_sec > 0:
                sleep_raw = {
                    "total_seconds": int(total_sec),
                    "deep_seconds": int(dto.get("deepSleepSeconds") or 0),
                    "rem_seconds": int(dto.get("remSleepSeconds") or 0),
                    "awake_count": int(dto.get("awakeCount") or 0),
                    "garmin_sleep_score": dto.get("sleepScores", {}).get("overall", {}).get("value") if isinstance(dto.get("sleepScores"), dict) else None,
                }
                logger.info(f"[API] 睡眠数据: {sleep_raw['total_seconds']}s, score={sleep_raw['garmin_sleep_score']}")
    except Exception as e:
        logger.warning(f"[API] 睡眠获取失败: {e}")

    # HRV
    hrv_raw = {"last_night": 0, "weekly_avg": 0, "status": ""}
    try:
        hrv = client.get_hrv_data(target_date)
        if hrv and isinstance(hrv, dict) and hrv.get("lastNightAvg"):
            hrv_raw = {
                "last_night": hrv.get("lastNightAvg") or 0,
                "weekly_avg": hrv.get("weeklyAvg") or 0,
                "status": hrv.get("status") or "",
            }
            logger.info(f"[API] HRV: last_night={hrv_raw['last_night']}, weekly={hrv_raw['weekly_avg']}")
    except Exception as e:
        logger.warning(f"[API] HRV获取失败: {e}")

    # RHR（从 heart_rates 里取）
    rhr = 0
    try:
        hr = client.get_heart_rates(target_date)
        if hr and isinstance(hr, dict):
            rhr_val = hr.get("restingHeartRate") or hr.get("lastSevenDaysAvgRestingHeartRate")
            if rhr_val:
                rhr = int(rhr_val)
                logger.info(f"[API] RHR: {rhr}")
    except Exception as e:
        logger.warning(f"[API] RHR获取失败: {e}")

    # 准备度
    readiness_val = 0
    try:
        rd = client.get_training_readiness(target_date)
        if rd and isinstance(rd, list) and len(rd) > 0:
            score = rd[0].get("score") or rd[0].get("trainingReadinessScore") or 0
            readiness_val = int(score)
            if readiness_val > 0:
                logger.info(f"[API] 准备度: {readiness_val}")
    except Exception as e:
        logger.warning(f"[API] 准备度获取失败: {e}")

    has_data = sleep_raw["total_seconds"] > 0 or hrv_raw["last_night"] > 0 or rhr > 0 or readiness_val > 0
    return {
        "has_data": has_data,
        "hrv_raw": hrv_raw,
        "rhr_raw": rhr,
        "sleep_raw": sleep_raw,
        "readiness_raw": {"score": readiness_val, "level": ""},
        "source": "api" if has_data else "api_empty",
    }


def _load_health_json():
    """Load daily_health.json, return days dict or None."""
    if not HEALTH_JSON.exists():
        logger.warning(f"[json] 数据文件不存在: {HEALTH_JSON}")
        return None
    with open(HEALTH_JSON, encoding="utf-8") as f:
        data = json.load(f)
    days = data.get("days", {})
    if not days:
        logger.warning("[json] 数据文件为空")
        return None
    return days


def _filter_valid(days, field, max_days):
    """Return up to max_days entries sorted by date desc where field is not None."""
    items = [
        {"date": d, "value": v[field]}
        for d, v in days.items()
        if isinstance(v, dict) and v.get(field) is not None
    ]
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:max_days]


def fetch_from_db(target_date: str = None) -> dict:
    """从 data/daily_health.json 获取历史数据"""
    days = _load_health_json()
    if not days:
        return None

    valid_dates = sorted(days.keys(), reverse=True)
    latest = valid_dates[0]
    target = target_date if target_date in days else latest
    if target not in days:
        logger.info(f"[json] {target} 不存在，使用最新: {latest}")
        target = latest

    logger.info(f"[json] 使用数据: {target} (最新: {latest})")

    l = days[target]

    # 估算 awake_count
    awake_sec = l.get("awake_sleep_seconds") or 0
    awake_cnt = min(int(awake_sec / 300), 10) if awake_sec > 0 else 0

    # 历史数据
    hrv_rows = _filter_valid(days, "hrv_last_night_avg", 14)
    rhr_rows = _filter_valid(days, "resting_hr", 28)
    sleep_rows = [
        {"date": d, "total_sec": int(v.get("sleep_seconds") or 0),
         "deep_sec": int(v.get("deep_sleep_seconds") or 0), "garmin_score": v.get("sleep_score")}
        for d, v in sorted(days.items(), reverse=True)[:7]
        if isinstance(v, dict) and v.get("sleep_seconds")
    ]
    rd_rows = _filter_valid(days, "training_readiness_score", 7)

    return {
        "data_date": target,
        "latest_db_date": latest,
        "hrv_raw": {
            "last_night": l.get("hrv_last_night_avg") or 0,
            "weekly_avg": l.get("hrv_weekly_avg") or 0,
            "status": l.get("hrv_status") or "",
        },
        "rhr_raw": l.get("resting_hr") or 0,
        "sleep_raw": {
            "total_seconds": int(l.get("sleep_seconds") or 0),
            "deep_seconds": int(l.get("deep_sleep_seconds") or 0),
            "rem_seconds": int(l.get("rem_sleep_seconds") or 0),
            "awake_count": awake_cnt,
            "garmin_sleep_score": l.get("sleep_score"),
        },
        "readiness_raw": {
            "score": l.get("training_readiness_score") or 0,
            "level": l.get("training_readiness_level") or "",
        },
        "history": {
            "hrv_14d": hrv_rows,
            "rhr_28d": rhr_rows,
            "sleep_7d": sleep_rows,
            "readiness_7d": [
                {"date": r["date"], "score": r["value"], "level": days[r["date"]].get("training_readiness_level", "")}
                for r in rd_rows
            ],
        },
        "profile": {
            "vo2max": l.get("vo2_max") or "",
            "bmi": l.get("bmi"),
            "device": "Forerunner 955 Solar",
            "training_status_phrase": l.get("training_status") or "RECOVERY",
            "acwr_percent": l.get("training_load") or 0,
            "total_steps": l.get("total_steps") or 0,
            "total_distance_m": l.get("total_distance_m") or 0,
            "active_calories": l.get("active_kcal") or 0,
            "avg_stress": l.get("avg_stress_level"),
            "max_stress": l.get("max_stress_level"),
            "min_hr": l.get("min_hr"),
            "max_hr": l.get("max_hr"),
        },
        "source": "local_json",
    }


def compute_kpis(data: dict, target_date: str) -> dict:
    """从统一数据字典计算所有 KPI"""
    result = {
        "date": target_date,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "script_version": "2.0-v4",
        "data_source": data.get("source", "unknown"),
    }

    if data.get("source") == "api_empty" and data.get("db_fallback"):
        fallback = data["db_fallback"]
        result["data_source"] = "api(empty)_db_fallback"
        result["data_date"] = fallback["data_date"]
        result["latest_db_date"] = fallback["latest_db_date"]
        hrv_raw = fallback["hrv_raw"]
        rhr_raw = fallback["rhr_raw"]
        sleep_raw = fallback["sleep_raw"]
        readiness_raw = fallback["readiness_raw"]
        history = fallback["history"]
        profile = fallback["profile"]
        result["note"] = f"API 返回空数据，使用 V3 数据库 {fallback['data_date']} 数据"
    else:
        result["data_date"] = data.get("data_date", target_date)
        result["latest_db_date"] = data.get("latest_db_date", target_date)
        hrv_raw = data["hrv_raw"]
        rhr_raw = data["rhr_raw"]
        sleep_raw = data["sleep_raw"]
        readiness_raw = data["readiness_raw"]
        history = data["history"]
        profile = data["profile"]

    result["raw_inputs"] = {
        "hrv": hrv_raw,
        "rhr": {"current_bpm": rhr_raw},
        "sleep": sleep_raw,
        "readiness": readiness_raw,
        "profile": profile,
    }
    result["history"] = history

    # 基线计算
    rv = [v for v in [h["value"] for h in history["hrv_14d"]] if v > 0]
    hrv_baseline_7d = round(sum(rv) / len(rv)) if rv else hrv_raw["weekly_avg"]
    rhr_vals = [h["value"] for h in history["rhr_28d"]]
    rhr_baseline_28d = round(sum(rhr_vals) / len(rhr_vals)) if rhr_vals else rhr_raw
    sleep_tots = [h["total_sec"] for h in history["sleep_7d"]]
    sleep_base_7d = round(sum(sleep_tots) / len(sleep_tots)) if sleep_tots else sleep_raw["total_seconds"]
    deep_pcts = [(h["deep_sec"] / h["total_sec"] * 100) for h in history["sleep_7d"] if h["total_sec"] > 0]
    deep_base_7d = round(sum(deep_pcts) / len(deep_pcts), 1) if deep_pcts else 0

    result["baselines"] = {
        "hrv_baseline_7d": hrv_baseline_7d,
        "rhr_baseline_28d": rhr_baseline_28d,
        "sleep_baseline_7d": {
            "total_seconds": sleep_base_7d,
            "total_hours": round(sleep_base_7d / 3600, 2),
            "deep_pct_avg": deep_base_7d,
        },
        "formulas": {
            "hrv_baseline": "rolling_mean(last_7_nights_HRV), Plews 2014",
            "rhr_baseline": "rolling_mean(last_28_days_RHR), Bosquet 2003",
            "sleep_baseline": "rolling_mean(last_7_days_total_sleep), Ohayon 2004",
        },
    }

    # 维度评分
    hrv = score_hrv_vars(hrv_raw["last_night"] or hrv_raw["weekly_avg"], hrv_baseline_7d)
    rhr_sc = score_rhr_vars(rhr_raw, rhr_baseline_28d)
    sleep_sc = score_sleep_vars(
        sleep_raw["total_seconds"], sleep_raw["deep_seconds"],
        sleep_raw["rem_seconds"], sleep_raw["awake_count"],
        sleep_raw["garmin_sleep_score"],
    )
    rd_sc = score_readiness_vars(readiness_raw["score"])
    result["dimension_scores"] = {"hrv": hrv, "rhr": rhr_sc, "sleep": sleep_sc, "readiness": rd_sc}

    # 综合恢复
    recovery = compute_recovery(hrv["score"], sleep_sc["score"], rhr_sc["score"], rd_sc["score"])
    result["composite"] = recovery

    # 多维验证
    hrv_pct = hrv.get("pct_change_pct") or 0
    rhr_dev = rhr_sc["deviation"]
    sleep_h = sleep_raw["total_seconds"] / 3600 if sleep_raw["total_seconds"] else 0
    awake_cnt = sleep_raw["awake_count"]
    deep_pct = (sleep_raw["deep_seconds"] / sleep_raw["total_seconds"] * 100 if sleep_raw["total_seconds"] > 0 else 0)
    result["multi_dimension_validation"] = cross_dimension_validation(hrv_pct, rhr_dev, sleep_h, awake_cnt, deep_pct)

    result["derived_metrics_summary"] = {
        "hrv_pct_change": hrv.get("pct_change_pct"),
        "hrv_ln_change": hrv.get("pct_change"),
        "rhr_deviation_bpm": rhr_dev,
        "sleep_total_hours": round(sleep_h, 2) if sleep_h else 0,
        "sleep_deep_pct": round(deep_pct, 2) if deep_pct else 0,
        "sleep_rem_pct": round(sleep_raw["rem_seconds"] / sleep_raw["total_seconds"] * 100, 2) if sleep_raw["total_seconds"] > 0 else 0,
        "acwr_percent": profile.get("acwr_percent", 0) if isinstance(profile.get("acwr_percent"), (int, float)) else 0,
        "readiness_score_original": readiness_raw["score"],
    }

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Compute KPIs from Garmin API + DB baseline")
    parser.add_argument("--date", "-d", type=str, help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file path")
    parser.add_argument("--no-api", action="store_true", help="跳过 API 查询，直接使用数据库")
    args = parser.parse_args()

    today = date.today()
    target_date = args.date or today.strftime("%Y-%m-%d")

    print(f"🏃 Garmin Agent KPI v4 — 计算 {target_date} 的 KPI 指标\n")

    data = None

    # 第一步：尝试 Garmin API 获取今日数据
    if not args.no_api:
        print("📡 [Step 1] 尝试 Garmin API 实时查询...")
        try:
            from garmin_agent.client import GarminClient
            client = GarminClient()
            if client.connect():
                api_data = fetch_from_api(target_date, client)
                if api_data["has_data"]:
                    print(f"  ✅ API 返回了有效数据")
                    data = api_data
                    data["data_date"] = target_date
                else:
                    print(f"  ⚠️  API 返回空数据（设备未同步）")
                    data = api_data  # api_empty
            else:
                print(f"  ❌ Garmin 连接失败")
                data = {"source": "api_empty", "has_data": False}
        except Exception as e:
            print(f"  ❌ API 异常: {e}")
            data = {"source": "api_empty", "has_data": False}
    else:
        data = {"source": "api_empty", "has_data": False}

    # 第二步：如果 API 无数据，回退到本地数据
    needs_db = not data.get("has_data", False)
    if needs_db:
        print("\n📁 [Step 2] 回退到本地数据...")
        db_data = fetch_from_db(args.date)
        if db_data:
            print(f"  ✅ 使用本地数据 {db_data['data_date']}")
            data["db_fallback"] = db_data
            data["history"] = db_data["history"]
            data["profile"] = db_data["profile"]
            data["data_date"] = db_data["data_date"]
            data["latest_db_date"] = db_data["latest_db_date"]
            data["hrv_raw"] = db_data["hrv_raw"]
            data["rhr_raw"] = db_data["rhr_raw"]
            data["sleep_raw"] = db_data["sleep_raw"]
            data["readiness_raw"] = db_data["readiness_raw"]
        else:
            print("  ❌ 本地数据为空")
            result = {"error": "无可用数据源", "date": target_date}
            print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
            return 1
    else:
        # API 有数据，但需要本地数据提供历史基线
        print("\n📁 [Step 2] 从本地数据获取历史基线...")
        db_data = fetch_from_db()
        if db_data:
            data["history"] = db_data["history"]
            data["profile"] = db_data["profile"]
            data["latest_db_date"] = db_data["latest_db_date"]
            data["data_date"] = target_date
            print(f"  ✅ 基线数据来自 {db_data['latest_db_date']}")
        else:
            print(f"  ⚠️  无本地基线数据，部分评分可能不准确")
            data["history"] = {"hrv_14d": [], "rhr_28d": [], "sleep_7d": [], "readiness_7d": []}
            data["profile"] = {}

    # 第三步：计算 KPI
    print(f"\n📊 [Step 3] 计算 KPI...")
    result = compute_kpis(data, target_date)
    print(f"  ✅ 恢复评分: {result['composite']['recovery_score']} ({result['composite']['grade']})")

    # 输出
    output = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"\n📝 JSON 写入: {out_path}")
    else:
        print("\n" + "=" * 60)
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())