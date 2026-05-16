"""
Activity Query Tools for LangChain Agent

These tools wrap the Garmin API for use with LangChain agents.
"""

import logging
from typing import Optional
from datetime import date, timedelta

from langchain_core.tools import tool

from ..client import GarminClient
from .. import formatters
from ..classifier import classify_activity, TRAINING_TYPE_NAMES, TRAINING_TYPE_DESCRIPTIONS

logger = logging.getLogger(__name__)

# Global client instance (initialized by agent)
_client: Optional[GarminClient] = None

# Global cache instances (initialized in set_client)
_cache = None
_sync_manager = None


def set_client(client: GarminClient):
    """Set the global Garmin client for tools to use

    Also initializes the activity classification cache and triggers
    background sync if needed.
    """
    global _client, _cache, _sync_manager
    _client = client

    # Initialize cache
    try:
        from ..cache_manager import ActivityClassificationCache
        from ..cache_sync import CacheSyncManager

        _cache = ActivityClassificationCache()
        _sync_manager = CacheSyncManager(client, _cache)

        # Sync on login
        sync_result = _sync_manager.sync_on_login()
        logger.info(f"Cache sync result: {sync_result}")

        # Log cache stats
        stats = _cache.get_stats()
        logger.info(f"Cache stats: {stats['total_count']} activities, "
                    f"age: {stats['cache_age_hours']:.1f}h" if stats['cache_age_hours'] else "Cache stats: new cache")

    except Exception as e:
        logger.warning(f"Failed to initialize cache: {e}")
        _cache = None
        _sync_manager = None


def get_client() -> GarminClient:
    """Get the global Garmin client"""
    if _client is None:
        raise RuntimeError("Client not initialized. Call set_client() first.")
    return _client


# ==========================================
# Activity Query Tools
# ==========================================

@tool
def get_latest_activity() -> str:
    """获取最近一次跑步活动的信息。

    当用户问"最近跑了什么"、"上一次跑步"、"今天跑了吗"等问题时使用。

    Returns:
        包含活动名称、日期、距离、时长、心率等信息的字符串
    """
    client = get_client()
    activities = client.get_activities(limit=1)

    if not activities:
        return "没有找到最近的活动记录。"

    a = activities[0]
    distance_m = a.get("distance", 0) or 0
    duration_s = a.get("duration", 0) or 0
    avg_hr = a.get("averageHR")
    calories = a.get("calories")

    # 处理可选字段
    hr_line = f"- 平均心率: {int(avg_hr)} bpm" if avg_hr else "- 平均心率: 无数据"
    cal_line = f"- 消耗: {int(calories)} kcal" if calories else "- 消耗: 无数据"

    result = f"""最近一次活动:
- 名称: {a.get("activityName", "未命名")}
- 日期: {formatters.format_date(a.get("startTimeLocal", ""))}
- 距离: {formatters.format_distance(distance_m)}
- 时长: {formatters.format_duration(duration_s)}
{hr_line}
{cal_line}
- 活动ID: {a.get("activityId")}"""

    return result


@tool
def get_activities_by_date(start_date: str, end_date: str) -> str:
    """查询指定日期范围内的跑步活动统计。

    当用户问"这周跑了多少"、"最近7天训练情况"、"本月跑量"等问题时使用。

    Args:
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD

    Returns:
        包含总距离、总时长、活动次数等统计信息的字符串
    """
    client = get_client()
    activities = client.get_activities_by_date(start_date, end_date)

    if not activities:
        return f"在 {start_date} 到 {end_date} 期间没有找到活动记录。"

    # 计算总计
    total_distance = sum(a.get("distance", 0) or 0 for a in activities)
    total_duration = sum(a.get("duration", 0) or 0 for a in activities)
    total_calories = sum(a.get("calories", 0) or 0 for a in activities)

    result = f"""{start_date} 至 {end_date} 训练统计:
- 活动次数: {len(activities)} 次
- 总距离: {formatters.format_distance(total_distance)}
- 总时长: {formatters.format_duration_minutes(total_duration)}
- 总消耗: {int(total_calories)} kcal

活动列表:"""

    # 返回所有活动记录，带 ID
    for a in activities:
        dist = formatters.format_distance(a.get("distance", 0) or 0)
        name = a.get("activityName", "未命名")
        d = a.get("startTimeLocal", "")[:10]
        aid = a.get("activityId", "")
        result += f"\n- {d}: {name} ({dist}) [ID:{aid}]"

    return result


@tool
def get_week_summary(weeks: int = 1) -> str:
    """查询最近几周的训练统计。

    当用户问"本周跑量"、"最近两周训练"等问题时使用。

    Args:
        weeks: 查询最近几周，默认1周

    Returns:
        训练统计信息
    """
    end = date.today()
    start = end - timedelta(weeks=weeks)
    return get_activities_by_date.invoke({
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d")
    })


@tool
def search_activities(keywords: str = None, start_date: str = None, end_date: str = None, limit: int = 10) -> str:
    """搜索跑步活动，返回候选活动列表（包含活动ID）。

    这是查找活动的通用方法。当用户提到特定活动时，先用这个工具搜索，
    获取活动ID后，再用 get_activity_detail 获取详情。

    使用场景：
    - 用户说"3.20那次"、"3月20日的跑步" → 设置日期范围
    - 用户说"间歇课"、"速度课"、"长距离" → 设置关键词
    - 用户说"上周的速度课" → 同时设置日期范围和关键词

    Args:
        keywords: 关键词筛选，如"间歇"、"速度"、"轻松"、"长距离"等
        start_date: 开始日期，格式 YYYY-MM-DD（可选）
        end_date: 结束日期，格式 YYYY-MM-DD（可选）
        limit: 返回数量限制，默认10

    Returns:
        匹配的活动列表，包含活动ID、名称、日期、距离等信息
    """
    import re
    from datetime import datetime, timedelta

    client = get_client()

    # 确定搜索范围
    if not start_date or not end_date:
        # 默认搜索最近30天
        end = date.today()
        start = end - timedelta(days=30)
        start_date = start_date or start.strftime("%Y-%m-%d")
        end_date = end_date or end.strftime("%Y-%m-%d")

    # 获取活动列表
    activities = client.get_activities_by_date(start_date, end_date)

    if not activities:
        return f"在 {start_date} 到 {end_date} 期间没有找到活动记录。"

    # 按关键词筛选
    if keywords:
        keywords_lower = keywords.lower()
        filtered = []
        for a in activities:
            name = (a.get("activityName") or "").lower()
            # 支持常见关键词
            if keywords_lower in name:
                filtered.append(a)
            elif keywords_lower == "间歇" and ("间歇" in name or "interval" in name):
                filtered.append(a)
            elif keywords_lower == "速度" and ("速度" in name or "tempo" in name):
                filtered.append(a)
            elif keywords_lower == "轻松" and ("轻松" in name or "easy" in name):
                filtered.append(a)
            elif keywords_lower == "长距离" and ("长距离" in name or "long" in name):
                filtered.append(a)
        activities = filtered if filtered else activities

    # 限制数量
    activities = activities[:limit]

    # 格式化输出
    result = f"找到 {len(activities)} 个匹配的活动:\n"
    result += "-" * 50 + "\n"

    for a in activities:
        activity_id = a.get("activityId")
        name = a.get("activityName", "未命名")
        d = (a.get("startTimeLocal") or "")[:10]
        dist = formatters.format_distance(a.get("distance", 0) or 0)
        result += f"ID: {activity_id} | {d} | {name} ({dist})\n"

    result += "-" * 50
    result += "\n提示: 用活动ID调用 get_activity_detail 获取详细信息"

    return result


@tool
def get_activity_detail(activity_id: int = None) -> str:
    """获取单个活动的详细信息，包括配速、步态数据、训练效果等。

    当用户问"上次跑步的步态数据"、"活动的详细信息"、"配速多少"等问题时使用。

    Args:
        activity_id: 活动ID，如果不提供则查询最近一次活动

    Returns:
        包含配速、步态、训练效果等详细信息的字符串
    """
    client = get_client()

    # 如果没有提供有效 ID，获取最近一次活动
    if activity_id is None or activity_id <= 0:
        activities = client.get_activities(limit=1)
        if not activities:
            return "没有找到活动记录。"
        activity_id = activities[0].get("activityId")

    # 获取详情
    activity = client.get_activity(activity_id)

    if not activity:
        return f"未找到活动 {activity_id}"

    # 数据在 summaryDTO 中
    summary = activity.get("summaryDTO", {})

    # 基本信息
    distance_m = summary.get("distance", 0) or 0
    duration_s = summary.get("duration", 0) or 0
    avg_hr = summary.get("averageHR")
    max_hr = summary.get("maxHR")
    calories = summary.get("calories")
    start_time = summary.get("startTimeLocal", "")

    # 配速数据
    avg_speed = summary.get("averageSpeed")
    max_speed = summary.get("maxSpeed")

    # 步态数据
    gct = summary.get("groundContactTime")
    vo = summary.get("verticalOscillation")
    stride = summary.get("strideLength")
    cadence = summary.get("averageRunCadence")

    # 训练效果
    aerobic = summary.get("trainingEffect")
    anaerobic = summary.get("anaerobicTrainingEffect")

    # 构建基本信息部分
    basic_info = f"""活动详情: {activity.get("activityName", "未命名")}
日期: {formatters.format_date(start_time)}
活动ID: {activity_id}

【基本信息】
距离: {formatters.format_distance(distance_m)}
时长: {formatters.format_duration(duration_s)}"""

    if avg_hr:
        basic_info += f"\n平均心率: {int(avg_hr)} bpm"
    if max_hr:
        basic_info += f"\n最大心率: {int(max_hr)} bpm"
    if calories:
        basic_info += f"\n消耗: {int(calories)} kcal"

    result = f"""{basic_info}

【配速数据】
平均配速: {formatters.format_pace(avg_speed)}
最快配速: {formatters.format_pace(max_speed)}

【步态数据】"""

    if cadence:
        result += f"\n步频: {formatters.format_cadence(cadence)}"
    if stride:
        result += f"\n步幅: {formatters.format_stride(stride)}"
    if gct:
        result += f"\n触地时间: {formatters.format_gct(gct)}"
    if vo:
        result += f"\n垂直振幅: {formatters.format_vo(vo)}"

    if not any([cadence, stride, gct, vo]):
        result += "\n(无步态数据)"

    result += "\n\n【训练效果】"
    if aerobic is not None:
        result += f"\n有氧效果: {aerobic:.1f}"
    if anaerobic is not None:
        result += f"\n无氧效果: {anaerobic:.1f}"

    if not any([aerobic is not None, anaerobic is not None]):
        result += "\n(无训练效果数据)"

    return result


