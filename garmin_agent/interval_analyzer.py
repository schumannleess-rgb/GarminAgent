"""
Interval Training Analyzer - 间歇跑深度分析模块

功能：
1. 提取间歇段落数据
2. 计算配速、心率统计
3. 支持横向对比分析
4. 生成格式化输出
"""

from typing import List, Dict, Optional
from statistics import mean, stdev


def extract_interval_segments(laps: List[dict]) -> dict:
    """从圈数据中提取间歇段落。

    Args:
        laps: 活动圈数据列表

    Returns:
        {
            'warmup': [...],      # 热身段落
            'intervals': [...],   # 间歇主段落
            'recoveries': [...],  # 恢复段落
            'cooldown': [...],    # 冷身段落
            'stats': {...}        # 统计数据
        }
    """
    if not laps:
        return {'warmup': [], 'intervals': [], 'recoveries': [], 'cooldown': [], 'stats': {}}

    # 按强度分组
    active_laps = []
    recovery_laps = []

    for i, lap in enumerate(laps):
        intensity = lap.get('intensityType', 'ACTIVE')
        lap_data = {
            'index': i + 1,
            'distance': lap.get('distance', 0) / 1000,  # km
            'time': lap.get('duration', 0),  # seconds
            'avg_hr': lap.get('averageHR', 0),
            'max_hr': lap.get('maxHR', 0),
            'avg_speed': lap.get('averageSpeed', 0),  # m/s
            'pace': _calculate_pace(lap.get('averageSpeed', 0)),  # min/km
            'intensity': intensity
        }

        if intensity == 'ACTIVE':
            active_laps.append(lap_data)
        elif intensity == 'RECOVERY':
            recovery_laps.append(lap_data)

    # 计算统计数据
    stats = _calculate_interval_stats(active_laps, recovery_laps)

    # 识别热身和冷身（首尾的非间歇段落）
    warmup = []
    cooldown = []

    if len(active_laps) > 0 and len(laps) > len(active_laps) + len(recovery_laps):
        # 第一圈可能是热身
        first_lap = laps[0]
        if first_lap.get('intensityType') != 'ACTIVE':
            warmup.append({
                'distance': first_lap.get('totalDistance', 0) / 1000,
                'pace': _calculate_pace(first_lap.get('averageSpeed', 0))
            })

        # 最后一圈可能是冷身
        last_lap = laps[-1]
        if last_lap.get('intensityType') != 'ACTIVE':
            cooldown.append({
                'distance': last_lap.get('totalDistance', 0) / 1000,
                'pace': _calculate_pace(last_lap.get('averageSpeed', 0))
            })

    return {
        'warmup': warmup,
        'intervals': active_laps,
        'recoveries': recovery_laps,
        'cooldown': cooldown,
        'stats': stats
    }


def _calculate_pace(speed_ms: float) -> str:
    """将速度(m/s)转换为配速(min/km)字符串。"""
    if speed_ms <= 0:
        return "N/A"
    pace_min_per_km = 1000 / speed_ms / 60
    minutes = int(pace_min_per_km)
    seconds = int((pace_min_per_km - minutes) * 60)
    return f"{minutes}:{seconds:02d}"


def _calculate_pace_seconds(speed_ms: float) -> float:
    """将速度(m/s)转换为配速(秒/公里)。"""
    if speed_ms <= 0:
        return 0
    return 1000 / speed_ms


def _calculate_interval_stats(active_laps: List[dict], recovery_laps: List[dict]) -> dict:
    """计算间歇训练统计数据。"""
    if not active_laps:
        return {}

    # 提取配速数据（秒/公里）
    paces = [_calculate_pace_seconds(lap.get('avg_speed', 0)) for lap in active_laps if lap.get('avg_speed', 0) > 0]
    hrs = [lap.get('avg_hr', 0) for lap in active_laps if lap.get('avg_hr', 0) > 0]
    distances = [lap.get('distance', 0) for lap in active_laps if lap.get('distance', 0) > 0]

    stats = {
        'interval_count': len(active_laps),
        'recovery_count': len(recovery_laps),
    }

    if paces:
        stats['avg_pace'] = mean(paces)
        stats['best_pace'] = min(paces)
        stats['worst_pace'] = max(paces)
        stats['pace_std'] = stdev(paces) if len(paces) > 1 else 0

        # 最佳段落索引
        best_idx = paces.index(min(paces))
        stats['best_lap_index'] = active_laps[best_idx]['index']

    if hrs:
        stats['avg_hr'] = mean(hrs)
        stats['first_hr'] = hrs[0]
        stats['last_hr'] = hrs[-1]
        stats['hr_drift'] = hrs[-1] - hrs[0] if len(hrs) > 1 else 0

    if distances:
        stats['interval_distance'] = distances[0] if len(set(distances)) == 1 else 'variable'
        stats['total_interval_distance'] = sum(distances)

    # 计算疲劳指数（末段vs首段配速差异百分比）
    if paces and len(paces) > 1:
        first_pace = paces[0]
        last_pace = paces[-1]
        stats['fatigue_index'] = round((last_pace - first_pace) / first_pace * 100, 1)

    return stats


