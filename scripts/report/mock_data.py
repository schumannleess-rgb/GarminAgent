"""
模拟数据生成器

基于 Garmin API 真实样例值（来源：suggestion/健康数据.txt），
生成用于报表开发和 UI 调试的模拟数据。

用法:
    from mock_data import MockData
    md = MockData()
    activities = md.weekly_activities()
    health = md.daily_health()
"""

import random
from datetime import date, timedelta


class MockData:
    """基于真实样例值的模拟数据生成器"""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.today = date.today()

    # ==========================================
    # 活动数据
    # ==========================================

    def weekly_activities(self, weeks_ago: int = 0) -> list:
        """生成一周的活动数据

        模拟一周 4-5 次跑步，含不同训练类型。
        """
        base_date = self.today - timedelta(weeks=weeks_ago)
        # 本周一
        monday = base_date - timedelta(days=base_date.weekday())

        activities = []
        # 周二轻松跑
        activities.append(self._make_activity(
            monday + timedelta(days=1), "轻松跑", "running",
            distance=8200, duration=2640, avg_hr=142, max_hr=165,
            calories=520, elevation_gain=45,
            avg_cadence=178, avg_stride=108, avg_gct=242, avg_vo=7.2,
        ))
        # 周四节奏跑
        activities.append(self._make_activity(
            monday + timedelta(days=3), "节奏跑", "running",
            distance=10500, duration=3150, avg_hr=162, max_hr=178,
            calories=710, elevation_gain=85,
            avg_cadence=182, avg_stride=115, avg_gct=228, avg_vo=6.5,
        ))
        # 周六长距离
        activities.append(self._make_activity(
            monday + timedelta(days=5), "长距离跑", "running",
            distance=18200, duration=6300, avg_hr=148, max_hr=172,
            calories=1180, elevation_gain=210,
            avg_cadence=176, avg_stride=110, avg_gct=238, avg_vo=6.8,
        ))
        # 周日恢复跑
        activities.append(self._make_activity(
            monday + timedelta(days=6), "恢复跑", "running",
            distance=5000, duration=1800, avg_hr=132, max_hr=148,
            calories=310, elevation_gain=20,
            avg_cadence=174, avg_stride=102, avg_gct=255, avg_vo=7.8,
        ))

        return activities

    def monthly_activities(self, months_ago: int = 0) -> list:
        """生成一个月的活动数据（约 16-20 次）"""
        base_month = self.today.replace(day=1) - timedelta(days=30 * months_ago)
        monday = base_month - timedelta(days=base_month.weekday())

        activities = []
        for week in range(4):
            week_acts = self.weekly_activities(weeks_ago=weeks_ago_from(base_month, monday, week))
            activities.extend(week_acts)
        return activities

    def single_run(self, run_type: str = "easy") -> dict:
        """生成单次跑步数据"""
        templates = {
            "easy": {
                "name": "轻松跑", "type": "running",
                "distance": 8200, "duration": 2640, "avg_hr": 142, "max_hr": 165,
                "calories": 520, "elevation_gain": 45,
            },
            "tempo": {
                "name": "节奏跑", "type": "running",
                "distance": 10500, "duration": 3150, "avg_hr": 162, "max_hr": 178,
                "calories": 710, "elevation_gain": 85,
            },
            "long_run": {
                "name": "长距离跑", "type": "running",
                "distance": 21100, "duration": 7200, "avg_hr": 150, "max_hr": 175,
                "calories": 1380, "elevation_gain": 320,
            },
            "interval": {
                "name": "间歇训练", "type": "running",
                "distance": 8000, "duration": 2400, "avg_hr": 168, "max_hr": 185,
                "calories": 650, "elevation_gain": 30,
            },
        }
        t = templates.get(run_type, templates["easy"])
        return self._make_activity(
            self.today - timedelta(hours=3), t["name"], t["type"],
            t["distance"], t["duration"], t["avg_hr"], t["max_hr"],
            t["calories"], t["elevation_gain"],
        )

    def activity_splits(self, distance: int = 10000, duration: int = 3000) -> list:
        """生成每公里圈数据"""
        km_count = distance // 1000
        avg_pace = duration / (distance / 1000)  # 秒/公里
        splits = []
        for i in range(km_count):
            # 模拟配速波动
            pace_var = random.uniform(-15, 20)  # ±15-20秒波动
            lap_pace = avg_pace + pace_var
            lap_distance = 1000
            lap_duration = lap_pace
            speed = lap_distance / lap_duration  # m/s

            splits.append({
                "lapIndex": i + 1,
                "distance": lap_distance,
                "duration": lap_duration,
                "averageSpeed": speed,
                "averageHR": int(random.gauss(150, 8)),
                "maxHR": int(random.gauss(165, 5)),
                "averageRunCadence": int(random.gauss(178, 3)),
                "strideLength": round(random.gauss(108, 5), 1),
                "groundContactTime": int(random.gauss(240, 10)),
                "verticalOscillation": round(random.gauss(7.2, 0.5), 1),
                "elevationGain": random.randint(0, 15),
                "elevationLoss": random.randint(0, 12),
                "calories": random.randint(55, 75),
            })
        return splits

    def hr_zones(self, activity_type: str = "easy") -> list:
        """生成心率区间数据（5 个区间）"""
        zone_templates = {
            "easy": [120, 1800, 2400, 600, 60],       # Z2为主
            "tempo": [60, 400, 1200, 1200, 300],       # Z3+Z4为主
            "interval": [30, 200, 600, 800, 600],      # Z4+Z5为主
            "long_run": [180, 2400, 2400, 900, 120],   # Z2+Z3为主
            "lactate_threshold": [30, 150, 800, 1500, 600],  # Z3+Z4+Z5>90%
        }
        zone_times = zone_templates.get(activity_type, zone_templates["easy"])
        boundaries = [0, 124, 134, 152, 167]  # 个性化心率阈值

        return [
            {"zoneNumber": i + 1, "secsInZone": zone_times[i], "zoneLowBoundary": boundaries[i]}
            for i in range(5)
        ]

    # ==========================================
    # 健康数据
    # ==========================================

    def daily_health(self, target_date: date = None) -> dict:
        """生成单日健康数据（基于真实样例值）"""
        if target_date is None:
            target_date = self.today

        return {
            "date": target_date.isoformat(),
            "hrv": self._mock_hrv(),
            "sleep": self._mock_sleep(),
            "training_readiness": self._mock_training_readiness(),
            "resting_hr": self._mock_rhr(),
            "training_status": self._mock_training_status(),
            "body_battery": self._mock_body_battery(),
        }

    def weekly_health(self, weeks_ago: int = 0) -> list:
        """生成 7 天健康数据"""
        base = self.today - timedelta(weeks=weeks_ago)
        monday = base - timedelta(days=base.weekday())
        return [self.daily_health(monday + timedelta(days=i)) for i in range(7)]

    def _mock_hrv(self) -> dict:
        return {
            "lastNightAvg": random.randint(38, 52),
            "weeklyAvg": 47,
            "status": "BALANCED",
            "baseline": {"low": 40, "high": 50},
        }

    def _mock_sleep(self) -> dict:
        total = random.randint(25000, 32000)
        deep = int(total * random.uniform(0.15, 0.22))
        rem = int(total * random.uniform(0.18, 0.25))
        light = total - deep - rem - random.randint(300, 600)
        return {
            "sleepTimeSeconds": total,
            "deepSleepSeconds": deep,
            "remSleepSeconds": rem,
            "lightSleepSeconds": light,
            "awakeSleepSeconds": total - deep - rem - light,
            "sleepScores": {
                "overall": {"value": random.randint(75, 95)},
                "deepPercentage": {"value": round(deep / total * 100)},
            },
        }

    def _mock_training_readiness(self) -> dict:
        score = random.randint(50, 85)
        level = "LOW" if score < 50 else "MODERATE" if score < 70 else "HIGH"
        return {"score": score, "level": level}

    def _mock_rhr(self) -> dict:
        return {"value": random.randint(48, 58)}

    def _mock_training_status(self) -> dict:
        statuses = ["PRODUCTIVE", "MAINTAINING", "RECOVERY", "DETRAINING"]
        return {
            "status": random.choice(statuses),
            "vo2max": round(random.gauss(47.8, 1.0), 1),
            "fitnessTrend": random.choice([-1, 0, 1, 2, 3]),
        }

    def _mock_body_battery(self) -> dict:
        return {
            "charged": random.randint(60, 95),
            "drained": random.randint(20, 50),
            "current_level": random.randint(40, 85),
        }

    # ==========================================
    # 辅助方法
    # ==========================================

    def _make_activity(
        self, act_date, name, activity_type,
        distance, duration, avg_hr, max_hr,
        calories, elevation_gain,
        avg_cadence=178, avg_stride=108, avg_gct=242, avg_vo=7.2,
    ) -> dict:
        """构造一个完整的活动数据字典"""
        speed = distance / duration  # m/s
        return {
            "activityId": random.randint(10000000000, 99999999999),
            "activityName": name,
            "startTimeLocal": f"{act_date.isoformat()} 07:30:00",
            "activityType": {"typeKey": activity_type},
            "eventType": {"typeKey": "training"},
            "distance": distance,
            "duration": duration,
            "movingDuration": duration - random.randint(30, 120),
            "averageSpeed": speed,
            "maxSpeed": speed * random.uniform(1.3, 1.6),
            "averageHR": avg_hr,
            "maxHR": max_hr,
            "calories": calories,
            "elevationGain": elevation_gain,
            "elevationLoss": int(elevation_gain * random.uniform(0.8, 1.0)),
            "averageRunningCadenceInStepsPerMinute": avg_cadence,
            "avgStrideLength": avg_stride,
            "avgGroundContactTime": avg_gct,
            "avgVerticalOscillation": avg_vo,
            "avgVerticalRatio": round(avg_vo / avg_stride * 100, 1),
            "avgGctBalance": round(random.gauss(50, 1), 1),
            "aerobicTrainingEffect": round(random.uniform(1.5, 3.5), 1),
            "anaerobicTrainingEffect": round(random.uniform(0.0, 2.0), 1),
            "lactateThresholdBPM": 174,
        }


def weeks_ago_from(base_date, monday, week_offset):
    """计算相对于 base_date 的周数偏移"""
    target = monday + timedelta(weeks=week_offset)
    delta = (base_date - target).days
    return max(0, delta // 7)