# ==========================================
# Additional Tools
# ==========================================

@tool
def get_activity_splits(activity_id: int) -> str:
    """获取活动的分段数据（每公里配速、心率、步频、步幅、垂直振幅等）。

    当用户问"分段配速"、"每公里配速"、"配速变化趋势"、"圈数据"等问题时使用。
    适用于分析配速稳定性、前后半程对比、步态变化等场景。

    Args:
        activity_id: 活动ID（必须先从 search_activities 获取)

    Returns:
        包含每公里配速、心率、步频、步幅、垂直振幅等分段数据的字符串
    """
    client = get_client()
    splits = client.get_activity_splits(activity_id)

    if not splits or not splits.get("lapDTOs"):
        return f"活动 {activity_id} 没有分段数据。"

    laps = splits["lapDTOs"]

    # 格式化输出 — 宽表
    result = f"活动 {activity_id} 分段数据 ({len(laps)} 圈):\n"
    result += "-" * 80 + "\n"
    result += f"{'段':<4} {'距离':<8} {'配速':<10} {'心率':<8} {'步频':<8} {'步幅':<8} {'垂振':<8}\n"
    result += "-" * 80 + "\n"

    for i, lap in enumerate(laps, 1):
        dist = formatters.format_distance(lap.get("distance", 0) or 0)
        pace = formatters.format_pace(lap.get("averageSpeed"))
        hr = f"{int(lap['averageHR'])}" if lap.get("averageHR") else "--"
        cadence = f"{int(lap['averageRunCadence'])}" if lap.get("averageRunCadence") else "--"
        stride = f"{lap['strideLength']:.0f}cm" if lap.get("strideLength") else "--"
        vo = f"{lap['verticalOscillation']:.1f}cm" if lap.get("verticalOscillation") else "--"
        result += f"{i:<4} {dist:<8} {pace:<10} {hr:<8} {cadence:<8} {stride:<8} {vo:<8}\n"

    return result


@tool
def get_interval_analysis(activity_id: int) -> str:
    """获取间歇训练的活跃段和恢复段数据。

    当用户问"间歇训练分析"、"速度课数据"、"间歇跑的恢复时间"等问题时使用。
    仅适用于包含间歇训练的活动。

    Args:
        activity_id: 活动ID（必须先从 search_activities 获取)

    Returns:
        包含活跃段(快跑)和恢复段(慢跑)的详细数据
    """
    client = get_client()
    typed_splits = client.get_activity_typed_splits(activity_id)
    if not typed_splits:
        return f"活动 {activity_id} 不是间歇训练活动，没有间歇训练数据。"

    # 格式化输出
    result = f"活动 {activity_id} 间歇训练分析:\n"
    result += "=" * 60 + "\n"

    # 活跃段 (INTERVAL_ACTIVE)
    active_splits = typed_splits.get("INTERVAL_ACTIVE", [])
    if active_splits:
        result += "\n【活跃段 - 快跑】\n"
        result += f"{'组':<4} {'距离':<8} {'时长':<10} {'配速':<10} {'心率':<8}\n"
        for i, split in enumerate(active_splits, 1):
            dist = formatters.format_distance(split.get("distance", 0) or 0)
            duration = formatters.format_duration(split.get("duration", 0) or 0)
            pace = formatters.format_pace(split.get("averageSpeed"))
            hr = f"{int(split['averageHR'])}" if split.get("averageHR") else "--"
            result += f"{i:<4} {dist:<8} {duration:<10} {pace:<10} {hr:<8}\n"
    else:
        result += "无活跃段数据\n"

    # 恢复段 (RECOVERY)
    recovery_splits = typed_splits.get("RECOVERY", [])
    if recovery_splits:
        result += "\n【恢复段 - 慢跑/休息】\n"
        result += f"{'组':<4} {'距离':<8} {'时长':<10} {'配速':<10} {'心率':<8}\n"
        for i, split in enumerate(recovery_splits, 1):
            dist = formatters.format_distance(split.get("distance", 0) or 0)
            duration = formatters.format_duration(split.get("duration", 0) or 0)
            pace = formatters.format_pace(split.get("averageSpeed"))
            hr = f"{int(split['averageHR'])}" if split.get("averageHR") else "--"
            result += f"{i:<4} {dist:<8} {duration:<10} {pace:<10} {hr:<8}\n"
    else:
        result += "无恢复段数据\n"

    return result


@tool
def get_activity_weather(activity_id: int) -> str:
    """获取活动的天气数据。

    当用户问"跑步时天气如何"、"上次跑步热不热"等问题时使用。

    适用于分析天气对运动表现的影响。

    Args:
        activity_id: 活动ID（必须先从 search_activities 获取)

    Returns:
        天气数据字符串
    """
    client = get_client()
    weather = client.get_activity_weather(activity_id)
    if not weather:
        return f"活动 {activity_id} 没有天气数据。"

    # 提取数据
    result = f"活动 {activity_id} 天气数据:\n"
    result += "-" * 50 + "\n"
    # 解析天气数据
    temperature = weather.get("temperature")
    humidity = weather.get("humidity")
    wind_speed = weather.get("windSpeed")
    feels_like = weather.get("feelsLike")
    condition = weather.get("weatherCondition")
    if temperature is not None:
        result += f"- 温度: {temperature}°C\n"
    if humidity is not None:
        result += f"- 湿度: {humidity}%\n"
    if wind_speed is not None:
        result += f"- 风速: {wind_speed} m/s秒\n"
    if feels_like is not None:
        result += f"- 体感温度: {feels_like}°C\n"
    if condition is not None:
        result += f"- 天气状况: {condition}\n"
    return result


@tool
def get_hill_score(activity_id: int) -> str:
    """获取爬坡能力评分。

    当用户问"爬坡能力如何"、"上坡跑得怎么样"时使用。
    仅适用于包含爬坡数据的活动。

    Args:
        activity_id: 活动ID(必须先从 search_activities 获取)

    Returns:
        紻坡能力评分和分析
    """
    client = get_client()
    hill_data = client.get_hill_score(activity_id)
    if not hill_data:
        return f"活动 {activity_id} 没有爬坡数据。"

    # 提取评分
    score = hill_data.get("hillScore")
    if score is None:
        return "无法获取爬坡评分"

    # 评级
    if score >= 80:
        rating = "优秀"
    elif score >= 60:
        rating = "良好"
    elif score >= 40:
        rating = "中等"
    else:
        rating = "需改进"
    return f"""爬坡能力评分: {score}/100
评级: {rating}

建议: 多进行爬坡训练来提高爬坡能力！"""


@tool
def get_fitnessage_data() -> str:
    """获取健身年龄数据。

    当用户问"我的健身年龄"、"身体状态如何"等问题时使用。

    Returns:
        包含健身年龄、VO2 Max 筪数据的字符串
    """
    client = get_client()
    fitness_data = client.get_fitnessage_data()
    if not fitness_data:
        return "无法获取健身年龄数据"
    # 提取数据
    fitness_age_data = fitness_data.get("fitnessAgeData", {})
    fitness_age = fitness_age_data.get("fitnessAge")
    vo2_max = fitness_age_data.get("vo2Max")
    activity_level = fitness_age_data.get("activityLevel")
    rest_hr = fitness_age_data.get("restingHeartRate")
    # 格式化输出
    result = "健身年龄数据:\n"
    result += "-" * 50 + "\n"
    if fitness_age is not None:
        result += f"- 健身年龄: {int(fitness_age)} 岁\n"
    if vo2_max is not None:
        result += f"- 最大摄氧量: {vo2_max} mL/kg/min\n"
    if activity_level is not None:
        result += f"- 活动水平: {activity_level}\n"
    if rest_hr is not None:
        result += f"- 静息心率: {int(rest_hr)} bpm\n"
    result += "-" * 50
    return result