def format_interval_analysis(analysis: dict, activity_name: str = "") -> str:
    """格式化间歇分析结果为 Markdown。"""
    intervals = analysis.get('intervals', [])
    stats = analysis.get('stats', {})

    if not intervals:
        return "未检测到间歇训练段落。"

    lines = []
    lines.append(f"## ⚡ 间歇跑分析 - {activity_name}")
    lines.append("")

    # 训练结构
    lines.append("### 训练结构")
    warmup = analysis.get('warmup', [])
    if warmup:
        warmup_dist = warmup[0].get('distance', 0)
        warmup_pace = warmup[0].get('pace', 'N/A')
        lines.append(f"- **热身**: {warmup_dist:.2f}km @ {warmup_pace}/km")
    lines.append(f"- **主训练**: {stats.get('interval_count', 0)} × {stats.get('interval_distance', 'N/A')} 间歇")
    lines.append(f"- **恢复间歇**: {stats.get('recovery_count', 0)} 段")
    cooldown = analysis.get('cooldown', [])
    if cooldown:
        cooldown_dist = cooldown[0].get('distance', 0)
        cooldown_pace = cooldown[0].get('pace', 'N/A')
        lines.append(f"- **冷身**: {cooldown_dist:.2f}km @ {cooldown_pace}/km")
    lines.append("")

    # 间歇段落详情表
    lines.append("### 间歇段落详情")
    lines.append("")
    lines.append("| 组数 | 距离 | 时长 | 配速 | 心率 | 与均值差异 |")
    lines.append("|------|------|------|------|------|------------|")

    avg_pace = stats.get('avg_pace', 0)
    for i, lap in enumerate(intervals):
        time_str = _format_time(lap.get('time', 0))
        diff = ""
        if avg_pace > 0 and lap.get('avg_speed', 0) > 0:
            lap_pace = _calculate_pace_seconds(lap['avg_speed'])
            diff_sec = lap_pace - avg_pace
            diff = f"{'+' if diff_sec > 0 else ''}{int(diff_sec)}s"

        lines.append(f"| {i+1} | {lap['distance']:.2f}km | {time_str} | {lap['pace']}/km | {lap['avg_hr']} bpm | {diff} |")

    lines.append("")

    # 统计分析
    lines.append("### 统计分析")
    if stats.get('best_lap_index'):
        lines.append(f"- **最佳段落**: 第{stats['best_lap_index']}组 - {_format_pace(stats['best_pace'])}")
    if stats.get('avg_pace'):
        lines.append(f"- **平均配速**: {_format_pace(stats['avg_pace'])}")
    if stats.get('pace_std'):
        lines.append(f"- **配速标准差**: ±{int(stats['pace_std'])}s")
    if stats.get('hr_drift') is not None:
        drift_icon = "📈" if stats['hr_drift'] > 0 else "✅"
        lines.append(f"- **心率漂移**: {drift_icon} +{stats['hr_drift']} bpm (第1组→最后组)")
    if stats.get('fatigue_index') is not None:
        lines.append(f"- **疲劳指数**: {stats['fatigue_index']}% (末段vs首段)")

    return "\n".join(lines)


def _format_time(seconds: float) -> str:
    """格式化秒数为 mm:ss 或 hh:mm:ss。"""
    if seconds <= 0:
        return "N/A"
    seconds = int(seconds)
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h}:{m:02d}:{s:02d}"
    else:
        m = seconds // 60
        s = seconds % 60
        return f"{m}:{s:02d}"


def _format_pace(pace_seconds: float) -> str:
    """格式化配速（秒/公里）为 mm:ss/km。"""
    if pace_seconds <= 0:
        return "N/A"
    minutes = int(pace_seconds // 60)
    seconds = int(pace_seconds % 60)
    return f"{minutes}:{seconds:02d}/km"


def compare_intervals(analyses: List[dict]) -> str:
    """横向对比多次间歇训练。

    Args:
        analyses: 多次活动的分析结果列表，每个包含 'date', 'name', 'analysis'

    Returns:
        格式化的对比 Markdown 表格
    """
    if len(analyses) < 2:
        return "需要至少2次训练才能进行对比。"

    lines = []
    lines.append("## 📈 间歇跑横向对比")
    lines.append("")
    lines.append("| 日期 | 活动名称 | 间歇类型 | 平均配速 | 心率漂移 | 趋势 |")
    lines.append("|------|----------|----------|----------|----------|------|")

    prev_pace = None
    for item in analyses:
        date = item.get('date', 'N/A')
        name = item.get('name', 'N/A')[:15]
        analysis = item.get('analysis', {})
        stats = analysis.get('stats', {})

        interval_type = f"{stats.get('interval_count', 0)}×{stats.get('interval_distance', '?')}"
        avg_pace = _format_pace(stats.get('avg_pace', 0))
        hr_drift = stats.get('hr_drift', 0)
        drift_str = f"+{hr_drift}" if hr_drift else "N/A"

        # 计算趋势
        trend = ""
        if prev_pace and stats.get('avg_pace'):
            curr_pace = stats['avg_pace']
            if curr_pace < prev_pace:
                trend = "✅ 进步"
            elif curr_pace > prev_pace:
                trend = "📉 退步"
            else:
                trend = "➡️ 持平"
            prev_pace = curr_pace
        elif stats.get('avg_pace'):
            prev_pace = stats['avg_pace']

        lines.append(f"| {date} | {name} | {interval_type} | {avg_pace} | {drift_str} bpm | {trend} |")

    lines.append("")
    lines.append("### 分析结论")

    # 简单的趋势总结
    paces = [a['analysis']['stats'].get('avg_pace', 0) for a in analyses if a.get('analysis', {}).get('stats', {}).get('avg_pace')]
    if len(paces) >= 2:
        if paces[-1] < paces[0]:
            lines.append("✅ 配速有提升趋势，训练效果良好。")
        elif paces[-1] > paces[0]:
            lines.append("⚠️ 配速有下降趋势，建议关注恢复状态。")
        else:
            lines.append("➡️ 配速保持稳定，可考虑增加训练强度。")

    return "\n".join(lines)
