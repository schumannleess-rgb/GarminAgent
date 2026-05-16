"""Layer 1: Unit tests for interval_analyzer.py — this module was NOT validated before, priority test."""

from garmin_agent.interval_analyzer import (
    extract_interval_segments,
    format_interval_analysis,
    compare_intervals,
    _calculate_pace,
    _calculate_pace_seconds,
)


class TestCalculatePace:
    """Test speed-to-pace conversion."""

    def test_normal_speed(self):
        # 4.17 m/s → 3:59/km (1000/4.17/60 = 3.997 min)
        assert _calculate_pace(4.17) == "3:59"

    def test_slow_speed(self):
        # 2.5 m/s → 6:40/km
        assert _calculate_pace(2.5) == "6:40"

    def test_zero_speed(self):
        assert _calculate_pace(0) == "N/A"

    def test_negative_speed(self):
        assert _calculate_pace(-1) == "N/A"


class TestCalculatePaceSeconds:
    def test_normal(self):
        # 4.17 m/s → 239.8 sec/km
        result = _calculate_pace_seconds(4.17)
        assert 239 < result < 241

    def test_zero(self):
        assert _calculate_pace_seconds(0) == 0


class TestExtractIntervalSegments:
    """Test interval segment extraction from lap data."""

    def test_empty_laps(self):
        result = extract_interval_segments([])
        assert result["intervals"] == []
        assert result["recoveries"] == []

    def test_none_laps(self):
        result = extract_interval_segments(None)
        assert result["intervals"] == []
        assert result["recoveries"] == []

    def test_interval_with_recovery(self, sample_laps):
        result = extract_interval_segments(sample_laps)

        # sample_laps has 6 ACTIVE and 5 RECOVERY
        assert len(result["intervals"]) == 6
        assert len(result["recoveries"]) == 5
        assert result["stats"]["interval_count"] == 6
        assert result["stats"]["recovery_count"] == 5

    def test_stats_calculated(self, sample_laps):
        result = extract_interval_segments(sample_laps)
        stats = result["stats"]

        assert stats["interval_count"] == 6
        assert "avg_pace" in stats
        assert "best_pace" in stats
        assert "worst_pace" in stats
        assert "pace_std" in stats
        assert "avg_hr" in stats
        assert "hr_drift" in stats
        assert "fatigue_index" in stats

    def test_best_lap_identified(self, sample_laps):
        result = extract_interval_segments(sample_laps)
        stats = result["stats"]

        # Best lap should be the one with lowest pace (highest speed)
        # sample_laps ACTIVE speeds: 4.17, 4.20, 4.26, 4.13, 4.22, 4.17
        # Best = 4.26 (3rd ACTIVE lap, index 3 in active_laps, but lap index 5 in original)
        assert stats["best_lap_index"] is not None

    def test_hr_drift_calculated(self, sample_laps):
        result = extract_interval_segments(sample_laps)
        stats = result["stats"]

        # HR: 165, 168, 170, 172, 174, 176
        # drift = 176 - 165 = 11
        assert stats["hr_drift"] == 11

    def test_fatigue_index_calculated(self, sample_laps):
        result = extract_interval_segments(sample_laps)
        stats = result["stats"]

        # First pace vs last pace, positive = slowing down
        assert stats["fatigue_index"] is not None
        assert isinstance(stats["fatigue_index"], float)


class TestFormatIntervalAnalysis:
    """Test markdown formatting of interval analysis."""

    def test_no_intervals(self):
        analysis = {"intervals": [], "stats": {}}
        result = format_interval_analysis(analysis)
        assert "未检测到" in result

    def test_with_data(self, sample_laps):
        analysis = extract_interval_segments(sample_laps)
        result = format_interval_analysis(analysis, activity_name="测试间歇跑")

        assert "测试间歇跑" in result
        assert "间歇段落详情" in result
        assert "统计分析" in result
        assert "配速" in result or "km" in result

    def test_table_format(self, sample_laps):
        analysis = extract_interval_segments(sample_laps)
        result = format_interval_analysis(analysis)

        # Should contain markdown table
        assert "|" in result
        assert "组数" in result
        assert "距离" in result


class TestCompareIntervals:
    """Test cross-session interval comparison."""

    def test_need_two_sessions(self):
        result = compare_intervals([{"date": "2026-05-01", "name": "test", "analysis": {}}])
        assert "至少2次" in result

    def test_comparison_table(self, sample_laps):
        analysis1 = extract_interval_segments(sample_laps)
        # Create a slightly different second session
        modified_laps = []
        for lap in sample_laps:
            new_lap = dict(lap)
            if lap.get("intensityType") == "ACTIVE":
                new_lap["averageSpeed"] = lap["averageSpeed"] * 1.05  # 5% faster
            modified_laps.append(new_lap)
        analysis2 = extract_interval_segments(modified_laps)

        sessions = [
            {"date": "2026-05-01", "name": "间歇跑A", "analysis": analysis1},
            {"date": "2026-05-08", "name": "间歇跑B", "analysis": analysis2},
        ]
        result = compare_intervals(sessions)

        assert "横向对比" in result
        assert "间歇跑A" in result
        assert "间歇跑B" in result
        assert "进步" in result or "退步" in result or "持平" in result

    def test_empty_analyses(self):
        result = compare_intervals([])
        assert "至少2次" in result