@tool
def get_training_status() -> str:
    """获取当前训练状态。

    当用户问"训练状态如何"、"恢复得怎么样"等问题时使用。

    Returns:
        训练状态信息
    """
    client = get_client()
    status_data = client.get_training_status()
    if not status_data:
        return "无法获取训练状态数据"
    # 解析状态
    status = status_data.get("status", "未知")
    status_text = {
        "productive": "高效训练",
        "maintaining": "维持状态",
        "peaking": "巅峰状态",
        "recovery": "恢复中",
        "strained": "过度训练",
    }
    status = status_text.get(status_data.get("status", ""), "未知")
    # 格式化输出
    result = f"训练状态: {status_text.get(status, '未知')}\n"
    result += f"原始状态: {status}\n"
    if "trainingLoad" in status_data:
        result += f"- 训练负荷: {status_data['trainingLoad']}\n"
    if "restDays" in status_data:
        result += f"- 建议休息天数: {status_data['restDays']} 天\n"
    return result


@tool
def get_race_predictions() -> str:
    """获取比赛配速预测。

    当用户问"比赛预测"、"我能跑多少配速"等问题时使用。

    Returns:
        比赛预测数据
    """
    client = get_client()
    predictions = client.get_race_predictions()
    if not predictions:
        return "无法获取比赛预测数据"
    # 格式化输出
    result = "比赛配速预测:\n"
    result += "-" * 50 + "\n"
    # 按距离排序
    distances = [5, 10, 21.1, 42.2]
    for d in distances:
        time_key = f"time{d}km"
        time_sec = predictions.get(time_key)
        if time_sec:
            pace_str = formatters.format_pace_from_min_km(time_sec / 60)
            result += f"{d}公里: {pace_str}\n"
    return result


@tool
def get_endurance_score() -> str:
    """获取耐力评分。

    当用户问"耐力评分"、"体能水平"等问题时使用。

    Returns:
        耐力评分信息
    """
    client = get_client()
    endurance = client.get_endurance_score()
    if not endurance:
        return "无法获取耐力评分数据"
    score = endurance.get("enduranceScore", 0)
    # 评级
    if score >= 60:
        rating = "优秀"
    elif score >= 45:
        rating = "良好"
    elif score >= 30:
        rating = "中等"
    else:
        rating = "需改进"
    return f"""耐力评分: {score}/100
评级: {rating}
建议: 持续规律训练来提高耐力水平！"""


@tool
def get_sleep_data(date_str: str = None) -> str:
    """获取睡眠数据。

    当用户问"睡眠质量如何"、"昨天睡得怎么样"等问题时使用。

    Args:
        date_str: 日期,格式 YYYY-MM-DD, 默认今天

    Returns:
        睡眠数据信息
    """
    client = get_client()
    if date_str is None:
        from datetime import date
        date_str = date.today().strftime("%Y-%m-%d")
    sleep = client.get_sleep_data(date_str)
    if not sleep:
        return f"没有找到 {date_str} 的睡眠数据"
    if isinstance(sleep, list):
        sleep = sleep[0] if sleep else {}
    daily_sleep = sleep.get("dailySleepDTO", {})
    total_seconds = daily_sleep.get("sleepTimeSeconds", 0)
    deep_seconds = daily_sleep.get("deepSleepSeconds", 0)
    light_seconds = daily_sleep.get("lightSleepSeconds", 0)
    rem_seconds = daily_sleep.get("remSleepSeconds", 0)
    awake_count = daily_sleep.get("awakeCount", 0)
    # 格式化输出
    result = f"睡眠数据 ({date_str}):\n"
    result += "-" * 40 + "\n"
    if total_seconds:
        result += f"- 总睡眠: {formatters.format_duration_minutes(total_seconds)}\n"
    if deep_seconds:
        result += f"- 深睡: {formatters.format_duration_minutes(deep_seconds)}\n"
    if light_seconds:
        result += f"- 浅睡: {formatters.format_duration_minutes(light_seconds)}\n"
    if rem_seconds:
        result += f"- REM睡眠: {formatters.format_duration_minutes(rem_seconds)}\n"
    if awake_count:
        result += f"- 清醒次数: {awake_count} 次\n"
    result += "-" * 40
    # 评估
    if total_seconds:
        if total_seconds >= 7 * 3600:
            result += "\n睡眠质量: 良好 (7小时以上)"
        elif total_seconds >= 6 * 3600:
            result += "\n睡眠质量: 中等 (6-7小时)"
        else:
            result += "\n睡眠质量: 不足 (少于6小时)"
    return result


# ==========================================
# Heart Rate Tools
# ==========================================

@tool
def get_heart_rate_data(date_str: str = None) -> str:
    """获取心率数据。

    当用户问"今天心率"、"心率曲线"等问题时使用。

    Args:
        date_str: 日期,格式 YYYY-MM-DD, 默认今天

    Returns:
        心率数据信息
    """
    client = get_client()
    if date_str is None:
        from datetime import date
        date_str = date.today().strftime("%Y-%m-%d")
    hr_data = client.get_heart_rates(date_str)
    if not hr_data:
        return f"没有找到 {date_str} 的心率数据"
    # API 可能返回 list 或 dict
    if isinstance(hr_data, list):
        hr_values = hr_data
    else:
        hr_values = hr_data.get("heartRateValues", [])
    if not hr_values:
        return "心率数据为空"
    # 计算统计数据
    hr_list = [v.get("heartRateValue", 0) for v in hr_values if v.get("heartRateValue")]
    if hr_list:
        max_hr = max(hr_list)
        min_hr = min(hr_list)
        avg_hr = sum(hr_list) / len(hr_list)
    else:
        max_hr = min_hr = avg_hr = 0
    # 格式化输出
    result = f"心率数据 ({date_str}):\n"
    result += "-" * 40 + "\n"
    result += f"- 最高心率: {int(max_hr)} bpm\n"
    result += f"- 最低心率: {int(min_hr)} bpm\n"
    result += f"- 平均心率: {int(avg_hr)} bpm\n"
    result += f"- 记录数: {len(hr_list)} 条\n"
    return result


@tool
def get_resting_heart_rate(date_str: str = None) -> str:
    """获取静息心率(RHR)数据。

    当用户问"静息心率"、"RHR多少"等问题时使用。
    避息心率是评估有氧能力的关键指标。

    Args:
        date_str: 日期,格式 YYYY-MM-DD, 默认今天

    Returns:
        静息心率数据
    """
    client = get_client()
    if date_str is None:
        from datetime import date
        date_str = date.today().strftime("%Y-%m-%d")
    rhr_data = client.get_rhr_day(date_str)
    if not rhr_data:
        return f"没有找到 {date_str} 的静息心率数据"
    # API 可能返回 list 或 dict
    if isinstance(rhr_data, list):
        rhr_data = rhr_data[0] if rhr_data else {}
    rhr = rhr_data.get("restingHeartRate")
    # 格式化输出
    result = f"静息心率 ({date_str}):\n"
    result += "-" * 40 + "\n"
    if rhr:
        result += f"- 静息心率: {int(rhr)} bpm\n"
    # 评估
    if rhr:
        if rhr <= 50:
            result += "- 评级: 优秀 (运动员水平)\n"
        elif rhr <= 60:
            result += "- 评级: 良好 (健康水平)\n"
        elif rhr <= 70:
            result += "- 评级: 中等\n"
        else:
            result += "- 评级: 偏高 (需要加强有氧训练)\n"
    return result


@tool
def get_hrv_data(date_str: str = None) -> str:
    """获取心率变异性(HRV)数据。

    当用户问"HRV数据"、"心率变异性"等问题时使用。
    HRV是评估恢复状态和重要指标。

    Args:
        date_str: 日期,格式 YYYY-MM-DD, 默认今天

    Returns:
        HRV数据信息
    """
    client = get_client()
    if date_str is None:
        from datetime import date
        date_str = date.today().strftime("%Y-%m-%d")
    hrv_data = client.get_hrv_data(date_str)
    if not hrv_data:
        return f"没有找到 {date_str} 的HRV数据"
    if isinstance(hrv_data, list):
        hrv_data = hrv_data[0] if hrv_data else {}
    hrv_summary = hrv_data.get("hrvSummary", {})
    weekly_avg = hrv_summary.get("weeklyAvg", 0)
    last_night_avg = hrv_summary.get("lastNightAvg", 0)
    status = hrv_summary.get("status", "未知")
    # 格式化输出
    result = f"心率变异性(HRV)数据 ({date_str}):\n"
    result += "-" * 40 + "\n"
    if weekly_avg:
        result += f"- 周平均HRV: {weekly_avg} ms\n"
    if last_night_avg:
        result += f"- 昨晚HRV: {last_night_avg} ms\n"
    if status:
        result += f"- 状态: {status}\n"
    result += "-" * 40 + "\n"
    # 评估
    if last_night_avg:
        if last_night_avg >= 60:
            result += "HRV状态: 优秀 (恢复良好)\n"
        elif last_night_avg >= 40:
            result += "HRV状态: 中等\n"
        else:
            result += "HRV状态: 较低 (需要更多休息)\n"
    return result


