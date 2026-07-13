#!/usr/bin/env python3
"""compute_all_kpis: 计算所有KPI并输出完整JSON"""
import json, sys, math, sqlite3, os
from datetime import date, timedelta
from pathlib import Path

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

def db_data(target_date=None):
    """从本地fitness_v3.db读取真实Garmin数据"""
    db_path = os.getenv("FITNESS_DB_PATH", "")
    conn = sqlite3.connect(db_path); cursor = conn.cursor()

    # Find the latest date with data
    cursor.execute("SELECT date, hrv_last_night_avg, resting_hr, sleep_score FROM daily_health ORDER BY date DESC LIMIT 1")
    latest = cursor.fetchone()
    if not latest:
        conn.close(); return None

    target = target_date or latest[0]
    print(f"[db] Using data from {target} (latest available: {latest[0]})")

    # Get target date entry
    cursor.execute(f'SELECT * FROM daily_health WHERE date = ?', (target,))
    cols = [c[0] for c in cursor.description]
    row = cursor.fetchone()
    if not row:
        cursor.execute(f'SELECT * FROM daily_health WHERE date = ?', (latest[0],))
        row = cursor.fetchone()
        target = latest[0]
    l = dict(zip(cols, row))

    # Calculate awake_count from awake_sleep_seconds (rough: each awake event ~5min)
    awake_sec = l.get('awake_sleep_seconds') or 0
    awake_cnt = min(int(awake_sec / 300), 10) if awake_sec > 0 else 0

    # Get 14d HRV history
    cursor.execute("SELECT date, hrv_last_night_avg FROM daily_health WHERE hrv_last_night_avg IS NOT NULL ORDER BY date DESC LIMIT 14")
    hrv_rows = cursor.fetchall()

    # Get 28d RHR history
    cursor.execute("SELECT date, resting_hr FROM daily_health WHERE resting_hr IS NOT NULL ORDER BY date DESC LIMIT 28")
    rhr_rows = cursor.fetchall()

    # Get 7d sleep
    cursor.execute("SELECT date, sleep_seconds, deep_sleep_seconds, sleep_score FROM daily_health ORDER BY date DESC LIMIT 7")
    sleep_rows = cursor.fetchall()

    # Get 7d readiness (use training_load as proxy)
    cursor.execute("SELECT date, training_readiness_score, training_readiness_level FROM daily_health ORDER BY date DESC LIMIT 7")
    rd_rows = cursor.fetchall()

    conn.close()

    return {
        "data_date": target,
        "latest_db_date": latest[0],
        "hrv_raw": {"last_night": l.get("hrv_last_night_avg") or 0, "weekly_avg": l.get("hrv_weekly_avg") or 0, "status": l.get("hrv_status") or ""},
        "rhr_raw": l.get("resting_hr") or 0,
        "sleep_raw": {"total_seconds": int(l.get("sleep_seconds") or 0), "deep_seconds": int(l.get("deep_sleep_seconds") or 0), "rem_seconds": int(l.get("rem_sleep_seconds") or 0), "awake_count": awake_cnt, "garmin_sleep_score": l.get("sleep_score")},
        "readiness_raw": {"score": l.get("training_readiness_score") or 0, "level": l.get("training_readiness_level") or ""},
        "history": {
            "hrv_14d": [{"date": d, "value": v} for d, v in hrv_rows if v],
            "rhr_28d": [{"date": d, "value": v} for d, v in rhr_rows if v],
            "sleep_7d": [{"date": d, "total_sec": int(t or 0), "deep_sec": int(dp or 0), "garmin_score": ss} for d, t, dp, ss in sleep_rows if t],
            "readiness_7d": [{"date": d, "score": int(sc or 0), "level": lv or ""} for d, sc, lv in rd_rows if sc]
        },
        "profile": {"vo2max": l.get("vo2_max") or "", "bmi": l.get("bmi"), "device": "Forerunner 955 Solar",
                    "fitness_age": "", "chronological_age": "",
                    "training_status_phrase": l.get("training_status") or "RECOVERY",
                    "acwr_percent": l.get("training_load") or 0,
                    "total_steps": l.get("total_steps") or 0,
                    "total_distance_m": l.get("total_distance_m") or 0,
                    "active_calories": l.get("active_kcal") or 0,
                    "avg_stress": l.get("avg_stress_level"),
                    "max_stress": l.get("max_stress_level"),
                    "min_hr": l.get("min_hr"),
                    "max_hr": l.get("max_hr"),
                    "body_battery_charged": l.get("body_battery_charged"),
                    "body_battery_drained": l.get("body_battery_drained"),
                    "avg_spo2": l.get("avg_spo2")},
        "race_predictions": {},
        "trend": {"readiness_direction": "", "readiness_last_3": []}
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Compute all KPIs from Garmin data")
    parser.add_argument("--date", "-d", type=str, help="Target date YYYY-MM-DD (default: latest available)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file path")
    args = parser.parse_args()

    today = date.today()
    result = {
        "date": today.strftime("%Y-%m-%d"),
        "generated_at": today.strftime("%Y-%m-%d %H:%M:%S"),
        "script_version": "1.0",
        "design_doc": "docs/design-morning-advisor.md",
        "references_count": 24
    }

    # Read from local database (fitness_v3.db contains the user's real Garmin data)
    data = db_data(args.date)
    if data:
        result["data_source"] = f"local_db ({data['data_date']})"
        result["latest_db_date"] = data["latest_db_date"]
    else:
        result["error"] = "本地数据库不存在或无数据"
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 1

    result["raw_inputs"] = {
        "hrv": data["hrv_raw"], "rhr": {"current_bpm": data["rhr_raw"]},
        "sleep": data["sleep_raw"], "readiness": data["readiness_raw"],
        "profile": data["profile"], "race_predictions": data["race_predictions"]
    }
    result["history"] = data["history"]

    # Baselines
    rv = [v for v in [h["value"] for h in data["history"]["hrv_14d"]] if v > 0]
    hrv_baseline_7d = round(sum(rv) / len(rv)) if rv else data["hrv_raw"]["weekly_avg"]
    rhr_vals = [h["value"] for h in data["history"]["rhr_28d"]]
    rhr_baseline_28d = round(sum(rhr_vals) / len(rhr_vals)) if rhr_vals else data["rhr_raw"]
    sleep_tots = [h["total_sec"] for h in data["history"]["sleep_7d"]]
    sleep_base_7d = round(sum(sleep_tots) / len(sleep_tots)) if sleep_tots else data["sleep_raw"]["total_seconds"]
    deep_pcts = [(h["deep_sec"] / h["total_sec"] * 100) for h in data["history"]["sleep_7d"] if h["total_sec"] > 0]
    deep_base_7d = round(sum(deep_pcts) / len(deep_pcts), 1) if deep_pcts else 0
    result["baselines"] = {
        "hrv_baseline_7d": hrv_baseline_7d, "rhr_baseline_28d": rhr_baseline_28d,
        "sleep_baseline_7d": {"total_seconds": sleep_base_7d, "total_hours": round(sleep_base_7d / 3600, 2), "deep_pct_avg": deep_base_7d},
        "formulas": {"hrv_baseline": "rolling_mean(last_7_nights_HRV), Plews 2014",
                      "rhr_baseline": "rolling_mean(last_28_days_RHR), Bosquet 2003",
                      "sleep_baseline": "rolling_mean(last_7_days_total_sleep), Ohayon 2004"}
    }

    # Scores
    hrv = score_hrv_vars(data["hrv_raw"]["last_night"] or data["hrv_raw"]["weekly_avg"], hrv_baseline_7d)
    rhr_sc = score_rhr_vars(data["rhr_raw"], rhr_baseline_28d)
    sleep_sc = score_sleep_vars(data["sleep_raw"]["total_seconds"], data["sleep_raw"]["deep_seconds"],
                                data["sleep_raw"]["rem_seconds"], data["sleep_raw"]["awake_count"],
                                data["sleep_raw"]["garmin_sleep_score"])
    rd_sc = score_readiness_vars(data["readiness_raw"]["score"])
    result["dimension_scores"] = {"hrv": hrv, "rhr": rhr_sc, "sleep": sleep_sc, "readiness": rd_sc}

    recovery = compute_recovery(hrv["score"], sleep_sc["score"], rhr_sc["score"], rd_sc["score"])
    result["composite"] = recovery

    hrv_pct = hrv.get("pct_change_pct") or 0
    rhr_dev = rhr_sc["deviation"]
    sleep_h = data["sleep_raw"]["total_seconds"] / 3600 if data["sleep_raw"]["total_seconds"] else 0
    awake_cnt = data["sleep_raw"]["awake_count"]
    deep_pct = (data["sleep_raw"]["deep_seconds"] / data["sleep_raw"]["total_seconds"] * 100 if data["sleep_raw"]["total_seconds"] > 0 else 0)
    result["multi_dimension_validation"] = cross_dimension_validation(hrv_pct, rhr_dev, sleep_h, awake_cnt, deep_pct)
    result["trend"] = data["trend"]
    result["derived_metrics_summary"] = {
        "hrv_pct_change": hrv.get("pct_change_pct"), "hrv_ln_change": hrv.get("pct_change"),
        "rhr_deviation_bpm": rhr_dev, "sleep_total_hours": round(sleep_h, 2) if sleep_h else 0,
        "sleep_deep_pct": round(deep_pct, 2) if deep_pct else 0,
        "sleep_rem_pct": round(data["sleep_raw"]["rem_seconds"] / data["sleep_raw"]["total_seconds"] * 100, 2) if data["sleep_raw"]["total_seconds"] > 0 else 0,
        "acwr_percent": data["profile"]["acwr_percent"] if isinstance(data["profile"]["acwr_percent"], (int, float)) else 0,
        "readiness_score_original": data["readiness_raw"]["score"]
    }

    output = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"JSON written to {out_path}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())