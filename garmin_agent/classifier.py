"""
Activity Classifier - Lightweight V2 Implementation

Classification Rules (priority order):
1. race       → event_type = 'race'
2. trail      → activity_type = 'trail_running'
3. interval   → ACTIVE laps > 5 AND RECOVERY laps > 4
4. long_run   → distance >= 15000m
5. lactate_threshold → Z3 + Z4 + Z5 > 90%
6. tempo      → Z3 + Z4 > 70%
7. easy       → Z2 + Z3 > 70%
8. mixed      → fallback

Based on: garmin-fitness-v3/src/analysis/classifier.py (100% validated)
"""


def classify_activity(
    activity_type: str = None,
    event_type: str = None,
    total_distance: float = 0,
    laps: list = None,
    hr_zones: list = None,
) -> dict:
    """Classify activity using V2 algorithm.

    Args:
        activity_type: Garmin activity type (e.g., 'running', 'trail_running')
        event_type: Garmin event type (e.g., 'race', 'uncategorized')
        total_distance: Total distance in meters
        laps: List of lap dicts with 'intensityType' field
        hr_zones: HR zone data with 'zoneNumber', 'secsInZone', 'zoneLowBoundary'

    Returns:
        Dict with 'type', 'reason', 'zone_distribution'
    """
    # Step 1: Race (highest priority)
    if event_type and event_type.lower() == 'race':
        return {'type': 'race', 'reason': 'event_type = race', 'zone_distribution': {}}

    # Step 2: Trail running
    if activity_type and activity_type.lower() == 'trail_running':
        return {'type': 'trail', 'reason': 'activity_type = trail_running', 'zone_distribution': {}}

    # Step 3: Interval (by ACTIVE and RECOVERY laps)
    if laps:
        active_count = sum(1 for lap in laps if lap.get('intensityType') == 'ACTIVE')
        recovery_count = sum(1 for lap in laps if lap.get('intensityType') == 'RECOVERY')
        if active_count > 5 and recovery_count > 4:
            return {
                'type': 'interval',
                'reason': f'ACTIVE={active_count}>5, RECOVERY={recovery_count}>4',
                'zone_distribution': {}
            }

    # Step 4: Long Run
    if total_distance >= 15000:
        return {
            'type': 'long_run',
            'reason': f'{total_distance/1000:.1f}km >= 15km',
            'zone_distribution': {}
        }

    # Step 5-7: HR Zone Classification
    if hr_zones:
        zone_dist = _calculate_zone_distribution(hr_zones)
        z2 = zone_dist.get(2, 0)
        z3 = zone_dist.get(3, 0)
        z4 = zone_dist.get(4, 0)
        z5 = zone_dist.get(5, 0)

        # Step 5: Lactate Threshold
        if z3 + z4 + z5 > 90:
            return {
                'type': 'lactate_threshold',
                'reason': f'Z3+4+5={z3+z4+z5:.1f}% > 90%',
                'zone_distribution': zone_dist
            }

        # Step 6: Tempo
        if z3 + z4 > 70:
            return {
                'type': 'tempo',
                'reason': f'Z3+4={z3+z4:.1f}% > 70%',
                'zone_distribution': zone_dist
            }

        # Step 7: Easy
        if z2 + z3 > 70:
            return {
                'type': 'easy',
                'reason': f'Z2+3={z2+z3:.1f}% > 70%',
                'zone_distribution': zone_dist
            }

        # Step 8: Mixed (fallback)
        z1 = zone_dist.get(1, 0)
        return {
            'type': 'mixed',
            'reason': f'Z1={z1:.1f}%, Z2={z2:.1f}%, Z3={z3:.1f}%, Z4={z4:.1f}%, Z5={z5:.1f}%',
            'zone_distribution': zone_dist
        }

    # No HR zone data
    return {'type': 'mixed', 'reason': 'no HR zone data', 'zone_distribution': {}}


def _calculate_zone_distribution(hr_zones: list) -> dict:
    """Calculate HR zone distribution from API data.

    Args:
        hr_zones: List of HR zone dicts with 'zoneNumber', 'secsInZone'

    Returns:
        Dict mapping zone numbers (1-5) to percentages
    """
    if not hr_zones:
        return {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0}

    zone_times = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for zone in hr_zones:
        zone_num = zone.get('zoneNumber', 0)
        secs = zone.get('secsInZone', 0)
        if zone_num and zone_num in range(1, 6):
            zone_times[zone_num] += secs or 0

    total = sum(zone_times.values())
    if total == 0:
        return {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0}

    return {z: round(zone_times[z] / total * 100, 1) for z in range(1, 6)}


# Training type descriptions
TRAINING_TYPE_NAMES = {
    'race': '赛事',
    'trail': '越野跑',
    'interval': '间歇训练',
    'long_run': '长距离跑',
    'lactate_threshold': '乳酸阈值跑',
    'tempo': '节奏跑',
    'easy': '轻松跑',
    'mixed': '混合训练',
}

TRAINING_TYPE_DESCRIPTIONS = {
    'race': '正式比赛，高强度竞技',
    'trail': '山地/野外跑步，地形多变',
    'interval': '强度重复跑，提升速度能力',
    'long_run': '耐力训练，15公里以上',
    'lactate_threshold': '高强度阈值训练，Z3+Z4+Z5>90%',
    'tempo': '乳酸阈值训练，Z3+Z4>70%',
    'easy': '低强度有氧训练，Z2+Z3>70%',
    'mixed': '多种强度组合',
}