@tool
def get_lactate_threshold() -> str:
    """获取乳酸阈值数据。

    当用户问"乳酸阈值"、"LT心率"等问题时使用。
    乳酸阈值是确定训练区间的重要参考。

    Returns:
        乳酸阈值数据(心率和配速)
    """
    client = get_client()
    lt_data = client.get_lactate_threshold()
    if not lt_data:
        return "无法获取乳酸阈值数据"
    # 提取数据
    lt_hr = lt_data.get("lactateThresholdHeartRate")
    lt_speed = lt_data.get("lactateThresholdSpeed")
    # 格式化输出
    result = "乳酸阈值数据:\n"
    result += "-" * 40 + "\n"
    if lt_hr:
        result += f"- 乳酸阈值心率: {int(lt_hr)} bpm\n"
    if lt_speed:
        # 速度是 m/s, 转换为配速
        pace = formatters.format_pace(lt_speed)
        result += f"- 乳酸阈值配速: {pace}\n"
    result += "-" * 40 + "\n"
    result += "提示: 乳酸阈值心率和配速是确定高强度训练区间的重要参考值。\n"
    return result


@tool
def get_activity_hr_zones(activity_id: int) -> str:
    """获取活动的心率区间分布。

    当用户问"心率区间分布"、"在哪个心率区间跑了多久"等问题时使用。
    适用于分析训练强度分布。

    Args:
        activity_id: 活动ID(必须先从 search_activities 获取)

    Returns:
        心率区间分布数据
    """
    client = get_client()
    hr_zones = client.get_activity_hr_in_timezones(activity_id)
    if not hr_zones:
        return f"活动 {activity_id} 没有心率区间数据"
    # 格式化输出
    result = f"活动 {activity_id} 心率区间分布:\n"
    result += "-" * 50 + "\n"
    result += f"{'区间':<10} {'心率范围':<15} {'时长':<10}\n"
    result += "-" * 50 + "\n"
    # 心率区间通常按百分比划分
    zones = hr_zones.get("timeInHeartRateZones", [])
    if zones:
        for zone in zones:
            zone_low = zone.get("zoneLowBoundary", 0)
            zone_high = zone.get("zoneHighBoundary", 0)
            secs = zone.get("secsInZone", 0)
            minutes = secs / 60
            result += f"Zone {zone_low}-{zone_high} bpm: {minutes:.1f} 分钟\n"
    else:
        result += "无区间数据\n"
    return result


@tool
def get_training_readiness(date_str: str = None) -> str:
    """获取训练准备度评分。

    当用户问"训练准备度"、"今天适合训练吗"等问题时使用。
    综合评估睡眠、恢复、训练负荷等因素。

    Args:
        date_str: 日期,格式 YYYY-MM-DD, 默认今天

    Returns:
        训练准备度评分和分析
    """
    client = get_client()
    if date_str is None:
        from datetime import date
        date_str = date.today().strftime("%Y-%m-%d")
    readiness = client.get_training_readiness(date_str)
    if not readiness:
        return f"没有找到 {date_str} 的训练准备度数据"
    if isinstance(readiness, list):
        readiness = readiness[0] if readiness else {}
    score = readiness.get("trainingReadinessScore", 0)
    # 格式化输出
    result = f"训练准备度 ({date_str}):\n"
    result += "-" * 40 + "\n"
    if score:
        result += f"- 训练准备度评分: {int(score)}/100\n"
    # 评估
    if score >= 80:
        result += "- 状态: 极佳 (适合高强度训练)\n"
    elif score >= 60:
        result += "- 状态: 良好 (可以进行正常训练)\n"
    elif score >= 40:
        result += "- 状态: 中等 (建议轻度训练)\n"
    else:
        result += "- 状态: 较低 (建议休息或恢复跑)\n"
    return result


# ==========================================
# Additional Activity Tools
# ==========================================

@tool
def get_activities_fordate(date_str: str = None) -> str:
    """获取指定日期的所有活动列表。

    当用户问"3月20日跑了什么"、"今天有什么活动"等问题时使用。

    Args:
        date_str: 日期,格式 YYYY-MM-DD, 默认今天

    Returns:
        指定日期的活动列表
    """
    client = get_client()
    if date_str is None:
        from datetime import date
        date_str = date.today().strftime("%Y-%m-%d")
    activities = client.get_activities_fordate(date_str)
    if not activities:
        return f"没有找到 {date_str} 的活动记录"
    # 格式化输出
    result = f"{date_str} 的活动列表:\n"
    result += "-" * 50 + "\n"
    for a in activities:
        activity_id = a.get("activityId")
        name = a.get("activityName", "未命名")
        activity_type = a.get("activityType", {}).get("typeKey", "unknown")
        dist = formatters.format_distance(a.get("distance", 0) or 0)
        duration = formatters.format_duration(a.get("duration", 0) or 0)
        result += f"ID: {activity_id} | {name} | {activity_type} | {dist} | {duration}\n"
    result += "-" * 50
    result += f"\n共 {len(activities)} 个活动"
    return result


@tool
def get_activity_split_summaries(activity_id: int) -> str:
    """获取活动的分段摘要数据。

    当用户问"分段摘要"、"每圈汇总"等问题时使用。
    提供每段的关键统计数据汇总。

    Args:
        activity_id: 活动ID(必须先从 search_activities 获取)

    Returns:
        分段摘要数据
    """
    client = get_client()
    summaries = client.get_activity_split_summaries(activity_id)
    if not summaries:
        return f"活动 {activity_id} 没有分段摘要数据"
    # 格式化输出
    result = f"活动 {activity_id} 分段摘要:\n"
    result += "-" * 70 + "\n"
    result += f"{'段':<4} {'距离':<10} {'时长':<10} {'配速':<12} {'心率':<10} {'步频':<10}\n"
    result += "-" * 70 + "\n"
    splits = summaries.get("splitSummaries", [])
    for i, split in enumerate(splits, 1):
        dist = formatters.format_distance(split.get("totalDistance", 0) or 0)
        duration = formatters.format_duration(split.get("totalDuration", 0) or 0)
        pace = formatters.format_pace(split.get("avgSpeed"))
        hr = f"{int(split['avgHeartRate'])}" if split.get("avgHeartRate") else "--"
        cadence = f"{int(split['avgRunCadence'])}" if split.get("avgRunCadence") else "--"
        result += f"{i:<4} {dist:<10} {duration:<10} {pace:<12} {hr:<10} {cadence:<10}\n"
    return result


@tool
def get_activity_details(activity_id: int) -> str:
    """获取活动的逐秒数据(最细粒度)。

    当用户需要最详细的活动数据时使用,包含每秒的记录。
    注意: 数据量可能很大,仅显示摘要和前几条记录。

    Args:
        activity_id: 活动ID(必须先从 search_activities 获取)

    Returns:
        逐秒数据摘要
    """
    client = get_client()
    details = client.get_activity_details(activity_id)
    if not details:
        return f"活动 {activity_id} 没有详细数据"
    # 提取数据
    metrics = details.get("activityDetails", [])
    if not metrics:
        return "没有逐秒数据"
    # 统计
    result = f"活动 {activity_id} 逐秒数据:\n"
    result += "-" * 50 + "\n"
    result += f"- 总记录数: {len(metrics)} 条\n"
    # 显示前5条记录
    result += "\n前5条记录:\n"
    result += f"{'时间':<8} {'心率':<8} {'配速':<12} {'步频':<8}\n"
    for i, m in enumerate(metrics[:5]):
        time_sec = m.get("elapsedTime", 0)
        hr = m.get("heartRate", "--")
        speed = m.get("speed", 0)
        pace = formatters.format_pace(speed) if speed else "--"
        cadence = m.get("runCadence", "--")
        result += f"{time_sec:<8} {hr:<8} {pace:<12} {cadence:<8}\n"
    result += "-" * 50
    result += "\n提示: 这是逐秒数据,可用于详细分析"
    return result


@tool
def get_activity_power_zones(activity_id: int) -> str:
    """获取活动的功率区间分布(骑行等运动)。

    当用户问"功率区间"、"功率分布"等问题时使用。
    主要用于骑行等带功率计的运动。

    Args:
        activity_id: 活动ID(必须先从 search_activities 获取)

    Returns:
        功率区间分布数据
    """
    client = get_client()
    power_zones = client.get_activity_power_in_timezones(activity_id)
    if not power_zones:
        return f"活动 {activity_id} 没有功率区间数据(可能不是骑行活动)"
    # 格式化输出
    result = f"活动 {activity_id} 功率区间分布:\n"
    result += "-" * 50 + "\n"
    zones = power_zones.get("powerZoneInfo", [])
    if zones:
        for zone in zones:
            zone_num = zone.get("zoneNumber", "?")
            low = zone.get("lowWatts", 0)
            high = zone.get("highWatts", 0)
            secs = zone.get("secsInZone", 0)
            minutes = secs / 60
            result += f"Zone {zone_num}: {low}-{high}W | {minutes:.1f} 分钟\n"
    else:
        result += "无功率区间数据\n"
    return result


