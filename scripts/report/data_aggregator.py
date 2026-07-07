"""
数据聚合层

从 GarminClient 或 mock 数据拉取原始数据，
按报表需求聚合计算，输出统一的数据结构。

用法:
    # Mock 模式
    aggregator = DataAggregator(mock=True)
    weekly = aggregator.get_weekly_data()

    # 真实数据模式
    aggregator = DataAggregator(mock=False)
    weekly = aggregator.get_weekly_data()
"""

import sys
import os
from pathlib import Path
from datetime import date, timedelta
from typing import Optional

# 设置项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mock_data import MockData
from garmin_agent.formatters import (
    format_distance, format_duration, format_pace,
    format_heart_rate, format_calories,
)


class DataAggregator:
    """数据聚合器：统一接口获取和聚合报表数据"""

    def __init__(self, mock: bool = True):
        self.mock = mock
        self._client = None
        self._mock = MockData() if mock else None

    def _get_client(self):
        """懒加载 GarminClient"""
        if self._client is None:
            from dotenv import load_dotenv
            load_dotenv(PROJECT_ROOT / ".env")
            from garmin_agent.client import GarminClient
            self._client = GarminClient()
            if not self._client.connect():
                raise RuntimeError("Garmin 连接失败")
        return self._client

    # ==========================================
    # 周报数据聚合
    # ==========================================

    def get_weekly_data(self, weeks_ago: int = 0) -> dict:
        """获取周报所需的全部数据

        Returns:
            {
                "week_start": date,
                "week_end": date,
                "summary": {...},          # 周概览
                "daily_breakdown": [...],  # 每日明细
                "hr_zones_week": {...},    # 心率区间汇总
                "health_trend": [...],     # 7天健康趋势
                "highlights": {...},       # 本周高光
                "vs_last_week": {...},     # 对比上周
                "training_types": {...},   # 训练类型分布
            }
        """
        today = date.today()
        week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks_ago)
        week_end = week_start + timedelta(days=6)

        if self.mock:
            activities = self._mock.weekly_activities(weeks_ago)
            health_data = self._mock.weekly_health(weeks_ago)
        else:
            activities = self._get_week_activities(week_start, week_end)
            health_data = self._get_week_health(week_start)

        return {
            "week_start": week_start,
            "week_end": week_end,
            "summary": self._calc_week_summary(activities),
            "daily_breakdown": self._calc_daily_breakdown(activities, week_start),
            "hr_zones_week": self._calc_hr_zones_week(activities),
            "health_trend": health_data,
            "highlights": self._calc_highlights(activities),
            "vs_last_week": self._calc_vs_last_week(weeks_ago),
            "training_types": self._calc_training_types(activities),
        }

    # ==========================================
    # 跑后报表数据聚合
    # ==========================================

    def get_post_run_data(self, activity_id: int = None) -> dict:
        """获取跑后报表所需的全部数据

        Args:
            activity_id: 活动 ID，None 时取最近一次

        Returns:
            {
                "activity": {...},         # 活动概览
                "splits": [...],           # 每公里圈数据
                "hr_zones": [...],         # 心率区间
                "health_before": {...},    # 训练前健康状态
                "history_compare": {...},  # 历史对比
                "progress": {...},         # 目标进度
            }
        """
        if self.mock:
            activity = self._mock.single_run("easy")
            activity_id = activity["activityId"]
            splits = self._mock.activity_splits(activity["distance"], activity["duration"])
            hr_zones = self._mock.hr_zones("easy")
            health = self._mock.daily_health()
        else:
            client = self._get_client()
            if activity_id is None:
                latest = client.get_latest_activity()
                activity_id = latest["activityId"]
                activity = latest
            else:
                activity = client.get_activity(activity_id)
            splits = client.get_activity_splits(activity_id).get("lapDTOs", [])
            hr_zones = client.get_activity_hr_in_timezones(activity_id)
            health = self._fetch_health_for_date(client, date.today().isoformat())

        return {
            "activity": activity,
            "splits": splits,
            "hr_zones": hr_zones,
            "health_before": health,
            "history_compare": self._calc_history_compare(activity),
            "progress": self._calc_progress(),
        }

    # ==========================================
    # Morning Call 数据聚合
    # ==========================================

    def get_morning_call_data(self) -> dict:
        """获取 Morning Call 所需的全部数据"""
        today = date.today()

        if self.mock:
            health = self._mock.daily_health()
            week_acts = self._mock.weekly_activities()
            week_health = self._mock.weekly_health()
        else:
            client = self._get_client()
            health = self._fetch_health_for_date(client, today.isoformat())
            week_acts = client.get_week_activities(1)
            week_health = [self._fetch_health_for_date(
                client, (today - timedelta(days=i)).isoformat()
            ) for i in range(7)]

        return {
            "date": today,
            "health": health,
            "week_activities": week_acts,
            "week_health_trend": week_health,
            "training_advice": self._calc_training_advice(health, week_acts),
        }

    # ==========================================
    # 月报数据聚合
    # ==========================================

    def get_monthly_data(self, months_ago: int = 0) -> dict:
        """获取月报所需的全部数据"""
        today = date.today()
        month_start = (today.replace(day=1) - timedelta(days=30 * months_ago)).replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)

        if self.mock:
            activities = self._mock.monthly_activities(months_ago)
        else:
            activities = self._get_client().get_activities_by_date(month_start, month_end)

        return {
            "month_start": month_start,
            "month_end": month_end,
            "summary": self._calc_month_summary(activities),
            "daily_breakdown": self._calc_daily_breakdown(activities, month_start, num_days=31),
            "weekly_trend": self._calc_weekly_trend(activities, month_start),
            "hr_zones_month": self._calc_hr_zones_week(activities),
            "highlights": self._calc_highlights(activities),
            "pb_records": self._calc_pb_records(activities),
        }

    # ==========================================
    # 聚合计算方法
    # ==========================================

    def _calc_week_summary(self, activities: list) -> dict:
        """计算周概览数据"""
        total_distance = sum(a.get("distance", 0) for a in activities)
        total_duration = sum(a.get("duration", 0) for a in activities)
        total_calories = sum(a.get("calories", 0) for a in activities)
        total_elevation = sum(a.get("elevationGain", 0) for a in activities)
        training_days = len(activities)

        avg_hr_list = [a["averageHR"] for a in activities if a.get("averageHR")]
        avg_hr = sum(avg_hr_list) / len(avg_hr_list) if avg_hr_list else 0

        return {
            "total_distance": total_distance,
            "total_distance_fmt": format_distance(total_distance),
            "total_duration": total_duration,
            "total_duration_fmt": format_duration(total_duration),
            "total_calories": total_calories,
            "total_calories_fmt": format_calories(total_calories),
            "total_elevation": total_elevation,
            "training_days": training_days,
            "avg_hr": int(avg_hr),
            "avg_pace": format_pace(total_distance / total_duration) if total_duration > 0 else "--",
        }

    def _calc_daily_breakdown(self, activities: list, start_date: date, num_days: int = 7) -> list:
        """计算每日明细（用于柱状图）

        Args:
            num_days: 生成几天的数据（周报=7，月报=31）
        """
        # 按日期分组
        day_map = {}
        for a in activities:
            d = a.get("startTimeLocal", "")[:10]
            if d not in day_map:
                day_map[d] = []
            day_map[d].append(a)

        result = []
        for i in range(min(num_days, 31)):
            d = start_date + timedelta(days=i)
            d_str = d.isoformat()
            acts = day_map.get(d_str, [])
            total_dist = sum(a.get("distance", 0) for a in acts)
            total_elev = sum(a.get("elevationGain", 0) for a in acts)
            result.append({
                "date": d,
                "weekday": d.strftime("%a"),
                "distance": total_dist,
                "elevation": total_elev,
                "activity_count": len(acts),
                "types": list(set(
                    a.get("activityType", {}).get("typeKey", "") for a in acts
                )),
            })
        return result

    def _calc_hr_zones_week(self, activities: list) -> dict:
        """汇总心率区间数据"""
        zone_totals = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        client = self._get_client() if not self.mock else None
        for a in activities:
            if self.mock:
                zones = self._mock.hr_zones("easy")
            else:
                aid = a.get("activityId")
                try:
                    zones = client.get_activity_hr_in_timezones(aid)
                except Exception:
                    zones = []
            for z in zones:
                zn = z.get("zoneNumber", 0)
                if zn in zone_totals:
                    zone_totals[zn] += z.get("secsInZone", 0)

        total = sum(zone_totals.values())
        return {
            "zones": zone_totals,
            "percentages": {
                z: round(zone_totals[z] / total * 100, 1) if total > 0 else 0
                for z in zone_totals
            },
            "total_seconds": total,
        }

    def _calc_highlights(self, activities: list) -> dict:
        """计算高光数据"""
        if not activities:
            return {"best_pace": None, "longest": None, "most_elevation": None}

        best_pace = max(activities, key=lambda a: a.get("averageSpeed", 0))
        longest = max(activities, key=lambda a: a.get("distance", 0))
        most_elev = max(activities, key=lambda a: a.get("elevationGain", 0))

        return {
            "best_pace": {
                "name": best_pace.get("activityName", ""),
                "distance": format_distance(best_pace.get("distance", 0)),
                "pace": format_pace(best_pace.get("averageSpeed", 0)),
                "date": best_pace.get("startTimeLocal", "")[:10],
            },
            "longest": {
                "name": longest.get("activityName", ""),
                "distance": format_distance(longest.get("distance", 0)),
                "duration": format_duration(longest.get("duration", 0)),
                "date": longest.get("startTimeLocal", "")[:10],
            },
            "most_elevation": {
                "name": most_elev.get("activityName", ""),
                "elevation": f"{most_elev.get('elevationGain', 0)}m",
                "distance": format_distance(most_elev.get("distance", 0)),
                "date": most_elev.get("startTimeLocal", "")[:10],
            },
        }

    def _calc_vs_last_week(self, current_weeks_ago: int) -> dict:
        """对比上周数据"""
        if self.mock:
            this_week = self._mock.weekly_activities(current_weeks_ago)
            last_week = self._mock.weekly_activities(current_weeks_ago + 1)
        else:
            today = date.today()
            this_start = today - timedelta(days=today.weekday()) - timedelta(weeks=current_weeks_ago)
            last_start = this_start - timedelta(weeks=1)
            client = self._get_client()
            this_week = client.get_activities_by_date(this_start, this_start + timedelta(days=6))
            last_week = client.get_activities_by_date(last_start, last_start + timedelta(days=6))

        this_dist = sum(a.get("distance", 0) for a in this_week)
        last_dist = sum(a.get("distance", 0) for a in last_week)
        this_dur = sum(a.get("duration", 0) for a in this_week)
        last_dur = sum(a.get("duration", 0) for a in last_week)

        this_avg_hr = self._avg_hr(this_week)
        last_avg_hr = self._avg_hr(last_week)

        return {
            "distance_diff": this_dist - last_dist,
            "distance_diff_fmt": f"{'+' if this_dist >= last_dist else ''}{(this_dist - last_dist)/1000:.1f} km",
            "duration_diff": this_dur - last_dur,
            "avg_hr_diff": this_avg_hr - last_avg_hr,
        }

    def _calc_training_types(self, activities: list) -> dict:
        """计算训练类型分布"""
        type_map = {}
        for a in activities:
            # 简单分类
            dist = a.get("distance", 0)
            hr = a.get("averageHR", 0)
            if dist >= 15000:
                t = "长距离跑"
            elif hr > 160:
                t = "高强度"
            elif hr < 140:
                t = "恢复跑"
            else:
                t = "轻松跑"

            if t not in type_map:
                type_map[t] = {"count": 0, "duration": 0}
            type_map[t]["count"] += 1
            type_map[t]["duration"] += a.get("duration", 0)

        return type_map

    def _calc_history_compare(self, activity: dict) -> dict:
        """与历史同类型活动对比"""
        return {
            "note": "需要真实数据支持",
            "same_type_count": 0,
            "pace_trend": [],
        }

    def _calc_progress(self) -> dict:
        """目标进度"""
        return {
            "weekly_km": 42,
            "weekly_target_km": 50,
            "monthly_km": 168,
            "monthly_target_km": 200,
        }

    def _calc_training_advice(self, health: dict, activities: list) -> dict:
        """根据健康数据计算训练建议"""
        readiness_raw = health.get("training_readiness", {})
        # 真实 API 返回列表，mock 返回字典
        if isinstance(readiness_raw, list):
            readiness = readiness_raw[0] if readiness_raw else {}
        else:
            readiness = readiness_raw
        score = readiness.get("score", 50)
        level = readiness.get("level", "MODERATE")

        hrv_raw = health.get("hrv", {})
        # 真实 API 嵌套在 hrvSummary 里
        hrv = hrv_raw.get("hrvSummary", hrv_raw) if isinstance(hrv_raw, dict) else {}
        hrv_val = hrv.get("lastNightAvg", 45)

        if score >= 70 and hrv_val >= 45:
            advice = "状态良好，可以进行正常训练或高强度训练"
            intensity = "正常训练"
        elif score >= 50:
            advice = "状态一般，建议轻松跑或恢复训练"
            intensity = "轻松跑"
        else:
            advice = "身体疲劳，建议休息或极轻松活动"
            intensity = "休息日"

        return {
            "intensity": intensity,
            "advice": advice,
            "readiness_score": score,
            "readiness_level": level,
            "hrv": hrv_val,
        }

    def _calc_month_summary(self, activities: list) -> dict:
        """月度概览"""
        return self._calc_week_summary(activities)  # 复用同一逻辑

    def _calc_weekly_trend(self, activities: list, month_start: date) -> list:
        """计算周趋势（月报用）"""
        weeks = []
        for w in range(4):
            w_start = month_start + timedelta(weeks=w)
            w_end = w_start + timedelta(days=6)
            w_acts = [
                a for a in activities
                if w_start.isoformat() <= a.get("startTimeLocal", "")[:10] <= w_end.isoformat()
            ]
            weeks.append({
                "week_num": w + 1,
                "distance": sum(a.get("distance", 0) for a in w_acts),
                "elevation": sum(a.get("elevationGain", 0) for a in w_acts),
                "count": len(w_acts),
            })
        return weeks

    def _calc_pb_records(self, activities: list) -> dict:
        """个人最佳记录"""
        return {
            "5k": {"time": "25:42", "date": "2026-03-21"},
            "10k": {"time": "53:20", "date": "2026-03-15"},
            "half_marathon": {"time": "2:01:15", "date": "2026-02-28"},
        }

    def _avg_hr(self, activities: list) -> int:
        """计算平均心率"""
        hrs = [a["averageHR"] for a in activities if a.get("averageHR")]
        return int(sum(hrs) / len(hrs)) if hrs else 0

    # ==========================================
    # 真实数据获取
    # ==========================================

    def _get_week_activities(self, start: date, end: date) -> list:
        """从 Garmin 获取一周活动"""
        client = self._get_client()
        return client.get_activities_by_date(start, end)

    def _get_week_health(self, start: date) -> list:
        """从 Garmin 获取 7 天健康数据"""
        client = self._get_client()
        result = []
        for i in range(7):
            d = (start + timedelta(days=i)).isoformat()
            try:
                result.append(self._fetch_health_for_date(client, d))
            except Exception:
                result.append({"date": d, "error": "获取失败"})
        return result

    def _fetch_health_for_date(self, client, d: str) -> dict:
        """获取单日健康数据（HRV + 睡眠 + RHR + 准备度）"""
        hrv = client.get_hrv_data(d)
        sleep = client.get_sleep_data(d)
        rhr = client.get_rhr_day(d)
        readiness = client.get_training_readiness(d)
        return {
            "date": d,
            "hrv": hrv,
            "sleep": sleep,
            "resting_hr": rhr,
            "training_readiness": readiness,
        }

    # ==========================================
    # Phase 0.3: 新增字段计算方法
    # ==========================================

    def _extract_hrv(self, health: dict) -> int:
        """从健康数据中提取 HRV 值（兼容 mock 和真实 API）"""
        hrv_raw = health.get("hrv", {})
        if isinstance(hrv_raw, dict):
            # 真实 API: hrv.hrvSummary.lastNightAvg
            val = hrv_raw.get("hrvSummary", {}).get("lastNightAvg", 0)
            if val > 0:
                return int(val)
            # Mock: hrv.lastNightAvg
            val = hrv_raw.get("lastNightAvg", 0)
            if val > 0:
                return int(val)
        elif isinstance(hrv_raw, (int, float)):
            return int(hrv_raw)
        return 0

    def _extract_rhr(self, health: dict) -> int:
        """从健康数据中提取静息心率（兼容 mock 和真实 API）"""
        rhr_raw = health.get("resting_hr", {})
        if isinstance(rhr_raw, dict):
            # 真实 API: resting_hr.allMetrics.metricsMap.WELLNESS_RESTING_HEART_RATE[0].value
            metrics = rhr_raw.get("allMetrics", {}).get("metricsMap", {})
            vals = metrics.get("WELLNESS_RESTING_HEART_RATE", [])
            if vals:
                return int(vals[0].get("value", 0))
            # Mock: resting_hr.value
            val = rhr_raw.get("value", 0)
            if val > 0:
                return int(val)
        elif isinstance(rhr_raw, (int, float)):
            return int(rhr_raw)
        return 0

    def _extract_sleep_score(self, health: dict) -> int:
        """从健康数据中提取睡眠评分（兼容 mock 和真实 API）"""
        sleep_raw = health.get("sleep", {})
        if isinstance(sleep_raw, dict):
            # 真实 API: sleep.dailySleepDTO.sleepScores.overall.value
            val = sleep_raw.get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value", 0)
            if val > 0:
                return int(val)
            # Mock: sleep.sleepScores.overall.value
            val = sleep_raw.get("sleepScores", {}).get("overall", {}).get("value", 0)
            if val > 0:
                return int(val)
        elif isinstance(sleep_raw, (int, float)):
            return int(sleep_raw)
        return 0

    def _extract_sleep_duration(self, health: dict) -> str:
        """从健康数据中提取睡眠时长（兼容 mock 和真实 API）"""
        sleep_raw = health.get("sleep", {})
        if isinstance(sleep_raw, dict):
            # 真实 API: sleep.dailySleepDTO.sleepTimeSeconds
            secs = sleep_raw.get("dailySleepDTO", {}).get("sleepTimeSeconds", 0)
            if secs == 0:
                # Mock: sleep.sleepTimeSeconds
                secs = sleep_raw.get("sleepTimeSeconds", 0)
            if secs > 0:
                h = secs // 3600
                m = (secs % 3600) // 60
                return f"{h}h{m:02d}m"
        return "--"

    def _calc_hrv_baseline(self, health_trend: list) -> int:
        """计算 HRV 7天基线"""
        hrvs = []
        for h in health_trend:
            val = self._extract_hrv(h)
            if val > 0:
                hrvs.append(val)
        return int(sum(hrvs) / len(hrvs)) if hrvs else 0

    def _calc_recovery_time(self, health: dict) -> str:
        """估算恢复时间（简化版）"""
        readiness_raw = health.get("training_readiness", {})
        if isinstance(readiness_raw, list):
            readiness_raw = readiness_raw[0] if readiness_raw else {}
        score = readiness_raw.get("score", 50)
        if score >= 80:
            return "6h"
        elif score >= 60:
            return "14h"
        elif score >= 40:
            return "24h"
        else:
            return "36h"

    def _calc_fatigue_level(self, health: dict) -> str:
        """估算疲劳程度"""
        readiness_raw = health.get("training_readiness", {})
        if isinstance(readiness_raw, list):
            readiness_raw = readiness_raw[0] if readiness_raw else {}
        score = readiness_raw.get("score", 50)
        if score >= 70:
            return "低"
        elif score >= 50:
            return "中"
        else:
            return "高"

    def _calc_hr_drift(self, splits: list) -> float:
        """计算心率漂移（简化版：前后半程 HR 差 / 平均 HR）"""
        if len(splits) < 2:
            return 0.0
        mid = len(splits) // 2
        first_half = splits[:mid]
        second_half = splits[mid:]

        hr_first = [s.get("averageHR", 0) for s in first_half if s.get("averageHR")]
        hr_second = [s.get("averageHR", 0) for s in second_half if s.get("averageHR")]

        if not hr_first or not hr_second:
            return 0.0

        avg_first = sum(hr_first) / len(hr_first)
        avg_second = sum(hr_second) / len(hr_second)
        avg_all = (avg_first + avg_second) / 2

        if avg_all == 0:
            return 0.0

        return round((avg_second - avg_first) / avg_all * 100, 1)

    def _calc_efficiency_metrics(self, activity: dict) -> dict:
        """计算效率指标"""
        return {
            "cadence": int(activity.get("averageRunningCadenceInStepsPerMinute", 0) or 0),
            "stride_length": round(activity.get("avgStrideLength", 0) or 0, 2),
            "ground_contact_time": int(activity.get("avgGroundContactTime", 0) or 0),
            "vertical_ratio": round(activity.get("avgVerticalRatio", 0) or 0, 1),
            "vertical_oscillation": round(activity.get("avgVerticalOscillation", 0) or 0, 1),
            "gct_balance": round(activity.get("avgGctBalance", 0) or 0, 1),
        }

    def _calc_vs_comparison(self, current_activities: list, days: int) -> dict:
        """计算 N 天对比"""
        today = date.today()
        current_dist = sum(a.get("distance", 0) for a in current_activities)
        current_hr = self._avg_hr(current_activities)

        if self.mock:
            past_activities = self._mock.weekly_activities()
        else:
            past_start = today - timedelta(days=days)
            past_end = today - timedelta(days=1)
            past_activities = self._get_client().get_activities_by_date(past_start, past_end)

        past_dist = sum(a.get("distance", 0) for a in past_activities)
        past_hr = self._avg_hr(past_activities)

        dist_change = ((current_dist - past_dist) / past_dist * 100) if past_dist > 0 else 0
        hr_change = ((current_hr - past_hr) / past_hr * 100) if past_hr > 0 else 0

        return {
            "pace_change_pct": round(-hr_change, 1),  # HR 下降 = 配速进步
            "efficiency_change_pct": round(dist_change * 0.3, 1),  # 简化估算
            "distance_change_pct": round(dist_change, 1),
        }

    def _calc_month_achievements(self, activities: list, weekly_trend: list) -> list:
        """计算月度核心成就"""
        achievements = []

        if weekly_trend:
            max_week = max(weekly_trend, key=lambda w: w.get("distance", 0))
            if max_week.get("distance", 0) > 0:
                achievements.append({
                    "label": "Highest Weekly Load",
                    "value": f"{max_week['distance']/1000:.1f} km",
                    "icon": "trophy",
                })

        if activities:
            max_elev = max(activities, key=lambda a: a.get("elevationGain", 0))
            if max_elev.get("elevationGain", 0) > 0:
                achievements.append({
                    "label": "New Climbing PB",
                    "value": f"{max_elev['elevationGain']}m",
                    "icon": "mountain",
                })

            max_dist = max(activities, key=lambda a: a.get("distance", 0))
            if max_dist.get("distance", 0) > 0:
                achievements.append({
                    "label": "Longest Run",
                    "value": format_distance(max_dist["distance"]),
                    "icon": "run",
                })

        return achievements[:3]

    def _calc_sleep_consistency(self, health_trend: list) -> float:
        """计算睡眠一致性（评分标准差越小越一致）"""
        scores = []
        for h in health_trend:
            s = self._extract_sleep_score(h)
            if s > 0:
                scores.append(s)
        if len(scores) < 2:
            return 100.0
        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)
        std = variance ** 0.5
        # 转换为一致性百分比（标准差越小越一致）
        consistency = max(0, 100 - std * 2)
        return round(consistency, 1)

    def _calc_recovery_stability(self, health_trend: list) -> str:
        """计算恢复稳定性"""
        hrvs = []
        for h in health_trend:
            val = self._extract_hrv(h)
            if val > 0:
                hrvs.append(val)
        if len(hrvs) < 3:
            return "stable"
        avg = sum(hrvs) / len(hrvs)
        variance = sum((h - avg) ** 2 for h in hrvs) / len(hrvs)
        cv = (variance ** 0.5) / avg if avg > 0 else 0
        return "stable" if cv < 0.1 else "volatile"

    def _calc_efficiency_growth(self, activities: list) -> dict:
        """计算效率增长（简化版：对比前半月和后半月）"""
        if len(activities) < 4:
            return {"aerobic": "+0%", "cadence": "+0%", "hr_drift": "+0%"}

        mid = len(activities) // 2
        first_half = activities[:mid]
        second_half = activities[mid:]

        # 有氧效率：配速/心率比
        def pace_hr_ratio(acts):
            dist = sum(a.get("distance", 0) for a in acts)
            dur = sum(a.get("duration", 0) for a in acts)
            hr = self._avg_hr(acts)
            if dur > 0 and hr > 0:
                return dist / dur / hr
            return 0

        ratio_first = pace_hr_ratio(first_half)
        ratio_second = pace_hr_ratio(second_half)
        aerobic_change = ((ratio_second - ratio_first) / ratio_first * 100) if ratio_first > 0 else 0

        # 步频变化
        cadence_first = [a.get("averageRunningCadenceInStepsPerMinute", 0) for a in first_half if a.get("averageRunningCadenceInStepsPerMinute")]
        cadence_second = [a.get("averageRunningCadenceInStepsPerMinute", 0) for a in second_half if a.get("averageRunningCadenceInStepsPerMinute")]
        avg_cadence_first = sum(cadence_first) / len(cadence_first) if cadence_first else 0
        avg_cadence_second = sum(cadence_second) / len(cadence_second) if cadence_second else 0
        cadence_change = ((avg_cadence_second - avg_cadence_first) / avg_cadence_first * 100) if avg_cadence_first > 0 else 0

        return {
            "aerobic": f"{'+' if aerobic_change >= 0 else ''}{aerobic_change:.1f}%",
            "cadence": f"{'+' if cadence_change >= 0 else ''}{cadence_change:.1f}%",
            "hr_drift": f"{'+' if aerobic_change >= 0 else ''}{-aerobic_change:.1f}%",
        }

    # ==========================================
    # Race Report 数据聚合
    # ==========================================

    def get_race_data(self, activity_id: int = None) -> dict:
        """获取赛事报表所需的全部数据"""
        if self.mock:
            activity = self._mock.single_run("long")
            activity_id = activity["activityId"]
            splits = self._mock.activity_splits(activity["distance"], activity["duration"])
            hr_zones = self._mock.hr_zones("hard")
        else:
            client = self._get_client()
            if activity_id is None:
                latest = client.get_latest_activity()
                activity_id = latest["activityId"]
                activity = latest
            else:
                activity = client.get_activity(activity_id)
            splits = client.get_activity_splits(activity_id).get("lapDTOs", [])
            hr_zones = client.get_activity_hr_in_timezones(activity_id)

        # 计算前后半程
        mid = len(splits) // 2
        first_half_splits = splits[:mid]
        second_half_splits = splits[mid:]
        first_half_time = sum(s.get("duration", 0) for s in first_half_splits)
        second_half_time = sum(s.get("duration", 0) for s in second_half_splits)

        # 赛事智能分析
        distance = activity.get("distance", 0)
        elevation = activity.get("elevationGain", 0)
        climbing_eff = f"{elevation/distance*1000:.0f}m/km" if distance > 0 else "--"

        return {
            "activity": activity,
            "result": {
                "distance": distance,
                "elevation": elevation,
                "finish_time": format_duration(activity.get("duration", 0)),
                "name": activity.get("activityName", "Race"),
                "date": activity.get("startTimeLocal", "")[:10],
            },
            "splits": splits,
            "hr_zones": hr_zones,
            "first_half_time": format_duration(first_half_time),
            "second_half_time": format_duration(second_half_time),
            "race_intelligence": {
                "fuel_timing": "每 45min 补给一次",
                "hr_collapse": "无明显心率崩塌" if self._avg_hr(splits) < 180 else "出现心率崩塌",
                "climbing_efficiency": climbing_eff,
                "downhill_control": "配速稳定",
            },
            "hr_drift": self._calc_hr_drift(splits),
            "km_splits": splits,
        }

    def _avg_hr(self, activities_or_splits: list) -> int:
        """计算平均心率（兼容活动列表和分段列表）"""
        hrs = []
        for item in activities_or_splits:
            hr = item.get("averageHR") or item.get("averageHeartRate")
            if hr:
                hrs.append(hr)
        return int(sum(hrs) / len(hrs)) if hrs else 0
