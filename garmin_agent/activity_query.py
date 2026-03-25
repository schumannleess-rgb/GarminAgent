"""
Activity Query Module

Provides high-level activity query functionality for the MVP.
Implements the three scenarios from docs/api_fields_reference.md.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict

from .client import GarminClient
from . import formatters

logger = logging.getLogger(__name__)


@dataclass
class ActivitySummary:
    """Summary of a single activity"""
    activity_id: int
    name: str
    date: str
    date_formatted: str
    distance: str
    distance_m: float
    duration: str
    duration_s: float
    avg_hr: Optional[int]
    calories: Optional[int]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ActivityRangeSummary:
    """Summary of activities in a date range"""
    start_date: str
    end_date: str
    total_distance: str
    total_distance_m: float
    total_duration: str
    total_duration_s: float
    activity_count: int
    total_calories: int
    activities: List[ActivitySummary]

    def to_dict(self) -> Dict:
        result = asdict(self)
        result["activities"] = [a.to_dict() for a in self.activities]
        return result


class ActivityQuery:
    """Activity Query functionality"""

    def __init__(self, client: GarminClient):
        """Initialize with Garmin client

        Args:
            client: Authenticated GarminClient instance
        """
        self.client = client

    # ==========================================
    # Scenario 1: Query Latest Activity
    # ==========================================

    def get_latest_activity(self) -> Optional[ActivitySummary]:
        """Get the most recent activity

        Usage:
            "最近一次跑步是什么时候？"
            "今天跑了多少？"

        Returns:
            ActivitySummary or None
        """
        activities = self.client.get_activities(limit=1)
        if not activities:
            return None

        return self._parse_activity(activities[0])

    # ==========================================
    # Scenario 2: Query Date Range
    # ==========================================

    def get_activities_by_range(
        self,
        start_date: str | date,
        end_date: str | date
    ) -> ActivityRangeSummary:
        """Get activities within date range

        Usage:
            "这周跑了多少？"
            "最近7天的训练情况"

        Args:
            start_date: Start date (YYYY-MM-DD or date object)
            end_date: End date (YYYY-MM-DD or date object)

        Returns:
            ActivityRangeSummary with aggregated stats
        """
        activities = self.client.get_activities_by_date(start_date, end_date)

        # Parse activities
        summaries = [self._parse_activity(a) for a in activities]

        # Calculate totals
        total_distance = sum(s.distance_m for s in summaries if s.distance_m)
        total_duration = sum(s.duration_s for s in summaries if s.duration_s)
        total_calories = sum(s.calories for s in summaries if s.calories)

        # Format dates
        if isinstance(start_date, date):
            start_str = start_date.strftime("%Y-%m-%d")
        else:
            start_str = start_date

        if isinstance(end_date, date):
            end_str = end_date.strftime("%Y-%m-%d")
        else:
            end_str = end_date

        return ActivityRangeSummary(
            start_date=start_str,
            end_date=end_str,
            total_distance=formatters.format_distance(total_distance),
            total_distance_m=total_distance,
            total_duration=formatters.format_duration_minutes(total_duration),
            total_duration_s=total_duration,
            activity_count=len(summaries),
            total_calories=total_calories,
            activities=summaries
        )

    def get_week_summary(self, weeks: int = 1) -> ActivityRangeSummary:
        """Get summary for past N weeks

        Args:
            weeks: Number of weeks to look back

        Returns:
            ActivityRangeSummary
        """
        end = date.today()
        start = end - timedelta(weeks=weeks)
        return self.get_activities_by_range(start, end)

    def get_recent_days(self, days: int = 7) -> ActivityRangeSummary:
        """Get summary for past N days

        Args:
            days: Number of days to look back

        Returns:
            ActivityRangeSummary
        """
        end = date.today()
        start = end - timedelta(days=days)
        return self.get_activities_by_range(start, end)

    # ==========================================
    # Scenario 3: Activity Details
    # ==========================================

    def get_activity_details(self, activity_id: int) -> Dict[str, Any]:
        """Get detailed activity information

        Usage:
            "575846802 这个活动详情"
            "上次的步态数据"

        Args:
            activity_id: Activity ID

        Returns:
            Dict with detailed activity data
        """
        activity = self.client.get_activity(activity_id)

        result = {
            "basic": self._parse_activity(activity),
            "pace": self._extract_pace_data(activity),
            "running_dynamics": self._extract_running_dynamics(activity),
            "training_effect": self._extract_training_effect(activity),
            "heart_rate_zones": self._extract_hr_zones(activity),
            "elevation": self._extract_elevation(activity)
        }

        return result

    def get_activity_splits(self, activity_id: int) -> List[Dict]:
        """Get lap/split data for an activity

        Args:
            activity_id: Activity ID

        Returns:
            List of lap data
        """
        splits = self.client.get_activity_splits(activity_id)

        if not splits:
            return []

        # Extract lap list
        laps = []
        if "lap" in splits:
            laps = splits["lap"]
        elif "laps" in splits:
            laps = splits["laps"]

        # Format each lap
        formatted_laps = []
        for i, lap in enumerate(laps):
            formatted_laps.append(self._format_lap(lap, i + 1))

        return formatted_laps

    # ==========================================
    # Helper Methods
    # ==========================================

    def _parse_activity(self, raw: Dict) -> ActivitySummary:
        """Parse raw activity data into ActivitySummary"""
        distance_m = raw.get("distance", 0) or 0
        duration_s = raw.get("duration", 0) or 0

        return ActivitySummary(
            activity_id=raw.get("activityId", 0),
            name=raw.get("activityName", "未命名"),
            date=raw.get("startTimeLocal", ""),
            date_formatted=formatters.format_date(raw.get("startTimeLocal", "")),
            distance=formatters.format_distance(distance_m),
            distance_m=distance_m,
            duration=formatters.format_duration(duration_s),
            duration_s=duration_s,
            avg_hr=int(raw["averageHR"]) if raw.get("averageHR") else None,
            calories=int(raw["calories"]) if raw.get("calories") else None
        )

    def _extract_pace_data(self, activity: Dict) -> Dict:
        """Extract pace/speed data"""
        avg_speed = activity.get("averageSpeed")
        max_speed = activity.get("maxSpeed")
        grade_speed = activity.get("avgGradeAdjustedSpeed")

        return {
            "avg_pace": formatters.format_pace(avg_speed),
            "max_pace": formatters.format_pace(max_speed),
            "grade_adjusted_pace": formatters.format_pace(grade_speed),
            "avg_speed_mps": avg_speed,
            "max_speed_mps": max_speed
        }

    def _extract_running_dynamics(self, activity: Dict) -> Dict:
        """Extract running dynamics data"""
        gct = activity.get("avgGroundContactTime")
        vo = activity.get("avgVerticalOscillation")
        stride = activity.get("avgStrideLength")
        cadence = activity.get("averageRunningCadenceInStepsPerMinute")

        formatted = formatters.format_running_dynamics(gct, vo, stride)

        return {
            "ground_contact_time": formatted["gct"],
            "vertical_oscillation": formatted["vo"],
            "stride_length": formatted["stride"],
            "cadence": formatters.format_cadence(cadence),
            "gct_ms": gct,
            "vo_cm": vo,
            "stride_cm": stride,
            "cadence_spm": cadence
        }

    def _extract_training_effect(self, activity: Dict) -> Dict:
        """Extract training effect data"""
        return {
            "aerobic_effect": activity.get("aerobicTrainingEffect"),
            "anaerobic_effect": activity.get("anaerobicTrainingEffect"),
            "effect_label": activity.get("trainingEffectLabel"),
            "vo2_max": activity.get("vO2MaxValue")
        }

    def _extract_hr_zones(self, activity: Dict) -> Dict:
        """Extract heart rate zone times"""
        return {
            "zone_1_sec": activity.get("hrTimeInZone_1", 0),
            "zone_2_sec": activity.get("hrTimeInZone_2", 0),
            "zone_3_sec": activity.get("hrTimeInZone_3", 0),
            "zone_4_sec": activity.get("hrTimeInZone_4", 0),
            "zone_5_sec": activity.get("hrTimeInZone_5", 0)
        }

    def _extract_elevation(self, activity: Dict) -> Dict:
        """Extract elevation data"""
        return {
            "gain_m": activity.get("elevationGain", 0),
            "loss_m": activity.get("elevationLoss", 0),
            "max_m": activity.get("maxElevation"),
            "min_m": activity.get("minElevation")
        }

    def _format_lap(self, lap: Dict, lap_num: int) -> Dict:
        """Format a single lap"""
        dist = lap.get("distance", 0) or 0
        dur = lap.get("duration", 0) or 0

        # Calculate pace
        pace_str = "--"
        if dist > 0 and dur > 0:
            pace_min_km = (dur / 60) / (dist / 1000)
            pace_str = formatters.format_pace_from_min_km(pace_min_km)

        return {
            "lap_number": lap_num,
            "distance": formatters.format_distance(dist),
            "duration": formatters.format_duration(dur),
            "pace": pace_str,
            "avg_hr": int(lap["averageHR"]) if lap.get("averageHR") else None,
            "distance_m": dist,
            "duration_s": dur
        }
