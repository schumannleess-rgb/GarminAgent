"""
Garmin API Client Wrapper

Uses login/garmin_login.py for authentication (is_cn=True, auto token persistence).
"""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import date, timedelta

logger = logging.getLogger(__name__)


class GarminClient:
    """
    Garmin API 客户端

    认证方式：委托给 login/garmin_login.py
    1. 优先恢复本地 TOKEN
    2. 没有 TOKEN 时用账号密码登录
    """

    def __init__(self, email: str = None, password: str = None, tokenstore: str = None):
        """Initialize client

        Args:
            email: Garmin email (可选，如果有已存储的 TOKEN)
            password: Garmin password (仅首次登录需要)
            tokenstore: TOKEN 存储路径 (默认 ./tokens/)
        """
        self.email = email or os.getenv("GARMIN_EMAIL")
        self.password = password or os.getenv("GARMIN_PASSWORD")
        self.tokenstore = tokenstore
        self._client = None
        self._authenticated = False

    def connect(self) -> bool:
        """连接 Garmin

        委托给 login/garmin_login.py，自动处理 token 恢复和密码登录。

        Returns:
            True if successful
        """
        from login.garmin_login import garmin_login

        try:
            kwargs = {"is_cn": True}
            if self.tokenstore:
                kwargs["tokenstore"] = self.tokenstore
            if self.email:
                kwargs["email"] = self.email
            if self.password:
                kwargs["password"] = self.password

            self._client = garmin_login(**kwargs)
            self._authenticated = True
            logger.info("Connected to Garmin via login module")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def _ensure_connected(self):
        """确保已连接"""
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    # ==========================================
    # Activity Query APIs
    # ==========================================

    def get_activities(self, limit: int = 10, start: int = 0) -> List[Dict]:
        """Get recent activities"""
        self._ensure_connected()
        return self._client.get_activities(start, limit)

    def get_activities_by_date(
        self,
        start_date: str | date,
        end_date: str | date,
        activity_type: str = "running"
    ) -> List[Dict]:
        """Get activities within date range"""
        self._ensure_connected()

        if isinstance(start_date, date):
            start_date = start_date.strftime("%Y-%m-%d")
        if isinstance(end_date, date):
            end_date = end_date.strftime("%Y-%m-%d")

        return self._client.get_activities_by_date(start_date, end_date, activity_type)

    def get_activity(self, activity_id: int) -> Dict:
        """Get single activity details"""
        self._ensure_connected()
        return self._client.get_activity(activity_id)

    def get_activity_splits(self, activity_id: int) -> Dict:
        """Get activity lap/split data"""
        self._ensure_connected()
        return self._client.get_activity_splits(activity_id)

    def get_activity_split_summaries(self, activity_id: int) -> Dict:
        """Get activity split summaries"""
        self._ensure_connected()
        return self._client.get_activity_split_summaries(activity_id)

    def get_activity_typed_splits(self, activity_id: int) -> Dict:
        """Get typed splits (INTERVAL_ACTIVE, RECOVERY, etc.)"""
        self._ensure_connected()
        return self._client.get_activity_typed_splits(activity_id)

    # ==========================================
    # Training & Fitness APIs
    # ==========================================

    def get_hill_score(self, activity_id: int) -> Dict:
        """Get hill score for an activity"""
        self._ensure_connected()
        return self._client.get_hill_score(activity_id)

    def get_fitnessage_data(self) -> Dict:
        """Get fitness age data"""
        self._ensure_connected()
        return self._client.get_fitnessage_data()

    def get_training_status(self, date_str: str = None) -> Dict:
        """Get training status for a specific date"""
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().strftime("%Y-%m-%d")
        return self._client.get_training_status(date_str)

    def get_training_readiness(self, date_str: str = None) -> List[Dict]:
        """Get training readiness for a specific date (returns list)"""
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().strftime("%Y-%m-%d")
        return self._client.get_training_readiness(date_str)

    def get_race_predictions(self) -> Dict:
        """Get race predictions"""
        self._ensure_connected()
        return self._client.get_race_predictions()

    def get_endurance_score(self) -> Dict:
        """Get endurance score"""
        self._ensure_connected()
        return self._client.get_endurance_score()

    # ==========================================
    # Health & Recovery APIs
    # ==========================================

    def get_sleep_data(self, date_str: str = None) -> Dict:
        """Get sleep data for a specific date

        Args:
            date_str: Date string (YYYY-MM-DD), defaults to today
        """
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().strftime("%Y-%m-%d")
        return self._client.get_sleep_data(date_str)

    # ==========================================
    # Convenience Methods
    # ==========================================

    def get_latest_activity(self) -> Optional[Dict]:
        """Get the most recent activity"""
        activities = self.get_activities(limit=1)
        return activities[0] if activities else None

    def get_todays_activities(self) -> List[Dict]:
        """Get all activities from today"""
        today = date.today()
        return self.get_activities_by_date(today, today)

    def get_week_activities(self, weeks: int = 1) -> List[Dict]:
        """Get activities from past N weeks"""
        end = date.today()
        start = end - timedelta(weeks=weeks)
        return self.get_activities_by_date(start, end)

    # ==========================================
    # Heart Rate APIs
    # ==========================================

    def get_heart_rates(self, date_str: str = None) -> Dict:
        """Get heart rate data for a date"""
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().strftime("%Y-%m-%d")
        return self._client.get_heart_rates(date_str)

    def get_rhr_day(self, date_str: str = None) -> Dict:
        """Get resting heart rate for a date"""
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().strftime("%Y-%m-%d")
        return self._client.get_rhr_day(date_str)

    def get_hrv_data(self, date_str: str = None) -> Dict:
        """Get HRV (Heart Rate Variability) data"""
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().strftime("%Y-%m-%d")
        return self._client.get_hrv_data(date_str)

    def get_lactate_threshold(self) -> Dict:
        """Get lactate threshold (heart rate and pace)"""
        self._ensure_connected()
        return self._client.get_lactate_threshold()

    def get_activity_hr_in_timezones(self, activity_id: int) -> Dict:
        """Get heart rate distribution in time zones for an activity"""
        self._ensure_connected()
        return self._client.get_activity_hr_in_timezones(activity_id)

    def get_activity_details(self, activity_id: int) -> Dict:
        """Get second-by-second activity data (finest granularity)"""
        self._ensure_connected()
        return self._client.get_activity_details(activity_id)

    # ==========================================
    # Additional Activity APIs
    # ==========================================

    def get_activities_fordate(self, date_str: str = None) -> List[Dict]:
        """Get activities for a specific date"""
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().strftime("%Y-%m-%d")
        return self._client.get_activities_fordate(date_str)

    def get_activity_power_in_timezones(self, activity_id: int) -> Dict:
        """Get power distribution in time zones for an activity"""
        self._ensure_connected()
        return self._client.get_activity_power_in_timezones(activity_id)

    def get_activity_exercise_sets(self, activity_id: int) -> Dict:
        """Get exercise sets for strength training activities"""
        self._ensure_connected()
        return self._client.get_activity_exercise_sets(activity_id)

    # ==========================================
    # Body Composition & Device APIs
    # ==========================================

    def get_body_composition(self, start_date: str, end_date: str = None) -> Dict:
        """Get body composition data (including BMI)

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to start_date

        Returns:
            Body composition data including height, weight, BMI, etc.
        """
        self._ensure_connected()
        return self._client.get_body_composition(start_date, end_date)

    def get_daily_weigh_ins(self, date_str: str = None) -> Dict:
        """Get weigh-in data for a specific date

        Args:
            date_str: Date string (YYYY-MM-DD), defaults to today

        Returns:
            Weigh-in data including weight, BMI, body fat, etc.
        """
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().strftime("%Y-%m-%d")
        return self._client.get_daily_weigh_ins(date_str)

    def get_devices(self) -> List[Dict]:
        """Get list of Garmin devices for the current user account

        Returns:
            List of device info dictionaries (model, device_id, etc.)
        """
        self._ensure_connected()
        return self._client.get_devices()