@tool
def get_activity_exercise_sets(activity_id: int) -> str:
    """获取力量训练的练习组数据。

    当用户问"力量训练组数"、"举重数据"等问题时使用。
    仅适用于力量训练类活动。

    Args:
        activity_id: 活动ID(必须先从 search_activities 获取)

    Returns:
        力量训练组数据
    """
    client = get_client()
    sets = client.get_activity_exercise_sets(activity_id)
    if not sets:
        return f"活动 {activity_id} 不是力量训练活动,没有练习组数据"
    # 格式化输出
    result = f"活动 {activity_id} 力量训练数据:\n"
    result += "-" * 60 + "\n"
    exercise_sets = sets.get("exerciseSets", [])
    if not exercise_sets:
        return "没有找到练习组数据"
    for i, exercise_set in enumerate(exercise_sets, 1):
        exercise_name = exercise_set.get("exerciseName", "未知动作")
        result += f"\n【{i}. {exercise_name}】\n"
        reps_list = exercise_set.get("reps", [])
        for j, rep in enumerate(reps_list, 1):
            weight = rep.get("weight", 0)
            rep_count = rep.get("reps", 0)
            if weight:
                result += f"  第{j}组: {rep_count}次 × {weight}kg\n"
            else:
                result += f"  第{j}组: {rep_count}次\n"
    return result


# ==========================================
# Merged Summary Tools (减少工具数量)
# ==========================================

@tool
def get_daily_health_summary(date_str: str = None) -> str:
    """获取每日健康摘要(合并睡眠、HRV、训练准备度)。

    当用户问"今天状态如何"、"身体状态"、"恢复得怎么样"等综合健康问题时使用。
    一次性获取睡眠、HRV和训练准备度数据。

    Args:
        date_str: 日期,格式 YYYY-MM-DD, 默认今天

    Returns:
        每日健康摘要(睡眠+HRV+训练准备度)
    """
    client = get_client()
    if date_str is None:
        date_str = date.today().strftime("%Y-%m-%d")

    result = f"📅 每日健康摘要 ({date_str})\n"
    result += "=" * 50 + "\n"

    # 1. 睡眠数据
    result += "\n【睡眠】\n"
    result += "-" * 40 + "\n"
    try:
        sleep = client.get_sleep_data(date_str)
        if sleep:
            if isinstance(sleep, list):
                sleep = sleep[0] if sleep else {}
            daily_sleep = sleep.get("dailySleepDTO", {})
            total_seconds = daily_sleep.get("sleepTimeSeconds", 0)
            deep_seconds = daily_sleep.get("deepSleepSeconds", 0)
            rem_seconds = daily_sleep.get("remSleepSeconds", 0)
            score_data = daily_sleep.get("overallSleepScore", {})
            score = score_data.get("value") if isinstance(score_data, dict) else score_data

            if total_seconds:
                result += f"总睡眠: {formatters.format_duration_minutes(total_seconds)}\n"
            if deep_seconds:
                result += f"深睡: {formatters.format_duration_minutes(deep_seconds)}\n"
            if rem_seconds:
                result += f"REM: {formatters.format_duration_minutes(rem_seconds)}\n"
            if score:
                result += f"睡眠评分: {score}\n"
            else:
                result += "睡眠评分: 无数据\n"
        else:
            result += "无睡眠数据\n"
    except Exception as e:
        result += f"睡眠数据获取失败: {e}\n"

    # 2. HRV数据
    result += "\n【心率变异性(HRV)】\n"
    result += "-" * 40 + "\n"
    try:
        hrv = client.get_hrv_data(date_str)
        if hrv:
            if isinstance(hrv, list):
                hrv = hrv[0] if hrv else {}
            hrv_summary = hrv.get("hrvSummary", {})
            weekly_avg = hrv_summary.get("weeklyAvg", 0)
            status = hrv_summary.get("status", "未知")
            result += f"周平均: {weekly_avg} ms\n"
            result += f"状态: {status}\n"
        else:
            result += "无HRV数据\n"
    except Exception as e:
        result += f"HRV数据获取失败: {e}\n"

    # 3. 训练准备度
    result += "\n【训练准备度】\n"
    result += "-" * 40 + "\n"
    try:
        readiness = client.get_training_readiness(date_str)
        if readiness:
            # API 返回的是 list，取第一个元素
            if isinstance(readiness, list) and len(readiness) > 0:
                readiness = readiness[0]
            score = readiness.get("score", 0)
            level = readiness.get("level", "未知")
            result += f"准备度: {int(score)}/100\n"
            result += f"等级: {level}\n"
        else:
            result += "无训练准备度数据\n"
    except Exception as e:
        result += f"训练准备度获取失败: {e}\n"

    return result


@tool
def get_training_capacity() -> str:
    """获取训练能力概览(合并训练状态、健身年龄、耐力、比赛预测、乳酸阈值)。

    当用户问"我的体能水平"、"训练状态如何"、"能跑多快"等能力评估问题时使用。
    一次性获取所有训练能力相关指标。

    Returns:
        训练能力概览(训练状态+健身年龄+耐力+比赛预测+乳酸阈值)
    """
    client = get_client()

    result = "🏃 训练能力概览\n"
    result += "=" * 50 + "\n"

    # 1. 训练状态
    result += "\n【训练状态】\n"
    result += "-" * 40 + "\n"
    try:
        today = date.today().strftime("%Y-%m-%d")
        status_data = client.get_training_status(today)
        if status_data:
            status = status_data.get("status", "未知")
            status_text = {
                "productive": "高效训练",
                "maintaining": "维持状态",
                "peaking": "巅峰状态",
                "recovery": "恢复中",
                "strained": "过度训练",
            }
            result += f"状态: {status_text.get(status, status)}\n"
            # VO2Max
            vo2 = status_data.get("mostRecentVO2Max", {})
            if isinstance(vo2, dict):
                vo2_val = vo2.get("generic", {}).get("vo2MaxValue")
                if vo2_val:
                    result += f"VO2Max: {vo2_val}\n"
        else:
            result += "无训练状态数据\n"
    except Exception as e:
        result += f"训练状态获取失败: {e}\n"

    # 2. 健身年龄
    result += "\n【健身年龄】\n"
    result += "-" * 40 + "\n"
    try:
        fitness_data = client.get_fitnessage_data()
        if fitness_data:
            fa = fitness_data.get("fitnessAgeData", {})
            fitness_age = fa.get("fitnessAge")
            vo2_max = fa.get("vo2Max")
            if fitness_age:
                result += f"健身年龄: {int(fitness_age)} 岁\n"
            if vo2_max:
                result += f"最大摄氧量: {vo2_max} mL/kg/min\n"
        else:
            result += "无健身年龄数据\n"
    except Exception as e:
        result += f"健身年龄获取失败: {e}\n"

    # 3. 耐力评分
    result += "\n【耐力评分】\n"
    result += "-" * 40 + "\n"
    try:
        endurance = client.get_endurance_score()
        if endurance:
            score = endurance.get("enduranceScore", 0)
            result += f"耐力评分: {score}/100\n"
            if score >= 60:
                result += "评级: 优秀\n"
            elif score >= 45:
                result += "评级: 良好\n"
            elif score >= 30:
                result += "评级: 中等\n"
            else:
                result += "评级: 需改进\n"
        else:
            result += "无耐力评分数据\n"
    except Exception as e:
        result += f"耐力评分获取失败: {e}\n"

    # 4. 比赛预测
    result += "\n【比赛预测】\n"
    result += "-" * 40 + "\n"
    try:
        predictions = client.get_race_predictions()
        if predictions:
            distances = [(5, "5公里"), (10, "10公里"), (21.1, "半马"), (42.2, "全马")]
            for d, name in distances:
                time_key = f"time{d}km" if d != 21.1 and d != 42.2 else f"time{int(d*10)}km"
                if d == 21.1:
                    time_key = "timeHalfMarathon"
                elif d == 42.2:
                    time_key = "timeMarathon"
                else:
                    time_key = f"time{d}K" if f"time{d}K" in predictions else f"time{d}km"
                time_sec = predictions.get(time_key)
                if time_sec:
                    pace_str = formatters.format_pace_from_min_km(time_sec / 60)
                    result += f"{name}: {pace_str}\n"
        else:
            result += "无比赛预测数据\n"
    except Exception as e:
        result += f"比赛预测获取失败: {e}\n"

    # 5. 乳酸阈值
    result += "\n【乳酸阈值】\n"
    result += "-" * 40 + "\n"
    try:
        lt_data = client.get_lactate_threshold()
        if lt_data:
            # 尝试获取速度和心率数据
            lt_hr = lt_data.get("lactateThresholdHeartRate")
            lt_speed = lt_data.get("lactateThresholdSpeed")
            # 也尝试从 speedAndHeartRate 获取
            speed_hr = lt_data.get("speedAndHeartRate", {})
            if not lt_hr and speed_hr:
                lt_hr = speed_hr.get("heartRate")
            if not lt_speed and speed_hr:
                lt_speed = speed_hr.get("speed")

            if lt_hr:
                result += f"阈值心率: {int(lt_hr)} bpm\n"
            if lt_speed:
                pace = formatters.format_pace(lt_speed)
                result += f"阈值配速: {pace}\n"
        else:
            result += "无乳酸阈值数据\n"
    except Exception as e:
        result += f"乳酸阈值获取失败: {e}\n"

    return result


