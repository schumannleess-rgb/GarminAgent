"""Write recent health data from Garmin API to fitness_v3.db"""
import sys, sqlite3, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from garmin_agent.config import FITNESS_DB_PATH
from login.garmin_login import garmin_login
from datetime import date, timedelta

DB_PATH = FITNESS_DB_PATH
client = garmin_login()
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(daily_health)")
cols = [r[1] for r in cur.fetchall()]
print(f"DB has {len(cols)} columns")

synced = 0
for days_ago in range(1, 8):
    d = (date.today() - timedelta(days=days_ago)).isoformat()

    # Check existing
    cur.execute("SELECT date FROM daily_health WHERE date = ?", (d,))
    exists = cur.fetchone() is not None

    # --- Sleep ---
    sleep_sec = deep_sec = rem_sec = light_sec = awake_sec = sleep_score = None
    try:
        sleep = client.get_sleep_data(d)
        if sleep:
            ds = sleep.get("dailySleepDTO", {}) or {}
            sleep_sec = ds.get("sleepTimeSeconds")
            deep_sec = ds.get("deepSleepSeconds")
            rem_sec = ds.get("remSleepSeconds")
            light_sec = ds.get("lightSleepSeconds")
            awake_sec = ds.get("awakeSleepSeconds")
            ss = ds.get("sleepScores", {})
            if isinstance(ss, dict):
                ov = ss.get("overall", {})
                if isinstance(ov, dict):
                    sleep_score = ov.get("value")
    except Exception as e:
        print(f"  {d} sleep error: {e}")

    # --- HRV ---
    hrv_night = hrv_weekly = hrv_status = hrv_5min = hrv_bl = hrv_bh = None
    try:
        hrv = client.get_hrv_data(d)
        if hrv:
            hs = hrv.get("hrvSummary", {}) or {}
            hrv_night = hs.get("lastNightAvg")
            hrv_weekly = hs.get("weeklyAvg")
            hrv_status = hs.get("status")
            hrv_5min = hs.get("lastNight5MinHigh")
            bl = hs.get("baseline", {}) or {}
            hrv_bl = bl.get("balancedLow")
            hrv_bh = bl.get("balancedUpper")
    except Exception as e:
        print(f"  {d} hrv error: {e}")

    # --- RHR ---
    rhr_val = None
    try:
        rhr = client.get_rhr_day(d)
        if rhr:
            mm = rhr.get("allMetrics", {}).get("metricsMap", {})
            for k, v in mm.items():
                if "RESTING" in k and v and isinstance(v, list):
                    rhr_val = v[0].get("value")
                    break
    except Exception as e:
        print(f"  {d} rhr error: {e}")

    # --- Training Readiness ---
    rd_score = rd_level = None
    try:
        tr = client.get_training_readiness(d)
        if tr and isinstance(tr, list) and len(tr) > 0:
            rd_score = tr[0].get("score") or tr[0].get("trainingReadinessScore")
            rd_level = tr[0].get("level") or tr[0].get("trainingReadinessLevel")
    except Exception as e:
        print(f"  {d} readiness error: {e}")

    # --- Stress ---
    stress_avg = stress_max = None
    try:
        stress = client.get_stress_data(d)
        if stress:
            stress_avg = stress.get("avgStressLevel")
            stress_max = stress.get("maxStressLevel")
    except Exception as e:
        print(f"  {d} stress error: {e}")

    # Build update dict
    updates = {
        "sleep_score": sleep_score,
        "sleep_seconds": sleep_sec,
        "deep_sleep_seconds": deep_sec,
        "rem_sleep_seconds": rem_sec,
        "light_sleep_seconds": light_sec,
        "awake_sleep_seconds": awake_sec,
        "sleep_hours": round(sleep_sec / 3600, 2) if sleep_sec else None,
        "deep_sleep_hours": round(deep_sec / 3600, 2) if deep_sec else None,
        "rem_sleep_hours": round(rem_sec / 3600, 2) if rem_sec else None,
        "light_sleep_hours": round(light_sec / 3600, 2) if light_sec else None,
        "awake_hours": round(awake_sec / 3600, 2) if awake_sec else None,
        "hrv_last_night_avg": hrv_night,
        "hrv_weekly_avg": hrv_weekly,
        "hrv_status": hrv_status,
        "hrv_last_night_5min_high": hrv_5min,
        "hrv_baseline_low": hrv_bl,
        "hrv_baseline_high": hrv_bh,
        "resting_hr": int(rhr_val) if rhr_val else None,
        "training_readiness_score": int(rd_score) if rd_score else None,
        "training_readiness_level": rd_level,
        "avg_stress_level": stress_avg,
        "max_stress_level": stress_max,
        "synced_at": date.today().isoformat(),
        "updated_at": date.today().isoformat(),
    }

    if exists:
        set_parts = [f"{k} = ?" for k in updates.keys()]
        vals = list(updates.values()) + [d]
        cur.execute(f"UPDATE daily_health SET {', '.join(set_parts)} WHERE date = ?", vals)
    else:
        all_cols = ["date"] + list(updates.keys())
        qmarks = ", ".join(["?"] * len(all_cols))
        vals = [d] + list(updates.values())
        cur.execute(f"INSERT INTO daily_health ({', '.join(all_cols)}) VALUES ({qmarks})", vals)

    synced += 1
    ss_mark = str(sleep_score) if sleep_score else "None"
    hrv_mark = str(hrv_night) if hrv_night else "None"
    rhr_mark = str(rhr_val) if rhr_val else "None"
    rd_mark = str(rd_score) if rd_score else "None"
    print(f"{d}: sleep={ss_mark} hrv_night={hrv_mark} rhr={rhr_mark} readiness={rd_mark}")

conn.commit()

# Summary
cur.execute("SELECT COUNT(*) FROM daily_health WHERE training_readiness_score IS NOT NULL")
print(f"\nRows with readiness_score: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM daily_health WHERE resting_hr IS NOT NULL")
print(f"Rows with resting_hr: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM daily_health WHERE sleep_score IS NOT NULL")
print(f"Rows with sleep_score: {cur.fetchone()[0]}")

cur.execute("SELECT date, sleep_score, sleep_hours, deep_sleep_hours, rem_sleep_hours, resting_hr, hrv_last_night_avg, hrv_weekly_avg, training_readiness_score, training_readiness_level FROM daily_health ORDER BY date DESC LIMIT 7")
print("\nLatest 7 rows:")
for r in cur.fetchall():
    print(f"  {r}")

conn.close()
print(f"\nDone. Synced {synced} days.")
