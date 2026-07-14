"""
Garmin CLI - Claude Code 数据获取入口

用法:
    python garmin_cli.py latest          # 最近一次活动
    python garmin_cli.py today           # 今天的活动
    python garmin_cli.py week [N]        # 最近N周(默认1)
    python garmin_cli.py activities START END  # 日期范围活动
    python garmin_cli.py detail ACTIVITY_ID    # 活动详情
    python garmin_cli.py splits ACTIVITY_ID    # 圈数据
    python garmin_cli.py classify ACTIVITY_ID  # 活动分类
    python garmin_cli.py intervals ACTIVITY_ID # 间歇分析
    python garmin_cli.py health [DATE]         # 健康数据(默认今天)
    python garmin_cli.py capacity              # 训练能力
    python garmin_cli.py status                # 训练状态
    python garmin_cli.py hr [DATE]             # 心率数据
    python garmin_cli.py rhr [DATE]            # 静息心率
    python garmin_cli.py sleep [DATE]          # 睡眠数据
    python garmin_cli.py hrv [DATE]            # HRV数据
"""

import sys
import os
import json
from pathlib import Path
from datetime import date, timedelta

# Windows encoding fix
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Setup path (one level up from scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

from garmin_agent.client import GarminClient


def format_distance(meters):
    if not meters:
        return "0km"
    return f"{meters/1000:.2f}km"


def format_duration(seconds):
    if not seconds:
        return "0:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_pace(speed):
    if not speed or speed <= 0:
        return "N/A"
    pace_min = 1000 / (speed * 60)
    m = int(pace_min)
    s = int((pace_min - m) * 60)
    return f"{m}:{s:02d}/km"


def format_activity(a):
    """Format activity dict to clean output"""
    speed = a.get("averageSpeed") or 0
    return {
        "activityId": a.get("activityId"),
        "name": a.get("activityName", ""),
        "date": (a.get("startTimeLocal") or "")[:16],
        "type": (a.get("activityType") or {}).get("typeKey", ""),
        "distance": format_distance(a.get("distance")),
        "duration": format_duration(a.get("duration")),
        "pace": format_pace(speed),
        "avgHR": a.get("averageHR"),
        "calories": a.get("calories"),
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    cmd = sys.argv[1]
    client = GarminClient()

    if not client.connect():
        print(json.dumps({"error": "Garmin连接失败"}, ensure_ascii=False))
        return 1

    try:
        if cmd == "latest":
            a = client.get_latest_activity()
            if a:
                print(json.dumps(format_activity(a), ensure_ascii=False, indent=2))
            else:
                print(json.dumps({"error": "没有活动记录"}, ensure_ascii=False))

        elif cmd == "today":
            acts = client.get_todays_activities()
            print(json.dumps([format_activity(a) for a in acts], ensure_ascii=False, indent=2))

        elif cmd == "week":
            weeks = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            acts = client.get_week_activities(weeks)
            print(json.dumps([format_activity(a) for a in acts], ensure_ascii=False, indent=2))

        elif cmd == "activities":
            if len(sys.argv) < 4:
                print("用法: garmin_cli.py activities START_DATE END_DATE")
                return 1
            start, end = sys.argv[2], sys.argv[3]
            acts = client.get_activities_by_date(start, end)
            print(json.dumps([format_activity(a) for a in acts], ensure_ascii=False, indent=2))

        elif cmd == "detail":
            aid = int(sys.argv[2])
            data = client.get_activity(aid)
            if data:
                summary = data.get("summaryDTO", {})
                speed = summary.get("averageSpeed") or 0
                result = {
                    "activityId": aid,
                    "name": summary.get("activityName", ""),
                    "date": (summary.get("startTimeLocal") or "")[:16],
                    "distance": format_distance(summary.get("distance")),
                    "duration": format_duration(summary.get("duration")),
                    "pace": format_pace(speed),
                    "avgHR": summary.get("averageHR"),
                    "maxHR": summary.get("maxHR"),
                    "calories": summary.get("calories"),
                    "avgCadence": summary.get("averageRunCadence"),
                    "strideLength": summary.get("strideLength"),
                    "verticalOscillation": summary.get("verticalOscillation"),
                    "groundContactTime": summary.get("groundContactTime"),
                    "aerobicTE": summary.get("trainingEffect"),
                    "anaerobicTE": summary.get("anaerobicTrainingEffect"),
                    "vo2max": summary.get("vO2MaxValue"),
                }
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(json.dumps({"error": f"活动 {aid} 未找到"}, ensure_ascii=False))

        elif cmd == "splits":
            aid = int(sys.argv[2])
            data = client.get_activity_splits(aid)
            if data:
                laps = data.get("lapDTOs", [])
                result = []
                for i, lap in enumerate(laps, 1):
                    speed = lap.get("averageSpeed") or 0
                    result.append({
                        "lap": i,
                        "distance": format_distance(lap.get("distance")),
                        "duration": format_duration(lap.get("duration")),
                        "pace": format_pace(speed),
                        "avgHR": lap.get("averageHR"),
                        "cadence": lap.get("averageRunCadence"),
                        "stride": lap.get("strideLength"),
                        "verticalOsc": lap.get("verticalOscillation"),
                        "gct": lap.get("groundContactTime"),
                        "intensityType": lap.get("intensityType"),
                    })
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(json.dumps({"error": f"活动 {aid} 圈数据未找到"}, ensure_ascii=False))

        elif cmd == "classify":
            aid = int(sys.argv[2]) if len(sys.argv) > 2 else None
            if aid is None:
                acts = client.get_activities(limit=1)
                if not acts:
                    print(json.dumps({"error": "没有活动"}, ensure_ascii=False))
                    return 1
                aid = acts[0].get("activityId")

            act = client.get_activity(aid)
            summary = act.get("summaryDTO", {}) if act else {}
            splits_data = client.get_activity_splits(aid)
            laps = splits_data.get("lapDTOs", []) if splits_data else []
            hr_zones_data = client.get_activity_hr_in_timezones(aid)

            from garmin_agent.classifier import classify_activity
            result = classify_activity(
                activity_type=(summary.get("activityType") or {}).get("typeKey"),
                event_type=summary.get("eventType"),
                total_distance=summary.get("distance") or 0,
                laps=laps,
                hr_zones=hr_zones_data,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == "intervals":
            aid = int(sys.argv[2])
            splits_data = client.get_activity_splits(aid)
            typed_data = client.get_activity_typed_splits(aid)

            from garmin_agent.interval_analyzer import extract_interval_segments
            segments = extract_interval_segments(splits_data, typed_data)
            print(json.dumps(segments, ensure_ascii=False, indent=2))

        elif cmd == "health":
            d = sys.argv[2] if len(sys.argv) > 2 else date.today().strftime("%Y-%m-%d")
            sleep = client.get_sleep_data(d)
            hrv = client.get_hrv_data(d)
            rhr = client.get_rhr_day(d)
            readiness = client.get_training_readiness(d)
            result = {
                "date": d,
                "sleep": sleep,
                "hrv": hrv,
                "restingHR": rhr,
                "readiness": readiness,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == "capacity":
            fitness = client.get_fitnessage_data()
            race = client.get_race_predictions()
            endurance = client.get_endurance_score()
            lactate = client.get_lactate_threshold()
            result = {
                "fitness": fitness,
                "racePredictions": race,
                "enduranceScore": endurance,
                "lactateThreshold": lactate,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == "status":
            status = client.get_training_status()
            print(json.dumps(status, ensure_ascii=False, indent=2))

        elif cmd == "hr":
            d = sys.argv[2] if len(sys.argv) > 2 else date.today().strftime("%Y-%m-%d")
            data = client.get_heart_rates(d)
            print(json.dumps(data, ensure_ascii=False, indent=2))

        elif cmd == "rhr":
            d = sys.argv[2] if len(sys.argv) > 2 else date.today().strftime("%Y-%m-%d")
            data = client.get_rhr_day(d)
            print(json.dumps(data, ensure_ascii=False, indent=2))

        elif cmd == "sleep":
            d = sys.argv[2] if len(sys.argv) > 2 else date.today().strftime("%Y-%m-%d")
            data = client.get_sleep_data(d)
            print(json.dumps(data, ensure_ascii=False, indent=2))

        elif cmd == "hrv":
            d = sys.argv[2] if len(sys.argv) > 2 else date.today().strftime("%Y-%m-%d")
            data = client.get_hrv_data(d)
            print(json.dumps(data, ensure_ascii=False, indent=2))

        else:
            print(f"未知命令: {cmd}")
            print(__doc__)
            return 1

    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