# ==========================================
# Activity Classification Tool
# ==========================================

@tool
def classify_activity_type(activity_id: int = None) -> str:
    """分析活动的训练类型(轻松跑/节奏跑/间歇/长距离等)。

    当用户问"这是什么类型的训练"、"分析训练强度"、"是轻松跑还是节奏跑"时使用。
    基于心率区间分布和活动特征进行分类。

    分类规则(优先级从高到低):
    1. 赛事 → event_type = 'race'
    2. 越野 → activity_type = 'trail_running'
    3. 间歇 → ACTIVE圈>5 且 RECOVERY圈>4
    4. 长距离 → 距离>=15km
    5. 乳酸阈值跑 → Z3+Z4+Z5>90%
    6. 节奏跑 → Z3+Z4>70%
    7. 轻松跑 → Z2+Z3>70%
    8. 混合 → 默认

    Args:
        activity_id: 活动ID(必须先从 search_activities 获取)，不提供则分析最近一次

    Returns:
        训练类型分类结果和分析
    """
    client = get_client()

    # 如果没有提供ID，获取最近活动
    if activity_id is None or activity_id <= 0:
        activities = client.get_activities(limit=1)
        if not activities:
            return "没有找到活动记录。"
        activity_id = activities[0].get("activityId")

    # 获取活动详情
    activity = client.get_activity(activity_id)
    if not activity:
        return f"未找到活动 {activity_id}"

    # 提取分类所需数据
    summary = activity.get("summaryDTO", {})
    activity_type = activity.get("activityType", {}).get("typeKey", "")
    event_type = activity.get("eventType", {}).get("typeKey", "")
    total_distance = summary.get("distance", 0) or 0

    # 获取心率区间数据
    hr_zones_data = client.get_activity_hr_in_timezones(activity_id)
    hr_zones = []
    if hr_zones_data:
        hr_zones = hr_zones_data.get("timeInHeartRateZones", [])

    # 获取分段数据(用于间歇判断)
    laps_data = client.get_activity_splits(activity_id)
    laps = []
    if laps_data:
        laps = laps_data.get("lapDTOs", [])

    # 调用分类器
    result = classify_activity(
        activity_type=activity_type,
        event_type=event_type,
        total_distance=total_distance,
        laps=laps,
        hr_zones=hr_zones,
    )

    # 格式化输出
    training_type = result.get('type', 'unknown')
    reason = result.get('reason', '')
    zone_dist = result.get('zone_distribution', {})

    type_name = TRAINING_TYPE_NAMES.get(training_type, training_type)
    type_desc = TRAINING_TYPE_DESCRIPTIONS.get(training_type, '')

    output = f"""训练类型分析 (活动ID: {activity_id})
{"=" * 50}

【分类结果】{type_name}
{type_desc}

【判断依据】{reason}
"""

    if zone_dist:
        output += "\n【心率区间分布】\n"
        output += "-" * 30 + "\n"
        for z in range(1, 6):
            pct = zone_dist.get(z, 0)
            bar = "█" * int(pct / 5)
            output += f"Z{z}: {pct:5.1f}% {bar}\n"

    # 训练建议
    suggestions = {
        'race': '比赛后注意充分恢复，建议2-3天轻松跑或休息。',
        'trail': '越野跑对核心稳定性要求高，建议加强核心训练。',
        'interval': '间歇训练强度高，确保有充分恢复时间(48-72小时)。',
        'long_run': '长距离跑是耐力基础，注意补给和恢复。',
        'lactate_threshold': '乳酸阈值训练强度很高，注意监控恢复状态。',
        'tempo': '节奏跑提升阈值配速，建议每周1-2次。',
        'easy': '轻松跑是有氧基础，可以频繁进行。',
        'mixed': '混合训练强度分布不均，建议观察训练效果。',
    }

    output += f"\n【建议】{suggestions.get(training_type, '')}"

    return output


@tool
def search_by_training_type(
    training_type: str,
    limit: int = 5,
    start_date: str = None,
    end_date: str = None,
) -> str:
    """按训练类型搜索活动（使用分类器智能识别）。

    当用户问"最近几次间歇跑"、"找节奏跑训练"、"长距离跑有哪些"时使用。
    自动分类并筛选出指定类型的训练。

    Args:
        training_type: 训练类型，支持：
            - interval/间歇 - 间歇训练
            - tempo/节奏 - 节奏跑
            - easy/轻松 - 轻松跑
            - long_run/长距离 - 长距离跑(15km+)
            - race/比赛 - 赛事
            - lactate_threshold/乳酸阈值 - 乳酸阈值跑
        limit: 返回数量，默认5
        start_date: 开始日期，默认90天前
        end_date: 结束日期，默认今天

    Returns:
        匹配指定类型的活动列表
    """
    client = get_client()

    # 类型映射
    type_map = {
        "间歇": "interval", "interval": "interval", "间歇跑": "interval",
        "节奏": "tempo", "tempo": "tempo", "节奏跑": "tempo",
        "轻松": "easy", "easy": "easy", "轻松跑": "easy",
        "长距离": "long_run", "long_run": "long_run", "长跑": "long_run", "lsd": "long_run",
        "比赛": "race", "race": "race", "赛事": "race",
        "乳酸阈值": "lactate_threshold", "lactate_threshold": "lactate_threshold",
        "越野": "trail", "trail": "trail", "越野跑": "trail",
    }

    target_type = type_map.get(training_type.lower(), training_type.lower())

    # 性能计时
    import time
    start_time = time.time()
    cache_hit = False

    # ==========================================
    # Step 1: Try cache first
    # ==========================================
    if _cache is not None:
        cached_results = _cache.get_all_by_type(target_type, limit=limit)
        if len(cached_results) >= limit:
            cache_hit = True
            matched = []
            for entry in cached_results[:limit]:
                basic = entry.get("basic_data", {})
                matched.append({
                    "id": entry.get("activity_id"),
                    "name": basic.get("name", "未命名"),
                    "date": (basic.get("start_time") or "")[:10],
                    "distance": basic.get("distance", 0) or 0,
                })

            total_time = time.time() - start_time
            type_name = TRAINING_TYPE_NAMES.get(target_type, target_type)

            output = f"找到 {len(matched)} 个 {type_name} (缓存):\n"
            output += "-" * 50 + "\n"

            for m in matched:
                dist_km = m["distance"] / 1000
                output += f"• {m['date']} | {m['name']} ({dist_km:.1f}km)\n"
                output += f"  ID: {m['id']}\n"

            output += "-" * 50
            output += f"\n💡 可以用活动ID查看详情，如\"分析 {matched[0]['id']} 这次训练\""
            output += f"\n⏱️ 处理时间: {total_time*1000:.1f}ms (缓存命中)"

            logger.info(f"Cache hit for {target_type}: {len(matched)} results in {total_time*1000:.1f}ms")
            return output

    # ==========================================
    # Step 2: Cache miss - use API (fallback)
    # ==========================================
    logger.info(f"Cache miss for {target_type}, falling back to API")

    # 确定日期范围（默认1年，无限制）
    if not end_date:
        end_date = date.today().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")

    # 获取活动列表
    fetch_start = time.time()
    activities = client.get_activities_by_date(start_date, end_date)
    fetch_time = time.time() - fetch_start

    if not activities:
        return f"在 {start_date} 到 {end_date} 期间没有找到活动记录。"

    # 定义处理单个活动的函数
    def process_activity(a):
        """处理单个活动，返回分类结果"""
        activity_id = a.get("activityId")
        activity_type = a.get("activityType", {}).get("typeKey", "")
        event_type = a.get("eventType", {}).get("typeKey", "")
        distance = a.get("distance", 0) or 0

        # 获取心率区间
        try:
            hr_data = client.get_activity_hr_in_timezones(activity_id)
            hr_zones = hr_data.get("timeInHeartRateZones", []) if hr_data else []
        except:
            hr_zones = []

        # 获取分段
        try:
            laps_data = client.get_activity_splits(activity_id)
            laps = laps_data.get("lapDTOs", []) if laps_data else []
        except:
            laps = []

        # 分类
        result = classify_activity(
            activity_type=activity_type,
            event_type=event_type,
            total_distance=distance,
            laps=laps,
            hr_zones=hr_zones,
        )

        return {
            "activity": a,
            "type": result.get("type"),
            "activity_id": activity_id,
        }

    # 并行处理所有活动
    from concurrent.futures import ThreadPoolExecutor, as_completed

    matched = []
    analyze_start = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_activity, a): a for a in activities}

        for future in as_completed(futures):
            if len(matched) >= limit:
                executor.shutdown(wait=False)
                break

            result = future.result()
            if result.get("type") == target_type:
                a = result["activity"]
                matched.append({
                    "id": result["activity_id"],
                    "name": a.get("activityName", "未命名"),
                    "date": (a.get("startTimeLocal") or "")[:10],
                    "distance": a.get("distance", 0) or 0,
                })

    analyze_time = time.time() - analyze_start

    # 格式化输出
    type_name = TRAINING_TYPE_NAMES.get(target_type, target_type)
    total_time = time.time() - start_time

    if not matched:
        return f"在 {start_date} 到 {end_date} 期间没有找到 {type_name} 记录。\n⏱️ 处理时间: {total_time:.2f}s (获取活动: {fetch_time:.2f}s, 分析: {total_time - fetch_time:.2f}s)"

    output = f"找到 {len(matched)} 个 {type_name}:\n"
    output += "-" * 50 + "\n"

    for m in matched:
        dist_km = m["distance"] / 1000
        output += f"• {m['date']} | {m['name']} ({dist_km:.1f}km)\n"
        output += f"  ID: {m['id']}\n"

    output += "-" * 50
    output += f"\n💡 可以用活动ID查看详情，如\"分析 {matched[0]['id']} 这次训练\""
    output += f"\n⏱️ 处理时间: {total_time:.2f}s (获取活动: {fetch_time:.2f}s, 分析: {total_time - fetch_time:.2f}s)"

    return output


