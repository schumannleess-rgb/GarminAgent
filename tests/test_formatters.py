"""Layer 1: Unit tests for formatters.py — pure functions, no external dependencies."""

from garmin_agent.formatters import (
    format_distance,
    format_duration,
    format_duration_minutes,
    format_pace,
    format_pace_from_min_km,
    format_heart_rate,
    format_calories,
    format_cadence,
    format_date,
    format_gct,
    format_vo,
    format_stride,
    format_split_pace,
)


class TestFormatDistance:
    def test_km(self):
        assert format_distance(5200) == "5.2 km"

    def test_meters(self):
        assert format_distance(850) == "850 m"

    def test_zero(self):
        assert format_distance(0) == "0 m"

    def test_none(self):
        assert format_distance(None) == "--"

    def test_exactly_1km(self):
        assert format_distance(1000) == "1.0 km"


class TestFormatDuration:
    def test_hours(self):
        assert format_duration(5581) == "1:33:01"

    def test_minutes_only(self):
        assert format_duration(2730) == "45:30"

    def test_zero(self):
        assert format_duration(0) == "0:00"

    def test_none(self):
        assert format_duration(None) == "--"


class TestFormatDurationMinutes:
    def test_normal(self):
        assert format_duration_minutes(5400) == "90 分钟"

    def test_none(self):
        assert format_duration_minutes(None) == "--"


class TestFormatPace:
    def test_normal(self):
        # 2.796 m/s → ~5:57/km
        result = format_pace(2.796)
        assert "/km" in result
        assert result == "5:57 /km"

    def test_fast(self):
        # 4.17 m/s → 3:59/km (1000/4.17/60 = 3.997 min)
        assert format_pace(4.17) == "3:59 /km"

    def test_zero(self):
        assert format_pace(0) == "--"

    def test_none(self):
        assert format_pace(None) == "--"


class TestFormatPaceFromMinKm:
    def test_normal(self):
        assert format_pace_from_min_km(5.95) == "5:57 /km"

    def test_none(self):
        assert format_pace_from_min_km(None) == "--"


class TestFormatHeartRate:
    def test_normal(self):
        assert format_heart_rate(148) == "148 bpm"

    def test_none(self):
        assert format_heart_rate(None) == "--"


class TestFormatCalories:
    def test_normal(self):
        assert format_calories(420) == "420 kcal"

    def test_none(self):
        assert format_calories(None) == "--"


class TestFormatCadence:
    def test_normal(self):
        assert format_cadence(176) == "176 spm"

    def test_none(self):
        assert format_cadence(None) == "--"


class TestFormatDate:
    def test_normal(self):
        assert format_date("2026-05-14 07:30:00") == "5月14日 07:30"

    def test_empty(self):
        assert format_date("") == "--"


class TestFormatGCT:
    def test_normal(self):
        assert format_gct(245) == "245 ms"

    def test_none(self):
        assert format_gct(None) == "--"


class TestFormatVO:
    def test_normal(self):
        # input is mm, output is cm
        assert format_vo(78) == "7.8 cm"

    def test_none(self):
        assert format_vo(None) == "--"


class TestFormatStride:
    def test_normal(self):
        # input is cm, output is m
        assert format_stride(120) == "1.20 m"

    def test_none(self):
        assert format_stride(None) == "--"


class TestFormatSplitPace:
    def test_normal(self):
        # 357 seconds/km = 5:57/km
        assert format_split_pace(357) == "5:57 /km"

    def test_zero(self):
        assert format_split_pace(0) == "--"

    def test_none(self):
        assert format_split_pace(None) == "--"
