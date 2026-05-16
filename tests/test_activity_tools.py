"""Layer 2: Mock integration tests for activity_tools.py — mock GarminClient."""

from unittest.mock import patch, MagicMock
from datetime import date

from garmin_agent.tools.activity_tools import (
    set_client,
    get_client,
    get_latest_activity,
    get_activities_by_date,
    get_week_summary,
    search_activities,
    get_activity_detail,
    get_daily_health_summary,
    get_training_capacity,
)


class TestSetClient:
    def test_set_and_get(self):
        mock_client = MagicMock()
        # Cache is imported inside set_client, patch at source
        with patch("garmin_agent.cache_manager.ActivityClassificationCache"):
            with patch("garmin_agent.cache_sync.CacheSyncManager"):
                set_client(mock_client)
        assert get_client() is mock_client

    def test_get_before_set_raises(self):
        # Reset global state
        import garmin_agent.tools.activity_tools as mod
        mod._client = None
        try:
            get_client()
            assert False, "Should have raised"
        except RuntimeError:
            pass


class TestGetLatestActivity:
    def test_with_data(self):
        mock_client = MagicMock()
        mock_client.get_activities.return_value = [{
            "activityName": "Morning Run",
            "startTimeLocal": "2026-05-14 07:30:00",
            "distance": 5200,
            "duration": 1860,
            "averageHR": 148,
            "calories": 420,
        }]

        with patch("garmin_agent.tools.activity_tools._client", mock_client):
            result = get_latest_activity.invoke({})

        assert "Morning Run" in result
        assert "5.2 km" in result
        assert "148 bpm" in result

    def test_no_activities(self):
        mock_client = MagicMock()
        mock_client.get_activities.return_value = []

        with patch("garmin_agent.tools.activity_tools._client", mock_client):
            result = get_latest_activity.invoke({})

        assert "没有找到" in result


class TestGetActivitiesByDate:
    def test_with_results(self):
        mock_client = MagicMock()
        mock_client.get_activities_by_date.return_value = [
            {"activityName": "Run A", "startTimeLocal": "2026-05-10 08:00:00", "distance": 5000, "duration": 1800},
            {"activityName": "Run B", "startTimeLocal": "2026-05-12 07:00:00", "distance": 8000, "duration": 2880},
        ]

        with patch("garmin_agent.tools.activity_tools._client", mock_client):
            result = get_activities_by_date.invoke({"start_date": "2026-05-01", "end_date": "2026-05-14"})

        # Check for key content (avoid Chinese encoding issues in assertion)
        assert "Run A" in result
        assert "Run B" in result
        assert "13.0 km" in result or "5.0 km" in result

    def test_no_results(self):
        mock_client = MagicMock()
        mock_client.get_activities_by_date.return_value = []

        with patch("garmin_agent.tools.activity_tools._client", mock_client):
            result = get_activities_by_date.invoke({"start_date": "2026-01-01", "end_date": "2026-01-31"})

        assert "没有找到" in result


class TestGetDailyHealthSummary:
    def test_returns_health_data(self):
        mock_client = MagicMock()
        mock_client.get_sleep_data.return_value = {
            "dailySleepDTO": {
                "sleepTimeSeconds": 28800,
                "deepSleepSeconds": 7200,
                "remSleepSeconds": 5400,
                "overallSleepScore": {"value": 82},
            }
        }
        mock_client.get_hrv_data.return_value = {
            "hrvSummary": {"weeklyAvg": 45, "status": "balanced"}
        }
        mock_client.get_training_readiness.return_value = [{"score": 75, "level": "high"}]

        with patch("garmin_agent.tools.activity_tools._client", mock_client):
            result = get_daily_health_summary.invoke({})

        assert "睡眠" in result
        assert "HRV" in result
        assert "训练准备度" in result


class TestGetTrainingCapacity:
    def test_returns_capacity_data(self):
        mock_client = MagicMock()
        mock_client.get_training_status.return_value = {"status": "productive", "mostRecentVO2Max": {"generic": {"vo2MaxValue": 48}}}
        mock_client.get_fitnessage_data.return_value = {"fitnessAgeData": {"fitnessAge": 28, "vo2Max": 48}}
        mock_client.get_endurance_score.return_value = {"enduranceScore": 65}
        mock_client.get_race_predictions.return_value = {"time5K": 1200, "time10K": 2520}
        mock_client.get_lactate_threshold.return_value = {"lactateThresholdHeartRate": 172, "lactateThresholdSpeed": 4.2}

        with patch("garmin_agent.tools.activity_tools._client", mock_client):
            result = get_training_capacity.invoke({})

        assert "训练状态" in result
        assert "健身年龄" in result
        assert "耐力" in result
        assert "比赛预测" in result
        assert "乳酸阈值" in result