# ==========================================
# Deep Analysis Tools (深度分析工具)
# ==========================================

@tool
def compare_interval_trainings(limit: int = 5) -> str:
    """对比最近多次间歇训练的趋势（配速进步/退步、心率漂移变化）。

    当用户问"间歇跑有没有进步"、"对比间歇训练"、"间歇跑趋势"时使用。
    自动搜索最近的间歇训练，提取活跃段数据，横向对比。

    Args:
        limit: 对比最近几次，默认5

    Returns:
        间歇训练对比表格和趋势分析
    """
    from ..interval_analyzer import extract_interval_segments, compare_intervals, _calculate_pace

    client = get_client()

    # 搜索间歇训练
    if _cache is not None:
        cached = _cache.get_all_by_type("interval", limit=limit)
        activities = []
        for entry in cached:
            basic = entry.get("basic_data", {})
            activities.append({
                "activityId": entry.get("activity_id"),
                "activityName": basic.get("name", "未命名"),
                "startTimeLocal": basic.get("start_time", ""),
            })
    else:
        end = date.today().strftime("%Y-%m-%d")
        start = (date.today() - timedelta(days=180)).strftime("%Y-%m-%d")
        all_activities = client.get_activities_by_date(start, end)
        activities = []
        for a in (all_activities or []):
            aid = a.get("activityId")
            laps_data = client.get_activity_splits(aid)
            laps = laps_data.get("lapDTOs", []) if laps_data else []
            active = sum(1 for l in laps if l.get("intensityType") == "ACTIVE")
            recovery = sum(1 for l in laps if l.get("intensityType") == "RECOVERY")
            if active > 5 and recovery > 4:
                activities.append(a)
            if len(activities) >= limit:
                break

    if not activities:
        return "没有找到间歇训练记录。"

    # 分析每次间歇训练
    analyses = []
    for a in activities[:limit]:
        aid = a.get("activityId")
        name = a.get("activityName", "未命名")
        d = (a.get("startTimeLocal") or "")[:10]

        laps_data = client.get_activity_splits(aid)
        laps = laps_data.get("lapDTOs", []) if laps_data else []

        if not laps:
            continue

        analysis = extract_interval_segments(laps)
        if analysis.get("intervals"):
            analyses.append({
                "date": d,
                "name": name,
                "analysis": analysis,
            })

    if len(analyses) < 2:
        if len(analyses) == 1:
            stats = analyses[0]["analysis"]["stats"]
            return f"只找到1次间歇训练 ({analyses[0]['date']}):\n" \
                   f"- 间歇组数: {stats.get('interval_count', 0)}\n" \
                   f"- 平均配速: {_format_pace_sec(stats.get('avg_pace', 0))}\n" \
                   f"- 心率漂移: +{stats.get('hr_drift', 0)} bpm\n" \
                   f"需要至少2次才能对比趋势。"
        return "间歇训练数据不足，无法对比。"

    result = compare_intervals(analyses)
    return result


