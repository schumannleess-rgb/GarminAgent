"""
Data Formatters

Utility functions for formatting activity data for display.
Based on docs/api_fields_reference.md calculation logic.
"""

from typing import Optional


def format_distance(meters: float) -> str:
    """Convert meters to human-readable distance

    Args:
        meters: Distance in meters

    Returns:
        Formatted string like "12.0 km" or "850 m"
    """
    if meters is None:
        return "--"

    if meters >= 1000:
        km = meters / 1000
        return f"{km:.1f} km"
    else:
        return f"{meters:.0f} m"


def format_duration(seconds: float) -> str:
    """Convert seconds to human-readable duration

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "1:33:01" or "45:30"
    """
    if seconds is None:
        return "--"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_duration_minutes(seconds: float) -> str:
    """Convert seconds to minutes

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "93 分钟"
    """
    if seconds is None:
        return "--"

    minutes = int(seconds / 60)
    return f"{minutes} 分钟"


def format_pace(speed_mps: float) -> str:
    """Convert speed (m/s) to pace (min/km)

    Args:
        speed_mps: Speed in meters per second

    Returns:
        Formatted string like "7:45 /km"
    """
    if speed_mps is None or speed_mps <= 0:
        return "--"

    # m/s → min/km
    pace_min_km = 1000 / (speed_mps * 60)
    minutes = int(pace_min_km)
    seconds = int((pace_min_km - minutes) * 60)

    return f"{minutes}:{seconds:02d} /km"


def format_pace_from_min_km(pace_min_km: float) -> str:
    """Format pace from min/km value

    Args:
        pace_min_km: Pace in minutes per km

    Returns:
        Formatted string like "7:45 /km"
    """
    if pace_min_km is None:
        return "--"

    minutes = int(pace_min_km)
    seconds = int((pace_min_km - minutes) * 60)

    return f"{minutes}:{seconds:02d} /km"


def format_heart_rate(hr: float) -> str:
    """Format heart rate

    Args:
        hr: Heart rate in bpm

    Returns:
        Formatted string like "142 bpm"
    """
    if hr is None:
        return "--"

    return f"{int(hr)} bpm"


def format_calories(calories: float) -> str:
    """Format calories

    Args:
        calories: Calories in kcal

    Returns:
        Formatted string like "609 kcal"
    """
    if calories is None:
        return "--"

    return f"{int(calories)} kcal"


def format_cadence(cadence: float) -> str:
    """Format running cadence

    Args:
        cadence: Cadence in steps per minute

    Returns:
        Formatted string like "178 spm"
    """
    if cadence is None:
        return "--"

    return f"{int(cadence)} spm"


def format_date(dt_str: str) -> str:
    """Format date string for display

    Args:
        dt_str: Date string like "2026-03-21 16:05:48"

    Returns:
        Formatted string like "3月21日 16:05"
    """
    if not dt_str:
        return "--"

    try:
        # Parse "2026-03-21 16:05:48"
        dt = __import__('datetime').datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return f"{dt.month}月{dt.day}日 {dt.hour:02d}:{dt.minute:02d}"
    except:
        return dt_str


def format_gct(gct_ms: float) -> str:
    """Format ground contact time

    Args:
        gct_ms: Ground contact time in milliseconds

    Returns:
        Formatted string like "259 ms"
    """
    if gct_ms is None:
        return "--"
    return f"{int(gct_ms)} ms"


def format_vo(vo_mm: float) -> str:
    """Format vertical oscillation

    Args:
        vo_mm: Vertical oscillation in millimeters

    Returns:
        Formatted string like "6.7 cm"
    """
    if vo_mm is None:
        return "--"
    return f"{vo_mm / 10:.1f} cm"


def format_stride(stride_cm: float) -> str:
    """Format stride length

    Args:
        stride_cm: Stride length in centimeters

    Returns:
        Formatted string like "0.72 m"
    """
    if stride_cm is None:
        return "--"
    return f"{stride_cm / 100:.2f} m"


def format_running_dynamics(gct_ms: float, vo_cm: float, stride_cm: float) -> dict:
    """Format running dynamics metrics

    Args:
        gct_ms: Ground contact time in milliseconds
        vo_cm: Vertical oscillation in centimeters
        stride_cm: Stride length in centimeters

    Returns:
        Dict with formatted strings
    """
    return {
        "gct": f"{int(gct_ms)} ms" if gct_ms else "--",
        "vo": f"{vo_cm:.1f} cm" if vo_cm else "--",
        "stride": f"{stride_cm:.0f} cm" if stride_cm else "--",
    }


# ==========================================
# Additional formatters for new tools
# ==========================================

def format_split_pace(pace_sec_km: float) -> str:
    """Format pace from seconds per km

    Args:
        pace_sec_km: Pace in seconds per km

    Returns:
        Formatted string like "7:45 /km"
    """
    if pace_sec_km is None or pace_sec_km <= 0:
        return "--"
    minutes = int(pace_sec_km // 60)
    seconds = int(pace_sec_km % 60)
    return f"{minutes}:{seconds:02d} /km"


