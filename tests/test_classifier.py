"""Layer 1: Unit tests for classifier.py — pure classification logic."""

from garmin_agent.classifier import classify_activity, _calculate_zone_distribution


class TestClassifyActivity:
    """Test all 8 classification rules in priority order."""

    def test_race(self, sample_laps, sample_hr_zones):
        result = classify_activity(
            activity_type="running",
            event_type="race",
            total_distance=10000,
            laps=sample_laps,
            hr_zones=sample_hr_zones,
        )
        assert result["type"] == "race"
        assert "race" in result["reason"]

    def test_trail(self, sample_laps, sample_hr_zones):
        result = classify_activity(
            activity_type="trail_running",
            event_type="uncategorized",
            total_distance=12000,
            laps=sample_laps,
            hr_zones=sample_hr_zones,
        )
        assert result["type"] == "trail"
        assert "trail_running" in result["reason"]

    def test_interval(self, sample_hr_zones):
        # Need >5 ACTIVE and >4 RECOVERY
        laps = [
            {"intensityType": "ACTIVE", "distance": 1000},
            {"intensityType": "RECOVERY", "distance": 400},
        ] * 6  # 6 ACTIVE + 6 RECOVERY
        result = classify_activity(
            activity_type="running",
            event_type="uncategorized",
            total_distance=10000,
            laps=laps,
            hr_zones=sample_hr_zones,
        )
        assert result["type"] == "interval"
        assert "ACTIVE" in result["reason"]

    def test_long_run(self, sample_hr_zones):
        result = classify_activity(
            activity_type="running",
            event_type="uncategorized",
            total_distance=16000,  # >=15km
            laps=[],
            hr_zones=sample_hr_zones,
        )
        assert result["type"] == "long_run"
        assert "15km" in result["reason"]

    def test_lactate_threshold(self):
        # Z3+Z4+Z5 > 90%
        hr_zones = [
            {"zoneNumber": 1, "secsInZone": 10},
            {"zoneNumber": 2, "secsInZone": 10},
            {"zoneNumber": 3, "secsInZone": 500},
            {"zoneNumber": 4, "secsInZone": 400},
            {"zoneNumber": 5, "secsInZone": 200},
        ]
        result = classify_activity(
            activity_type="running",
            event_type="uncategorized",
            total_distance=8000,
            laps=[],
            hr_zones=hr_zones,
        )
        assert result["type"] == "lactate_threshold"

    def test_tempo(self):
        # Z3+Z4 > 70%
        hr_zones = [
            {"zoneNumber": 1, "secsInZone": 10},
            {"zoneNumber": 2, "secsInZone": 100},
            {"zoneNumber": 3, "secsInZone": 500},
            {"zoneNumber": 4, "secsInZone": 400},
            {"zoneNumber": 5, "secsInZone": 10},
        ]
        result = classify_activity(
            activity_type="running",
            event_type="uncategorized",
            total_distance=8000,
            laps=[],
            hr_zones=hr_zones,
        )
        assert result["type"] == "tempo"

    def test_easy(self):
        # Z2+Z3 > 70%
        hr_zones = [
            {"zoneNumber": 1, "secsInZone": 10},
            {"zoneNumber": 2, "secsInZone": 500},
            {"zoneNumber": 3, "secsInZone": 400},
            {"zoneNumber": 4, "secsInZone": 50},
            {"zoneNumber": 5, "secsInZone": 10},
        ]
        result = classify_activity(
            activity_type="running",
            event_type="uncategorized",
            total_distance=8000,
            laps=[],
            hr_zones=hr_zones,
        )
        assert result["type"] == "easy"

    def test_mixed_fallback(self):
        # No clear dominant zone
        hr_zones = [
            {"zoneNumber": 1, "secsInZone": 200},
            {"zoneNumber": 2, "secsInZone": 200},
            {"zoneNumber": 3, "secsInZone": 200},
            {"zoneNumber": 4, "secsInZone": 200},
            {"zoneNumber": 5, "secsInZone": 200},
        ]
        result = classify_activity(
            activity_type="running",
            event_type="uncategorized",
            total_distance=8000,
            laps=[],
            hr_zones=hr_zones,
        )
        assert result["type"] == "mixed"

    def test_no_hr_data(self):
        result = classify_activity(
            activity_type="running",
            event_type="uncategorized",
            total_distance=8000,
            laps=[],
            hr_zones=None,
        )
        assert result["type"] == "mixed"


class TestCalculateZoneDistribution:
    def test_normal(self):
        zones = [
            {"zoneNumber": 1, "secsInZone": 100},
            {"zoneNumber": 2, "secsInZone": 400},
            {"zoneNumber": 3, "secsInZone": 300},
            {"zoneNumber": 4, "secsInZone": 150},
            {"zoneNumber": 5, "secsInZone": 50},
        ]
        result = _calculate_zone_distribution(zones)
        assert result[1] == 10.0
        assert result[2] == 40.0
        assert result[3] == 30.0
        assert result[4] == 15.0
        assert result[5] == 5.0

    def test_empty(self):
        result = _calculate_zone_distribution([])
        assert all(v == 0.0 for v in result.values())

    def test_none(self):
        result = _calculate_zone_distribution(None)
        assert all(v == 0.0 for v in result.values())