def _format_pace_sec(pace_seconds: float) -> str:
    """格式化配速（秒/公里）"""
    if pace_seconds <= 0:
        return "N/A"
    minutes = int(pace_seconds // 60)
    seconds = int(pace_seconds % 60)
    return f"{minutes}:{seconds:02d}/km"


@tool
def evaluate_lap_quality(activity_id: int = None) -> str:
    """评估活动每圈的训练质量（圈评分系统）。

    当用户问"这圈跑得怎么样"、"哪圈最好"、"圈质量"、"训练质量"时使用。
    基于 Garmin 的 compliance score 评估每圈质量。

    Args:
        activity_id: 活动ID，不填则查最近一次

    Returns:
        每圈评分、最佳圈、最差圈、整体评级
    """
    from ..coach_evaluator import prepare_coach_evaluation_data

    client = get_client()

    if activity_id is None or activity_id <= 0:
        activities = client.get_activities(limit=1)
        if not activities:
            return "没有找到活动记录。"
        activity_id = activities[0].get("activityId")

    # 获取活动详情和圈数据
    activity = client.get_activity(activity_id)
    if not activity:
        return f"未找到活动 {activity_id}"

    laps_data = client.get_activity_splits(activity_id)
    laps = laps_data.get("lapDTOs", []) if laps_data else None

    # 使用教练评估器分析
    data = prepare_coach_evaluation_data(activity, lap_data=laps)

    summary = activity.get("summaryDTO", {})
    name = activity.get("activityName", "未命名")
    dist_km = (summary.get("distance", 0) or 0) / 1000

    result = f"📊 圈质量评估 - {name}\n"
    result += f"距离: {dist_km:.1f}km | 活动ID: {activity_id}\n"
    result += "=" * 50 + "\n\n"

    # 整体评级
    lap_dist = data["lap_distribution"]
    result += f"【整体评级】{lap_dist['grade']}\n"
    result += f"平均圈评分: {lap_dist['avg_score']}/100\n"
    result += f"总圈数: {lap_dist['total']}\n\n"

    # 圈分布
    result += "【圈评分分布】\n"
    result += f"  🟢 优秀(≥80): {lap_dist['excellent']} 圈\n"
    result += f"  🔵 良好(60-79): {lap_dist['good']} 圈\n"
    result += f"  🟡 一般(40-59): {lap_dist['fair']} 圈\n"
    result += f"  🔴 较差(<40): {lap_dist['poor']} 圈\n\n"

    # 最佳圈
    if data["excellent_laps"]:
        result += "【最佳圈】\n"
        for lap in data["excellent_laps"]:
            result += f"  第{lap['lap_number']}圈: {lap['distance_km']}km, " \
                      f"配速{lap['pace']}/km, 心率{lap['hr']}bpm, 评分{lap['score']}\n"
        result += "\n"

    # 最差圈
    if data["poor_laps"]:
        result += "【需要改进的圈】\n"
        for lap in data["poor_laps"]:
            result += f"  第{lap['lap_number']}圈: {lap['distance_km']}km, " \
                      f"配速{lap['pace']}/km, 心率{lap['hr']}bpm, 评分{lap['score']}\n"
        result += "\n"

    # 训练建议
    if lap_dist['avg_score'] >= 80:
        result += "💡 训练执行力优秀，配速控制稳定！"
    elif lap_dist['avg_score'] >= 60:
        result += "💡 训练质量良好，注意后半程配速保持。"
    elif lap_dist['avg_score'] >= 40:
        result += "💡 训练质量一般，建议关注配速一致性和心率控制。"
    else:
        result += "💡 训练质量需改进，建议降低目标配速，先求稳再求快。"

    return result


@tool
def get_hr_zone_distribution(activity_id: int = None) -> str:
    """展示活动的心率区间详细分布（Z1-Z5占比）。

    当用户问"心率区间分布"、"训练强度分布"、"在哪个区间跑了多久"时使用。
    用柱状图展示每个区间的占比。

    Args:
        activity_id: 活动ID，不填则查最近一次

    Returns:
        心率区间分布（含可视化柱状图）
    """
    client = get_client()

    if activity_id is None or activity_id <= 0:
        activities = client.get_activities(limit=1)
        if not activities:
            return "没有找到活动记录。"
        activity_id = activities[0].get("activityId")

    # 获取活动信息
    activity = client.get_activity(activity_id)
    name = activity.get("activityName", "未命名") if activity else "未知"

    # 获取心率区间数据
    hr_zones_data = client.get_activity_hr_in_timezones(activity_id)
    if not hr_zones_data:
        return f"活动 {activity_id} 没有心率区间数据。"

    hr_zones = hr_zones_data.get("timeInHeartRateZones", [])
    if not hr_zones:
        return f"活动 {activity_id} 心率数据为空。"

    # 使用分类器计算分布
    from ..classifier import _calculate_zone_distribution, classify_activity

    zone_dist = _calculate_zone_distribution(hr_zones)

    # 计算总时间
    total_secs = sum(z.get("secsInZone", 0) for z in hr_zones)

    result = f"❤️ 心率区间分布 - {name}\n"
    result += f"活动ID: {activity_id} | 总时间: {total_secs // 60}分钟\n"
    result += "=" * 50 + "\n\n"

    # 区间含义
    zone_names = {
        1: "Z1 轻松",
        2: "Z2 有氧",
        3: "Z3 节奏",
        4: "Z4 阈值",
        5: "Z5 最大",
    }

    # 柱状图
    for z in range(1, 6):
        pct = zone_dist.get(z, 0)
        bar = "█" * int(pct / 2)  # 每2%一个块
        mins = sum(zn.get("secsInZone", 0) for zn in hr_zones if zn.get("zoneNumber") == z) / 60
        result += f"{zone_names[z]:<10} {pct:5.1f}% {bar} ({mins:.0f}分钟)\n"

    result += "\n"

    # 训练类型判断
    classification = classify_activity(
        activity_type=activity.get("activityType", {}).get("typeKey", "") if activity else "",
        event_type=activity.get("eventType", {}).get("typeKey", "") if activity else "",
        total_distance=activity.get("summaryDTO", {}).get("distance", 0) if activity else 0,
        laps=[],
        hr_zones=hr_zones,
    )

    from ..classifier import TRAINING_TYPE_NAMES
    type_name = TRAINING_TYPE_NAMES.get(classification["type"], classification["type"])
    result += f"📌 训练类型判断: {type_name}\n"
    result += f"   依据: {classification['reason']}\n\n"

    # 强度评估
    z45 = zone_dist.get(4, 0) + zone_dist.get(5, 0)
    z23 = zone_dist.get(2, 0) + zone_dist.get(3, 0)

    if z45 > 30:
        result += "⚠️ 高强度占比偏高，注意恢复。"
    elif z23 > 70:
        result += "✅ 以有氧为主，很好的基础训练。"
    else:
        result += "💡 强度分布均衡。"

    return result


def _infer_date_for_tools(text: str, today=None):
    """把自然语言日期转成 YYYY-MM-DD，供工具函数内部使用。"""
    import re
    from datetime import date, timedelta
    if today is None:
        today = date.today()
    text = text.strip()
    # 直接是 YYYY-MM-DD
    if re.match(r'\d{4}-\d{2}-\d{2}', text):
        return text
    # 昨天 / 今天 / 前天
    if "前天" in text:
        return (today - timedelta(days=2)).strftime("%Y-%m-%d")
    if "昨天" in text:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    if "今天" in text:
        return today.strftime("%Y-%m-%d")
    # 本周 / 上周
    if "上周" in text:
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        return f"{last_monday.strftime('%Y-%m-%d')},{last_sunday.strftime('%Y-%m-%d')}"
    if "本周" in text or "这周" in text:
        monday = today - timedelta(days=today.weekday())
        return f"{monday.strftime('%Y-%m-%d')},{today.strftime('%Y-%m-%d')}"
    # 本月 / 这个月
    if "本月" in text or "这个月" in text:
        first = today.replace(day=1)
        return f"{first.strftime('%Y-%m-%d')},{today.strftime('%Y-%m-%d')}"
    # 上月 / 上个月
    if "上月" in text or "上个月" in text:
        first_this = today.replace(day=1)
        last_month_end = first_this - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return f"{last_month_start.strftime('%Y-%m-%d')},{last_month_end.strftime('%Y-%m-%d')}"
    # X月X日
    m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]', text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = today.year
        try:
            d = date(year, month, day)
            if d > today:
                d = date(year - 1, month, day)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass
    # X天前
    m = re.search(r'(\d+)\s*天前', text)
    if m:
        return (today - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")
    return today.strftime("%Y-%m-%d")


@tool
def filter_laps_by_pace(
    pace_threshold: str = "8:00",
    direction: str = "slower",
    activity_type: str = "running",
    start_date: str = None,
    end_date: str = None,
    limit: int = 20,
) -> str:
    """按配速条件过滤所有活动的圈数据，返回符合条件的圈的完整指标。

    当用户问"配速慢于X的圈"、"哪些圈掉速了"、"配速超过8分钟的圈"时使用。
    自动搜索指定时间范围内的活动，逐圈过滤，返回心率、配速、步频、步幅、垂直振幅。

    Args:
        pace_threshold: 配速阈值，格式 "M:SS"，如 "8:00" 表示 8分钟/公里
        direction: "slower" = 慢于此配速(>阈值)，"faster" = 快于此配速(<阈值)
        activity_type: 活动类型 "running" 或 "hiking"，支持逗号分隔多类型如 "running,hiking"
        start_date: 开始日期，支持自然语言如"本月"、"上周"，默认本月
        end_date: 结束日期，默认今天
        limit: 最多检查多少个活动，默认20

    Returns:
        符合条件的圈的详细数据（配速、心率、步频、步幅、垂直振幅）
    """
    import re as _re
    from datetime import date as _date, timedelta as _timedelta

    client = get_client()

    # 解析配速阈值 → 速度 (m/s)
    m = _re.match(r'(\d+):(\d+)', pace_threshold)
    if not m:
        return f"配速格式错误: {pace_threshold}，请用 M:SS 格式，如 8:00"
    threshold_min = int(m.group(1)) + int(m.group(2)) / 60
    threshold_speed = 1000 / (threshold_min * 60)  # m/s

    # 解析日期
    today = _date.today()
    if start_date:
        sd = _infer_date_for_tools(start_date, today)
        # 如果是范围（含逗号），取第一个
        if "," in sd:
            sd = sd.split(",")[0]
    else:
        sd = today.replace(day=1).strftime("%Y-%m-%d")

    if end_date:
        ed = _infer_date_for_tools(end_date, today)
        if "," in ed:
            ed = ed.split(",")[-1]
    else:
        ed = today.strftime("%Y-%m-%d")

    # 搜索活动 — 支持多种类型（逗号分隔）
    activity_types = [t.strip() for t in activity_type.split(",")]
    activities = []
    for atype in activity_types:
        acts = client.get_activities_by_date(sd, ed, atype) or []
        activities.extend(acts)
    if not activities:
        return f"在 {sd} 到 {ed} 期间没有找到{activity_type}活动。"

    # 逐活动检查圈
    matching_laps = []
    activities_checked = 0

    for a in activities[:limit]:
        aid = a.get("activityId")
        name = a.get("activityName", "未命名")
        a_date = (a.get("startTimeLocal") or "")[:10]

        splits = client.get_activity_splits(aid)
        laps = splits.get("lapDTOs", []) if splits else []
        if not laps:
            continue

        activities_checked += 1
        for i, lap in enumerate(laps, 1):
            speed = lap.get("averageSpeed") or 0
            if speed <= 0:
                continue

            pace_min_km = 1000 / (speed * 60)

            if direction == "slower" and pace_min_km <= threshold_min:
                continue
            if direction == "faster" and pace_min_km >= threshold_min:
                continue

            matching_laps.append({
                "activity_id": aid,
                "activity_name": name,
                "activity_date": a_date,
                "lap_number": i,
                "distance_m": lap.get("distance", 0),
                "pace_min_km": pace_min_km,
                "hr": lap.get("averageHR"),
                "cadence": lap.get("averageRunCadence"),
                "stride_cm": lap.get("strideLength"),
                "vo_cm": lap.get("verticalOscillation"),
                "gct_ms": lap.get("groundContactTime"),
            })

    if not matching_laps:
        dir_text = "慢于" if direction == "slower" else "快于"
        return f"在 {sd} 到 {ed} 期间，检查了 {activities_checked} 个活动，没有找到配速{dir_text}{pace_threshold}/km 的圈。"

    # 格式化输出
    dir_text = "慢于" if direction == "slower" else "快于"
    result = f"🔍 配速{dir_text}{pace_threshold}/km 的圈 ({sd} ~ {ed})\n"
    result += f"共 {len(matching_laps)} 个圈 / 检查了 {activities_checked} 个活动\n"
    result += "=" * 80 + "\n\n"

    # 按活动分组
    from collections import defaultdict
    by_activity = defaultdict(list)
    for lap in matching_laps:
        by_activity[lap["activity_id"]].append(lap)

    for aid, laps in by_activity.items():
        first = laps[0]
        result += f"📌 {first['activity_date']} {first['activity_name']} [ID:{aid}]\n"
        result += f"{'圈':<4} {'距离':<8} {'配速':<10} {'心率':<8} {'步频':<8} {'步幅':<8} {'垂振':<8}\n"
        result += "-" * 70 + "\n"

        for lap in laps:
            dist = f"{lap['distance_m']/1000:.2f}km" if lap['distance_m'] else "--"
            pace = formatters.format_pace_from_min_km(lap['pace_min_km'])
            hr = f"{int(lap['hr'])}bpm" if lap['hr'] else "--"
            cad = f"{int(lap['cadence'])}spm" if lap['cadence'] else "--"
            stride = f"{lap['stride_cm']:.0f}cm" if lap['stride_cm'] else "--"
            vo = f"{lap['vo_cm']:.1f}cm" if lap['vo_cm'] else "--"
            result += f"{lap['lap_number']:<4} {dist:<8} {pace:<10} {hr:<8} {cad:<8} {stride:<8} {vo:<8}\n"
        result += "\n"

    # 汇总统计
    paces = [l['pace_min_km'] for l in matching_laps]
    hrs = [l['hr'] for l in matching_laps if l['hr']]
    result += "📊 汇总:\n"
    result += f"  平均配速: {formatters.format_pace_from_min_km(sum(paces)/len(paces))}\n"
    result += f"  最慢配速: {formatters.format_pace_from_min_km(max(paces))}\n"
    if hrs:
        result += f"  平均心率: {sum(hrs)/len(hrs):.0f} bpm\n"

    return result
