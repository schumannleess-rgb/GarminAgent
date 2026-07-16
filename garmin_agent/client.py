"""
Garmin API Client — thin delegation to login.garmin_login.

Authentication logic lives entirely in login/garmin_login.py.
This file is a thin facade so tools/activity_tools.py don't need
to know about garmin_login or garminconnect directly.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from sys import path as _sys_path
from typing import List, Optional

# Ensure the login module is on sys.path.
_LOGIN_DIR = Path(__file__).resolve().parent.parent / "login"
if str(_LOGIN_DIR) not in _sys_path:
    _sys_path.insert(0, str(_LOGIN_DIR))

from login.garmin_login import garmin_login  # noqa: E402

logger = logging.getLogger(__name__)


class GarminClient:
    """Thin wrapper: authenticate via garmin_login, delegate API calls."""

    def __init__(
        self,
        email: str = None,
        password: str = None,
        tokenstore: str = None,
    ):
        self.email = email
        self.password = password
        # Default tokenstore: project_root/.local/tokens/ (via config)
        self.tokenstore = tokenstore or str(
            Path(__file__).resolve().parent.parent / ".local" / "tokens"
        )
        self._garmin = None
        self._authenticated = False

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Authenticate via garmin_login (handles token restore + credential login)."""
        try:
            kwargs = {"is_cn": True}
            if self.email:
                kwargs["email"] = self.email
            if self.password:
                kwargs["password"] = self.password
            kwargs["tokenstore"] = self.tokenstore

            self._garmin = garmin_login(**kwargs)
            self._authenticated = True
            logger.info(
                "Garmin authenticated: %s (%s)",
                self._garmin.display_name,
                self._garmin.full_name,
            )
            return True
        except Exception as e:
            logger.error("Garmin authentication failed: %s", e)
            self._authenticated = False
            return False

    def _ensure_connected(self):
        if not self._authenticated or self._garmin is None:
            raise RuntimeError("Not connected. Call connect() first.")

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    # ------------------------------------------------------------------
    # Activity APIs
    # ------------------------------------------------------------------

    def get_activities(self, limit: int = 10, start: int = 0) -> List[dict]:
        """Recent activities, paginated."""
        self._ensure_connected()
        return self._garmin.get_activities(start=start, limit=limit)

    def get_activities_by_date(
        self,
        start_date: str | date,
        end_date: str | date,
        activity_type: str = "running",
    ) -> List[dict]:
        """Activities within a date range."""
        self._ensure_connected()
        if isinstance(start_date, date):
            start_date = start_date.isoformat()
        if isinstance(end_date, date):
            end_date = end_date.isoformat()
        return self._garmin.get_activities_by_date(start_date, end_date, activity_type)

    def get_activity(self, activity_id: int) -> dict:
        """Single activity detail."""
        self._ensure_connected()
        return self._garmin.get_activity(activity_id)

    def get_activity_splits(self, activity_id: int) -> dict:
        self._ensure_connected()
        return self._garmin.get_activity_splits(activity_id)

    def get_activity_typed_splits(self, activity_id: int) -> dict:
        self._ensure_connected()
        return self._garmin.get_activity_typed_splits(activity_id)

    def get_activity_split_summaries(self, activity_id: int) -> dict:
        self._ensure_connected()
        return self._garmin.get_activity_split_summaries(activity_id)

    def get_activity_details(self, activity_id: int) -> dict:
        self._ensure_connected()
        return self._garmin.get_activity_details(activity_id)

    def get_activity_hr_in_timezones(self, activity_id: int) -> dict:
        self._ensure_connected()
        return self._garmin.get_activity_hr_in_timezones(activity_id)

    def get_activity_power_in_timezones(self, activity_id: int) -> dict:
        self._ensure_connected()
        return self._garmin.get_activity_power_in_timezones(activity_id)

    def get_activity_exercise_sets(self, activity_id: int) -> dict:
        self._ensure_connected()
        return self._garmin.get_activity_exercise_sets(activity_id)

    def get_activity_weather(self, activity_id: int) -> dict:
        self._ensure_connected()
        return self._garmin.get_activity_weather(activity_id)

    def get_activities_fordate(self, date_str: str = None) -> List[dict]:
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().isoformat()
        return self._garmin.get_activities_fordate(date_str)

    # ------------------------------------------------------------------
    # Health & Recovery APIs
    # ------------------------------------------------------------------

    def get_sleep_data(self, date_str: str = None) -> dict:
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().isoformat()
        return self._garmin.get_sleep_data(date_str)

    def get_heart_rates(self, date_str: str = None) -> dict:
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().isoformat()
        return self._garmin.get_heart_rates(date_str)

    def get_rhr_day(self, date_str: str = None) -> dict:
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().isoformat()
        return self._garmin.get_rhr_day(date_str)

    def get_hrv_data(self, date_str: str = None) -> dict:
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().isoformat()
        return self._garmin.get_hrv_data(date_str)

    def get_training_readiness(self, date_str: str = None):
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().isoformat()
        return self._garmin.get_training_readiness(date_str)

    def get_stress_data(self, date_str: str = None):
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().isoformat()
        return self._garmin.get_stress_data(date_str)

    # ------------------------------------------------------------------
    # Training & Fitness APIs
    # ------------------------------------------------------------------

    def get_training_status(self, date_str: str = None) -> dict:
        self._ensure_connected()
        if date_str is None:
            date_str = date.today().isoformat()
        return self._garmin.get_training_status(date_str)

    def get_fitnessage_data(self) -> dict:
        self._ensure_connected()
        return self._garmin.get_fitnessage_data(date.today().isoformat())

    def get_race_predictions(self) -> dict:
        self._ensure_connected()
        return self._garmin.get_race_predictions()

    def get_endurance_score(self) -> dict:
        self._ensure_connected()
        return self._garmin.get_endurance_score()

    def get_lactate_threshold(self) -> dict:
        self._ensure_connected()
        return self._garmin.get_lactate_threshold()

    def get_hill_score(self, date_str: str = None) -> dict:
        """Hill score — with or without a date."""
        self._ensure_connected()
        if date_str is not None:
            return self._garmin.get_hill_score(date_str)
        return self._garmin.get_hill_score()

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def get_latest_activity(self) -> Optional[dict]:
        activities = self.get_activities(limit=1)
        return activities[0] if activities else None

    def get_todays_activities(self) -> List[dict]:
        return self.get_activities_by_date(date.today(), date.today())

    def get_week_activities(self, weeks: int = 1) -> List[dict]:
        end = date.today()
        start = end - timedelta(weeks=weeks)
        return self.get_activities_by_date(start, end)
