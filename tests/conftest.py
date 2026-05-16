"""Shared fixtures for Garmin Agent tests."""

import sys
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==========================================
# Layer 1 Fixtures (pure data)
# ==========================================

@pytest.fixture
def sample_activity():
    """A typical running activity from Garmin API."""
    return {
        "activityId": 12345678901,
        "activityName": "晨跑 5公里",
        "activityType": {"typeKey": "running"},
        "eventType": {"typeKey": "uncategorized"},
        "startTimeLocal": "2026-05-14 07:30:00",
        "summaryDTO": {
            "distance": 5200.5,
            "duration": 1860.0,
            "averageSpeed": 2.796,
            "averageHR": 148,
            "maxHR": 172,
            "calories": 420,
            "averageRunCadence": 176,
            "groundContactTime": 245,
            "verticalOscillation": 78,
            "trainingEffect": 2.8,
            "anaerobicTrainingEffect": 0.5,
        },
    }


@pytest.fixture
def sample_laps():
    """Lap data with ACTIVE/RECOVERY intervals."""
    return [
        {"intensityType": "ACTIVE", "distance": 1000, "duration": 240, "averageSpeed": 4.17, "averageHR": 165},
        {"intensityType": "RECOVERY", "distance": 400, "duration": 180, "averageSpeed": 2.22, "averageHR": 130},
        {"intensityType": "ACTIVE", "distance": 1000, "duration": 238, "averageSpeed": 4.20, "averageHR": 168},
        {"intensityType": "RECOVERY", "distance": 400, "duration": 175, "averageSpeed": 2.29, "averageHR": 132},
        {"intensityType": "ACTIVE", "distance": 1000, "duration": 235, "averageSpeed": 4.26, "averageHR": 170},
        {"intensityType": "RECOVERY", "distance": 400, "duration": 170, "averageSpeed": 2.35, "averageHR": 135},
        {"intensityType": "ACTIVE", "distance": 1000, "duration": 242, "averageSpeed": 4.13, "averageHR": 172},
        {"intensityType": "RECOVERY", "distance": 400, "duration": 185, "averageSpeed": 2.16, "averageHR": 128},
        {"intensityType": "ACTIVE", "distance": 1000, "duration": 237, "averageSpeed": 4.22, "averageHR": 174},
        {"intensityType": "RECOVERY", "distance": 400, "duration": 178, "averageSpeed": 2.25, "averageHR": 130},
        {"intensityType": "ACTIVE", "distance": 1000, "duration": 240, "averageSpeed": 4.17, "averageHR": 176},
    ]


@pytest.fixture
def sample_hr_zones():
    """Heart rate zone distribution data."""
    return [
        {"zoneNumber": 1, "secsInZone": 120},
        {"zoneNumber": 2, "secsInZone": 1800},
        {"zoneNumber": 3, "secsInZone": 600},
        {"zoneNumber": 4, "secsInZone": 300},
        {"zoneNumber": 5, "secsInZone": 60},
    ]
