#!/usr/bin/env python3
"""Merge morning_advisor scores with raw_inputs + history from daily_health.json."""
import json
from pathlib import Path
from datetime import date

from garmin_agent.config import DATA_DIR, OUTPUT_DIR

# Load advisor scores (computed by tested morning_advisor.py)
with open(OUTPUT_DIR / "kpi_scores.json", encoding="utf-8") as f:
    scores = json.load(f)

# Load raw data
with open(DATA_DIR / "daily_health.json", encoding="utf-8") as f:
    raw = json.load(f)
days = raw.get("days", {})
valid_dates = sorted(days.keys(), reverse=True)
target = scores["date"]
day = days.get(target, days[valid_dates[0]])

# Build history
def _filter(field, max_days):
    items = [{"date": d, "value": v[field]} for d, v in days.items()
             if isinstance(v, dict) and v.get(field) is not None]
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:max_days]

hrv_14d = _filter("hrv_last_night_avg", 14)
rhr_28d = _filter("resting_hr", 28)
sleep_28d = [{"date": d, "total_sec": int(v["sleep_seconds"]),
             "deep_sec": int(v.get("deep_sleep_seconds") or 0),
             "awake": int(v.get("awake_count") or 0)}
            for d, v in sorted(days.items(), reverse=True)[:28]
            if isinstance(v, dict) and v.get("sleep_seconds")]
rd_28d = _filter("training_readiness_score", 7)
rd_28d_full = [{"date": r["date"], "score": r["value"],
               "level": days[r["date"]].get("training_readiness_level", "")} for r in rd_28d]

history = {"hrv_14d": hrv_14d, "rhr_28d": rhr_28d, "sleep_28d": sleep_28d, "readiness_28d": rd_28d_full}

# Build raw_inputs
awake_cnt = day.get("awake_count") or 0
raw_inputs = {
    "hrv": {
        "last_night": day.get("hrv_last_night_avg") or 0,
        "weekly_avg": day.get("hrv_weekly_avg") or 0,
        "status": day.get("hrv_status") or "",
    },
    "rhr": {"current_bpm": day.get("resting_hr") or 0},
    "sleep": {
        "total_seconds": int(day.get("sleep_seconds") or 0),
        "deep_seconds": int(day.get("deep_sleep_seconds") or 0),
        "rem_seconds": int(day.get("rem_sleep_seconds") or 0),
        "awake_count": awake_cnt,
        "garmin_sleep_score": day.get("sleep_score"),
    },
    "readiness": {
        "score": day.get("training_readiness_score") or 0,
        "level": day.get("training_readiness_level") or "",
    },
    "profile": {
        "vo2max": day.get("vo2_max") or "",
        "bmi": day.get("bmi"),
        "device": "Forerunner 955 Solar",
        "training_status_phrase": day.get("training_status", "") or "RECOVERY",
        "acwr_percent": day.get("acwr_percent", 0),
        "total_steps": day.get("total_steps"),
        "total_distance_m": day.get("total_distance_m"),
        "active_calories": day.get("active_calories"),
        "avg_stress": day.get("avg_stress_level"),
        "max_stress": day.get("max_stress_level"),
        "min_hr": day.get("min_hr"), "max_hr": day.get("max_hr"),
    },
    "race_predictions": {},
    "stress_raw": {
        "avg_stress_level": day.get("avg_stress_level") or 0,
        "max_stress_level": day.get("max_stress_level") or 0,
    },
}

# Assemble final output
result = {
    "date": target,
    "generated_at": date.today().strftime("%Y-%m-%d %H:%M:%S"),
    "engine_version": "2.0",
    "design_doc": "docs/design-morning-advisor.md",
    "references_count": 24,
    "data_source": scores.get("data_source", ""),
    "latest_db_date": valid_dates[0],
    "raw_inputs": raw_inputs,
    "history": history,
    "baselines": scores["baselines"],
    "dimension_scores": scores["dimension_scores"],
    "composite": scores["composite"],
    "multi_dimension_validation": scores["multi_dimension_validation"],
    "trend": scores["trend"],
    "derived_metrics_summary": scores["derived_metrics_summary"],
}

out_path = OUTPUT_DIR / "kpi_today.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"Written: {out_path}")
print(f"\n=== 验证 ===")
print(f"  date: {result['date']}")
print(f"  recovery_score: {result['composite']['recovery_score']} ({result['composite']['grade']} {result['composite']['label']})")
print(f"  HRV: {result['dimension_scores']['hrv']['score']} ({result['dimension_scores']['hrv']['zone']})")
print(f"  RHR: {result['dimension_scores']['rhr']['score']} ({result['dimension_scores']['rhr']['zone']})")
print(f"  Sleep: {result['dimension_scores']['sleep']['score']} (garmin={result['dimension_scores']['sleep']['garmin_score_used']})")
print(f"  Readiness: {result['dimension_scores']['readiness']['score']} ({result['dimension_scores']['readiness']['zone']})")
print(f"  Stress: {result['dimension_scores']['stress']['score']} ({result['dimension_scores']['stress']['zone']})")
print(f"  history.hrv_14d: {len(history['hrv_14d'])} entries")
print(f"  history.rhr_28d: {len(history['rhr_28d'])} entries")
print(f"  history.sleep_28d: {len(history['sleep_28d'])} entries")
print(f"  history.readiness_28d: {len(history['readiness_28d'])} entries")
print(f"  raw_inputs.device: {raw_inputs['profile']['device']}")
print(f"  trend.alert: {result['trend']['alert']}")
print(f"  trend.scores: {result['trend']['recent_scores_in_window']}")
