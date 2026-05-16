"""
教练风格训练评估报告生成器

核心原则：模板提供结构 + 数据，Agent（LLM）承担生成工作

使用方式：
1. Agent 执行 Python 获取数据
2. Python 输出数据（JSON 格式）
3. Agent 根据数据和 SKILL.md 中的模板生成报告
"""

import json
from typing import Dict, List, Optional


def prepare_coach_evaluation_data(
    activity_data: Dict,
    health_data: Optional[Dict] = None,
    lap_data: Optional[List[Dict]] = None
) -> Dict:
    """
    准备训练评估所需的数据

    Args:
        activity_data: 活动数据（从 Garmin API 获取）
        health_data: 健康数据（睡眠、HRV、身体电量）
        lap_data: 圈数据（每圈的配速、心率）

    Returns:
        Dict: 结构化数据，可直接输出给 Agent
    """

    # Garmin API 数据在 summaryDTO 里面
    summary = activity_data.get('summaryDTO', {})

    # 准备基本信息
    result = {
        'activity': {
            'name': activity_data.get('activityName', '未知活动'),
            'date': summary.get('startTimeLocal', '未知日期'),
            'distance_km': round(summary.get('distance', 0) / 1000, 2) if summary.get('distance') else None,
            'duration': format_duration(summary.get('duration', 0)),
            'avg_pace': format_pace(summary.get('averageSpeed', 0)),
            'avg_hr': summary.get('averageHR'),
            'aerobic_effect': summary.get('trainingEffect'),
            'anaerobic_effect': summary.get('anaerobicTrainingEffect'),
            'avg_cadence': summary.get('averageRunCadence'),
            'avg_gct': summary.get('groundContactTime'),
            'avg_vo': summary.get('verticalOscillation'),
            'compliance_score': summary.get('directWorkoutComplianceScore')
        },
        'lap_distribution': {
            'excellent': 0,
            'good': 0,
            'fair': 0,
            'poor': 0,
            'total': 0,
            'avg_score': 0,
            'grade': 'N/A'
        },
        'excellent_laps': [],
        'poor_laps': [],
        'health': {
            'sleep_score': None,
            'hrv_status': None,
            'body_battery_start': None,
            'body_battery_end': None
        }
    }

    # 处理圈数据（如果有）
    if lap_data:
        scores = []
        excellent_laps = []
        poor_laps = []
        total_laps = len(lap_data)

        for i, lap in enumerate(lap_data, 1):
            # Garmin API 的评分字段
            score = lap.get('directWorkoutComplianceScore', 0)
            scores.append(score)

            lap_info = {
                'lap_number': i,
                'distance_km': round(lap.get('distance', 0) / 1000, 2) if lap.get('distance') else None,
                'pace': format_pace(lap.get('averageSpeed', 0)),  # 注意：是 averageSpeed，不是 avgSpeed
                'hr': lap.get('averageHR'),
                'score': score
            }

            if score >= 80:
                result['lap_distribution']['excellent'] += 1
                excellent_laps.append(lap_info)
            elif score >= 60:
                result['lap_distribution']['good'] += 1
            elif score >= 40:
                result['lap_distribution']['fair'] += 1
            else:
                result['lap_distribution']['poor'] += 1
                poor_laps.append(lap_info)

        result['lap_distribution']['total'] = total_laps

        if scores:
            avg_score = round(sum(scores) / len(scores), 1)
            result['lap_distribution']['avg_score'] = avg_score
            result['lap_distribution']['grade'] = get_grade(avg_score)

        result['excellent_laps'] = excellent_laps[:3]  # 最多 3 个
        result['poor_laps'] = poor_laps[:3]  # 最多 3 个

    # 处理健康数据（如果有）
    if health_data:
        result['health'] = {
            'sleep_score': health_data.get('sleepScore'),
            'hrv_status': health_data.get('hrvStatus'),
            'body_battery_start': health_data.get('bodyBatteryStart'),
            'body_battery_end': health_data.get('bodyBatteryEnd')
        }

    return result


def format_duration(seconds: float) -> str:
    """格式化时长（秒 -> MM:SS 或 HH:MM:SS）"""
    if not seconds or seconds <= 0:
        return None

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_pace(speed_mps: float) -> str:
    """格式化配速（米/秒 -> MM:SS/km）"""
    if not speed_mps or speed_mps <= 0:
        return None

    # 速度（米/秒）-> 配速（秒/公里）
    pace_seconds_per_km = 1000 / speed_mps

    # 过滤异常数据（配速 > 20:00/km 认为是异常）
    if pace_seconds_per_km > 1200:  # 20分钟
        return None

    minutes = int(pace_seconds_per_km // 60)
    seconds = int(pace_seconds_per_km % 60)

    return f"{minutes}:{seconds:02d}"


def get_grade(score: float) -> str:
    """根据评分获取等级"""
    if score >= 80:
        return '优秀 (A)'
    elif score >= 65:
        return '良好 (B)'
    elif score >= 50:
        return '一般 (C)'
    else:
        return '需改进 (D)'


# 示例：直接执行
if __name__ == "__main__":
    import sys
    sys.path.insert(0, 'modules')

    from garmin_agent.client import GarminClient

    # 连接
    client = GarminClient()
    if not client.connect():
        print(json.dumps({'error': '认证失败'}, ensure_ascii=False))
        sys.exit(1)

    # 获取最近的活动
    activities = client.get_activities(limit=1)
    if not activities:
        print(json.dumps({'error': '未找到活动'}, ensure_ascii=False))
        sys.exit(1)

    activity_id = activities[0]['activityId']

    # 获取详情
    activity = client.get_activity(activity_id)
    laps_data = client.get_activity_splits(activity_id)
    laps = laps_data.get('lapDTOs', []) if laps_data else None

    # 准备数据
    data = prepare_coach_evaluation_data(activity, health_data=None, lap_data=laps)

    # 输出 JSON
    print(json.dumps(data, ensure_ascii=False, indent=2))
