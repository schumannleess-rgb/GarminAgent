"""Layer 1: Unit tests for coach_evaluator.py — data preparation logic."""

from garmin_agent.coach_evaluator import (
    prepare_coach_evaluation_data,
    format_duration,
    format_pace,
    get_grade,
)


class TestPrepareCoachEvaluationData:
    """Test data extraction from Garmin API response."""

    def test_basic_activity_data(self, sample_activity):
        result = prepare_coach_evaluation_data(sample_activity)

        assert result["activity"]["name"] == "晨跑 5公里"
        assert result["activity"]["distance_km"] == 5.2
        assert result["activity"]["avg_hr"] == 148
        assert result["activity"]["aerobic_effect"] == 2.8

    def test_with_lap_data(self, sample_activity):
        laps = [
            {"distance": 1000, "averageSpeed": 4.17, "averageHR": 165, "directWorkoutComplianceScore": 85},
            {"distance": 1000, "averageSpeed": 4.20, "averageHR": 168, "directWorkoutComplianceScore": 90},
            {"distance": 1000, "averageSpeed": 3.50, "averageHR": 155, "directWorkoutComplianceScore": 30},
        ]
        result = prepare_coach_evaluation_data(sample_activity, lap_data=laps)

        assert result["lap_distribution"]["total"] == 3
        assert result["lap_distribution"]["excellent"] == 2  # score >= 80
        assert result["lap_distribution"]["poor"] == 1  # score < 40
        assert len(result["excellent_laps"]) == 2
        assert len(result["poor_laps"]) == 1

    def test_with_health_data(self, sample_activity):
        health = {
            "sleepScore": 82,
            "hrvStatus": "balanced",
            "bodyBatteryStart": 65,
            "bodyBatteryEnd": 30,
        }
        result = prepare_coach_evaluation_data(sample_activity, health_data=health)

        assert result["health"]["sleep_score"] == 82
        assert result["health"]["hrv_status"] == "balanced"
        assert result["health"]["body_battery_start"] == 65

    def test_empty_activity(self):
        result = prepare_coach_evaluation_data({})
        assert result["activity"]["name"] == "未知活动"
        assert result["activity"]["distance_km"] is None

    def test_no_optional_data(self, sample_activity):
        result = prepare_coach_evaluation_data(sample_activity)
        assert result["lap_distribution"]["total"] == 0
        assert result["health"]["sleep_score"] is None


class TestFormatDuration:
    def test_hours(self):
        assert format_duration(5580) == "1:33:00"

    def test_minutes(self):
        assert format_duration(2730) == "45:30"

    def test_zero(self):
        assert format_duration(0) is None

    def test_none(self):
        assert format_duration(None) is None


class TestFormatPace:
    def test_normal(self):
        # 4.17 m/s → 3:59/km
        assert format_pace(4.17) == "3:59"

    def test_slow(self):
        # 2.5 m/s → ~6:40/km
        assert format_pace(2.5) == "6:40"

    def test_zero(self):
        assert format_pace(0) is None

    def test_none(self):
        assert format_pace(None) is None


class TestGetGrade:
    def test_excellent(self):
        assert get_grade(85) == "优秀 (A)"

    def test_good(self):
        assert get_grade(70) == "良好 (B)"

    def test_fair(self):
        assert get_grade(55) == "一般 (C)"

    def test_poor(self):
        assert get_grade(30) == "需改进 (D)"
