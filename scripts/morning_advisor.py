#!/usr/bin/env python3
"""
morning_advisor.py — 晨起健康建议引擎

复现 design-morning-advisor.md 中全部 8 个算法落点:
  §4.1  个人基线建立 (HRV 7d / RHR 28d / 睡眠 7d)
  §4.2  score_hrv()        — HRV 维度评分 (7 锚点分段线性)
  §4.3  score_rhr()        — RHR 维度评分 (5 锚点分段线性)
  §4.4  score_sleep()      — 睡眠维度评分 (4 子维度加权)
  §4.5  score_readiness()  — 训练准备度评分 (透传)
  §4.6  compute_recovery() — 综合恢复评分 (加权求和 + 分级)
  §4.7  grade_advice()     — 分级标签 + 建议触发条件
  §4.8  check_trend()      — 趋势预警 (连续低分 NFOR 检测)
  §4.9  cross_dimension_validation() — 综合指标逻辑验证矩阵

数据源:
  - data/daily_health.json (本地 JSON, 由 sync_data.py 每日同步)

输出: 结构化 JSON, 供报告层 (morning_report.py / daily_report.py 等) 消费。

用法:
  python scripts/morning_advisor.py [--date 2026-07-14] [--pretty] [--output result.json]

参考: docs/design-morning-advisor.md v1.0 (2026-07-09)
"""

from __future__ import annotations

import json
import math
import sys
import logging
from datetime import date, timedelta, datetime
from pathlib import Path

from dotenv import load_dotenv

from garmin_agent.config import DATA_DIR

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("morning_advisor")

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
HEALTH_JSON = DATA_DIR / "daily_health.json"

# ===========================================================================
# 评分配置 — 所有设计参数集中定义，函数体不出现裸数字
# ===========================================================================

# 睡眠子维度权重 (§4.4)
SLEEP_WEIGHTS = {"duration": 0.30, "deep": 0.35, "rem": 0.15, "awake": 0.20}

# 综合评分权重 (§4.6)
RECOVERY_WEIGHTS = {"hrv": 0.30, "sleep": 0.25, "rhr": 0.20, "readiness": 0.15, "stress": 0.10}

# 分级阈值 (§4.7)
GRADE_THRESHOLDS = [
    (85, "A", "🟢 状态极佳", "EXCELLENT"),
    (70, "B", "🔵 状态良好", "GOOD"),
    (55, "C", "🟡 需要注意", "CAUTION"),
    (40, "D", "🟠 恢复不足", "POOR"),
]

# HRV 评分锚点 (§4.2) — (pct_change, score, zone_label)
HRV_ANCHORS = [
    (0.10,  70, "spike"),
    (0.05,  85, "green_high"),
    (0.00,  75, "green_normal_mid"),
    (-0.05, 60, "green_low_yellow_high"),
    (-0.08, 40, "yellow_low_red_high"),
    (-0.15, 10, "red_deep"),
    (-0.20,  0, "severe"),
]

# RHR 评分锚点 (§4.3) — (deviation_bpm, score, zone_label)
RHR_ANCHORS = [
    (-3,  95, "very_low"),
    ( 0,  75, "baseline"),
    ( 3,  55, "mild_fatigue"),
    ( 6,  30, "fatigue"),
    (10,   0, "severe"),
]

# 压力评分锚点 (§4.x) — (stress_level_0_100, score, zone_label)
# Garmin stress: 0=极低压力, 100=极高压力; 分数反向（低压力=高分）
_STRESS_ANCHORS = [
    ( 0,  95, "very_low"),
    (25,  85, "low"),
    (50,  60, "moderate"),
    (75,  25, "high"),
    (100,  0, "severe"),
]

# --- 从锚点自动派生的分段线性参数 (HRV) ---
# 每段: (p_min, p_max, score_at_p_min, slope, zone_at_segment)
# slope = (score_at_p_max - score_at_p_min) / (p_max - p_min)
_HRV_SEGMENTS = []
for i in range(len(HRV_ANCHORS) - 1):
    p1, s1, z1 = HRV_ANCHORS[i + 1]   # 从低到高排列，取后者作为段起点
    p2, s2, z2 = HRV_ANCHORS[i]
    slope = (s2 - s1) / (p2 - p1)
    _HRV_SEGMENTS.append({"p_min": p1, "p_max": p2, "score_at_min": s1, "slope": slope, "zone": z2})

# Spike 段: p > +0.10，固定分数
_HRV_SPIKE_SCORE = HRV_ANCHORS[0][1]   # 70
_HRV_SPIKE_ZONE  = HRV_ANCHORS[0][2]   # "spike"

# Fallback 值
_HRV_FALLBACK_SCORE = 75
_HRV_FALLBACK_ZONE  = "FALLBACK"
_RHR_FALLBACK_SCORE = 75

# --- 从锚点自动派生的分段线性参数 (RHR) ---
_RHR_SEGMENTS = []
for i in range(len(RHR_ANCHORS) - 1):
    p1, s1, _ = RHR_ANCHORS[i]
    p2, s2, z2 = RHR_ANCHORS[i + 1]
    slope = (s2 - s1) / (p2 - p1)
    _RHR_SEGMENTS.append({"p_min": p1, "p_max": p2, "score_at_min": s1, "slope": slope, "zone": z2})

# --- 从锚点自动派生的分段线性参数 (压力) ---
_STRESS_SEGMENTS = []
for i in range(len(_STRESS_ANCHORS) - 1):
    p1, s1, z1 = _STRESS_ANCHORS[i]
    p2, s2, z2 = _STRESS_ANCHORS[i + 1]
    slope = (s2 - s1) / (p2 - p1)
    _STRESS_SEGMENTS.append({"p_min": p1, "p_max": p2, "score_at_min": s1, "slope": slope, "zone": z2})

# --- 睡眠维度分段阈值 (§4.4) ---

# 时长评分锚点: (hours_threshold, score)
_SLEEP_DURATION_ANCHORS = [
    (5,  10),
    (6,  45),
    (7,  80),
    (9,  100),
]
_SLEEP_DURATION_MAX_SCORE = 100
_SLEEP_DURATION_EXCESS_DECAY = 20   # 每超1h扣20分，下限50

# 深睡占比评分锚点: (pct_threshold, score)
_SLEEP_DEEP_ANCHORS = [
    (5,  20),
    (10, 60),
    (25, 100),
]
_SLEEP_DEEP_MAX_SCORE = 90

# REM 占比评分锚点: (pct_threshold, score)
_SLEEP_REM_ANCHORS = [
    (10, 30),
    (18, 50),
    (25, 100),
]
_SLEEP_REM_MAX_SCORE = 85

# 清醒次数评分 (§4.4)
_AWAKE_SCORES = {0: 100, 1: 80, 2: 60}  # 0/1/2 次对应固定分
_AWAKE_FRAG_BASE  = 45   # ≥3 次起始分
_AWAKE_FRAG_STEP  = 15   # 每多1次扣15分
_AWAKE_FRAG_MIN   = 0    # 下限

# --- 训练准备度分级阈值 ---
_READINESS_GREEN_THRESHOLD = 80
_READINESS_YELLOW_THRESHOLD = 60

# --- 趋势预警参数 (§4.8) ---
_TREND_WINDOW  = 5
_TREND_THRESHOLD = 60
_TREND_STREAK  = 3

# --- 综合验证矩阵阈值 (§4.9) ---
# IDEAL_RECOVERY
_VAL_HRV_OK       = -5    # HRV 不低于基线 5%
_VAL_RHR_NEUTRAL  = 3     # RHR 偏移 ±3 内
_VAL_SLEEP_OK     = 7     # 睡眠 ≥7h
_VAL_AWAKE_OK     = 1     # 清醒 ≤1 次
# SYMPATHETIC_FATIGUE
_VAL_HRV_FATIGUE  = -8
_VAL_RHR_FATIGUE  = 3
_VAL_SLEEP_BAD    = 6
_VAL_AWAKE_BAD    = 3
# PARASYMPATHETIC_REBOUND
_VAL_HRV_SPIKE    = 10
_VAL_RHR_LOW      = -3
# SLEEP_DEBT
_VAL_HRV_DEBT     = -8
_VAL_RHR_DEBT     = 3
_VAL_DEEP_LOW     = 10
# HIGH_LOAD_ADAPTATION
_VAL_HRV_LOAD     = -5
_VAL_RHR_LOAD_MAX = 3

# --- 历史数据窗口 (§4.1) ---
_HRV_HISTORY_DAYS  = 14
_RHR_HISTORY_DAYS  = 28
_SLEEP_HISTORY_DAYS = 7
_READINESS_HISTORY_DAYS = 7

# --- 秒/小时换算 ---
_SECS_PER_HOUR = 3600


# ===========================================================================
#  §4.1  个人基线建立
# ===========================================================================

def _safe_mean(values: list[float]) -> float:
    """安全均值, 空列表返回 0。"""
    return round(sum(values) / len(values)) if values else 0


def compute_baselines(
    hrv_14d: list[dict],
    rhr_28d: list[dict],
    sleep_7d: list[dict],
    fallback_hrv_weekly_avg: float = 0,
) -> dict:
    """
    计算三条基线 (§4.1)。

    参数:
        hrv_14d:    [{date, value}, ...]  最多 14 条, 降序
        rhr_28d:    [{date, value}, ...]  最多 28 条, 降序
        sleep_7d:   [{date, total_sec, deep_sec}, ...] 最多 7 条, 降序
        fallback_hrv_weekly_avg: JSON 无 weekly_avg 时的回退值

    返回:
        {
          "hrv_baseline_7d": int,          # Plews 2014: 7 天最小窗口
          "rhr_baseline_28d": int,         # Bosquet 2003: 28 天覆盖微周期
          "sleep_baseline_7d": {
              "total_seconds": int,
              "total_hours": float,
              "deep_pct_avg": float,       # Ohayon 2004: 个体趋势监控
          },
          "formulas": { ... }
        }
    """
    # HRV: 取全部有效值均值 (输入已限制 14d, 实际 ≥7d 有效值即可)
    hrv_vals = [h["value"] for h in hrv_14d if h.get("value", 0) > 0]
    hrv_baseline_7d = _safe_mean(hrv_vals) if hrv_vals else (int(fallback_hrv_weekly_avg) if fallback_hrv_weekly_avg > 0 else 0)

    # RHR: 取全部有效值均值 (输入已限制 28d)
    rhr_vals = [h["value"] for h in rhr_28d if h.get("value", 0) > 0]
    rhr_baseline_28d = _safe_mean(rhr_vals)

    # 睡眠: 总时长均值 + 深睡占比均值
    sleep_tots = [h["total_sec"] for h in sleep_7d if h.get("total_sec", 0) > 0]
    sleep_base_7d = _safe_mean(sleep_tots)

    deep_pcts = []
    for h in sleep_7d:
        ts = h.get("total_sec", 0)
        ds = h.get("deep_sec", 0)
        if ts > 0:
            deep_pcts.append(ds / ts * 100)
    deep_base_7d = round(sum(deep_pcts) / len(deep_pcts), 1) if deep_pcts else 0.0

    return {
        "hrv_baseline_7d": hrv_baseline_7d,
        "rhr_baseline_28d": rhr_baseline_28d,
        "sleep_baseline_7d": {
            "total_seconds": sleep_base_7d,
            "total_hours": round(sleep_base_7d / _SECS_PER_HOUR, 2),
            "deep_pct_avg": deep_base_7d,
        },
        "formulas": {
            "hrv_baseline": "rolling_mean(last_7_nights_HRV), Plews 2014 [R7]",
            "rhr_baseline": "rolling_mean(last_28_days_RHR), Bosquet 2003 [R12]",
            "sleep_baseline": "rolling_mean(last_7_days_total_sleep), Ohayon 2004 [R16]",
        },
    }


# ===========================================================================
#  §4.2  score_hrv() — HRV 维度评分
# ===========================================================================

def score_hrv(last_night: float, weekly: float) -> dict:
    """
    HRV 恢复评分 — 基于对数偏差的分段线性插值 (§4.2)。

    输入:
        last_night: 昨晚 HRV 均值 (ms), 无数据时传 0
        weekly:     7 天 HRV 均值 (ms), 无数据时传 0

    返回:
        {
          "score": int (0-100),
          "zone": str,
          "fallback_used": bool,
          "ln_last_night": float | None,
          "ln_baseline": float | None,
          "pct_change": float | None,
          "pct_change_pct": float | None,
          "anchors": [...]
        }
    """
    result: dict = {
        "last_night_ms": last_night,
        "weekly_avg_ms": weekly,
        "fallback_used": False,
        "ln_last_night": None,
        "ln_baseline": None,
        "pct_change": None,
        "pct_change_pct": None,
        "anchors": [
            {"pct_change": a, "score": s, "label": l} for a, s, l in HRV_ANCHORS
        ],
    }

    if last_night <= 0 or weekly <= 0:
        result.update({"score": _HRV_FALLBACK_SCORE, "zone": _HRV_FALLBACK_ZONE})
        return result

    cl = math.log(last_night)
    bl = math.log(weekly)
    p = (cl - bl) / bl

    result["ln_last_night"] = round(cl, 4)
    result["ln_baseline"] = round(bl, 4)
    result["pct_change"] = round(p, 6)
    result["pct_change_pct"] = round(p * 100, 2)

    # Spike 段: p > +0.10，固定分数 (锚点列表首个元素的 pct_change 值)
    if p > HRV_ANCHORS[0][0]:
        s, z = _HRV_SPIKE_SCORE, _HRV_SPIKE_ZONE
    else:
        # 逐段查找（最多 6 段，线性扫描足够）
        for seg in _HRV_SEGMENTS:
            if seg["p_min"] <= p <= seg["p_max"]:
                s = seg["score_at_min"] + (p - seg["p_min"]) * seg["slope"]
                z = seg["zone"]
                break
        else:
            s, z = 0, "SEVERE"

    result["score"] = round(min(100, max(0, s)))
    result["zone"] = z
    return result


# ===========================================================================
#  §4.3  score_rhr() — RHR 维度评分
# ===========================================================================

def score_rhr(current_rhr: float, baseline_rhr_28d: float) -> dict:
    """
    静息心率评分 — 基于与 28 天基线偏差的分段线性插值 (§4.3)。

    输入:
        current_rhr:     当日静息心率 (bpm)
        baseline_rhr_28d: 28 天滚动均值 (bpm)

    返回:
        {
          "score": int (0-100),
          "zone": str,
          "deviation": int (bpm),
          "deviation_bpm": str (e.g. "+1 bpm"),
          "anchors": [...]
        }
    """
    d = current_rhr - baseline_rhr_28d

    result: dict = {
        "current_bpm": current_rhr,
        "baseline_bpm": baseline_rhr_28d,
        "deviation": d,
        "deviation_bpm": f"{d:+d} bpm",
        "anchors": [
            {"deviation_bpm": a, "score": s, "label": l} for a, s, l in RHR_ANCHORS
        ],
    }

    # 逐段查找
    for seg in _RHR_SEGMENTS:
        if seg["p_min"] <= d <= seg["p_max"]:
            s = seg["score_at_min"] + (d - seg["p_min"]) * seg["slope"]
            z = seg["zone"]
            break
    else:
        # d < 最左锚点 (-3)
        s, z = RHR_ANCHORS[0][1], RHR_ANCHORS[0][2]

    result["score"] = round(min(100, max(0, s)))
    result["zone"] = z
    return result


# ===========================================================================
#  §4.4  score_sleep() — 睡眠维度评分
# ===========================================================================

def score_sleep(
    total_sec: int,
    deep_sec: int,
    rem_sec: int,
    awake_cnt: int,
    garmin_sleep_score: int | None = None,
) -> dict:
    """
    睡眠质量评分 — 四维度加权融合 (§4.4)。

    输入:
        total_sec:          总睡眠时长 (秒)
        deep_sec:           深睡时长 (秒)
        rem_sec:            REM 时长 (秒)
        awake_cnt:          夜间清醒次数
        garmin_sleep_score: Garmin 自有评分 (0-100), 有则优先透传

    返回:
        {
          "score": int (0-100),
          "garmin_score_used": bool,
          "total_hours": float,
          "deep_pct": float,
          "rem_pct": float,
          "sub_scores": {
              "duration": {"value": float, "zone": str, "weight": 0.30},
              "deep":     {"value": float, "zone": str, "weight": 0.35},
              "rem":      {"value": float, "zone": str, "weight": 0.15},
              "awake":    {"value": float, "zone": str, "weight": 0.20},
          },
          "weights": { ... }
        }
    """
    result: dict = {
        "total_seconds": total_sec,
        "deep_seconds": deep_sec,
        "rem_seconds": rem_sec,
        "awake_count": awake_cnt,
        "garmin_score_used": False,
    }

    # 优先使用 Garmin 自有评分 (§4.4: garmin_sleep_score 透传)
    if garmin_sleep_score is not None:
        result["garmin_score_used"] = True
        result["score"] = garmin_sleep_score
        result["sub_scores"] = {}
        return result

    result["garmin_score_used"] = False
    th = total_sec / _SECS_PER_HOUR
    dp = (deep_sec / total_sec * 100) if total_sec > 0 else 0.0
    rp = (rem_sec / total_sec * 100) if total_sec > 0 else 0.0

    result["total_hours"] = round(th, 2)
    result["deep_pct"] = round(dp, 2)
    result["rem_pct"] = round(rp, 2)

    # --- 时长评分 (30%) — Ohayon 2004: 理想 7-9h ---
    dur_anchors = _SLEEP_DURATION_ANCHORS
    if th < dur_anchors[0][0]:
        ds, dz = dur_anchors[0][1], "SEVERE_SHORT"
    elif th < dur_anchors[1][0]:
        # (5h,10) → (6h,45), slope = 35
        ds = round(dur_anchors[0][1] + (th - dur_anchors[0][0]) * 35, 1)
        dz = "SHORT"
    elif th < dur_anchors[2][0]:
        # (6h,45) → (7h,80), slope = 35
        ds = round(dur_anchors[1][1] + (th - dur_anchors[1][0]) * 35, 1)
        dz = "MODERATE"
    elif th <= dur_anchors[3][0]:
        # (7h,80) → (9h,100), slope = 10
        ds = round(dur_anchors[2][1] + (th - dur_anchors[2][0]) * 10, 1)
        dz = "IDEAL"
    else:
        ds = round(max(50, 100 - (th - dur_anchors[3][0]) * _SLEEP_DURATION_EXCESS_DECAY), 1)
        dz = "EXCESS"

    # --- 深睡占比评分 (35%) — Dijk 2009: 正常 10-25% ---
    deep_anchors = _SLEEP_DEEP_ANCHORS
    if dp < deep_anchors[0][0]:
        des, dez = 20, "SEVERE_LOW"
    elif dp < deep_anchors[1][0]:
        # (5%,20) → (10%,60), slope = 8
        des = round(deep_anchors[0][1] + (dp - deep_anchors[0][0]) * 8, 1)
        dez = "LOW"
    elif dp <= deep_anchors[2][0]:
        # (10%,60) → (25%,100), slope = 40/15
        des = round(deep_anchors[1][1] + (dp - deep_anchors[1][0]) * (40 / 15), 1)
        dez = "IDEAL"
    else:
        des = _SLEEP_DEEP_MAX_SCORE
        dez = "HIGH"

    # --- REM 占比评分 (15%) — Dijk 2009: 正常 18-25% ---
    rem_anchors = _SLEEP_REM_ANCHORS
    if rp < rem_anchors[0][0]:
        res, rez = round(30 + rp * 2, 1), "LOW"
    elif rp < rem_anchors[1][0]:
        # (10%,30) → (18%,50), slope = 2.5
        res = round(rem_anchors[0][1] + (rp - rem_anchors[0][0]) * 2.5, 1)
        rez = "MODERATE"
    elif rp <= rem_anchors[2][0]:
        # (18%,50) → (25%,100), slope = 30/7
        res = round(rem_anchors[1][1] + (rp - rem_anchors[1][0]) * (30 / 7), 1)
        rez = "IDEAL"
    else:
        res = _SLEEP_REM_MAX_SCORE
        rez = "HIGH"

    # --- 清醒次数评分 (20%) — AASM 通用标准 ---
    if awake_cnt in _AWAKE_SCORES:
        aws, az = _AWAKE_SCORES[awake_cnt], ["NONE", "ONCE", "TWICE"][awake_cnt]
    else:
        aws = round(max(_AWAKE_FRAG_MIN, _AWAKE_FRAG_BASE - (awake_cnt - 3) * _AWAKE_FRAG_STEP), 1)
        az = "FRAGMENTED"

    result["sub_scores"] = {
        "duration": {"value": ds, "zone": dz, "weight": SLEEP_WEIGHTS["duration"]},
        "deep":     {"value": des, "zone": dez, "weight": SLEEP_WEIGHTS["deep"]},
        "rem":      {"value": res, "zone": rez, "weight": SLEEP_WEIGHTS["rem"]},
        "awake":    {"value": aws, "zone": az, "weight": SLEEP_WEIGHTS["awake"]},
    }
    result["weights"] = dict(SLEEP_WEIGHTS)

    score = ds * SLEEP_WEIGHTS["duration"] + des * SLEEP_WEIGHTS["deep"] \
         + res * SLEEP_WEIGHTS["rem"]     + aws * SLEEP_WEIGHTS["awake"]
    result["score"] = round(score)
    return result


# ===========================================================================
#  §4.5  score_readiness() — 训练准备度评分
# ===========================================================================

def score_readiness(garmin_score: int) -> dict:
    """
    训练准备度评分 — 透传 Garmin 自有分数 (§4.5)。

    Garmin Training Readiness 已内部融合 HRV / 睡眠 / 压力 / ACWR,
    此处仅做上限裁剪和 zone 标记, 不重复计算。

    输入:
        garmin_score: Garmin trainingReadinessScore (0-100)

    返回:
        {
          "score": int (0-100),
          "original_score": int,
          "zone": "GREEN" | "YELLOW" | "RED"
        }
    """
    capped = min(garmin_score, 100)
    if capped >= _READINESS_GREEN_THRESHOLD:
        zone = "GREEN"
    elif capped >= _READINESS_YELLOW_THRESHOLD:
        zone = "YELLOW"
    else:
        zone = "RED"
    return {
        "original_score": garmin_score,
        "score": capped,
        "zone": zone,
    }


# ===========================================================================
#  §4.x  score_stress() — 压力维度评分
# ===========================================================================

def score_stress(stress_level: int | float) -> dict:
    """
    压力维度评分 — Garmin avgStressLevel 反向映射 (§4.x)。

    输入:
        stress_level: Garmin 平均压力等级 (0-100, 越低越好)

    返回:
        {
          "score": int (0-100),
          "zone": str,
          "stress_level": int,
          "anchors": [...]
        }
    """
    s = max(0, min(100, int(stress_level)))

    result: dict = {
        "stress_level": s,
        "anchors": [
            {"stress_level": a, "score": sc, "label": l} for a, sc, l in _STRESS_ANCHORS
        ],
    }

    for seg in _STRESS_SEGMENTS:
        if seg["p_min"] <= s <= seg["p_max"]:
            score = seg["score_at_min"] + (s - seg["p_min"]) * seg["slope"]
            zone = seg["zone"]
            break
    else:
        score, zone = 0, "SEVERE"

    result["score"] = round(min(100, max(0, score)))
    result["zone"] = zone
    return result


# ===========================================================================
#  §4.6  compute_recovery() — 综合恢复评分
# ===========================================================================

def compute_recovery(
    hrv_score: int,
    sleep_score: int,
    rhr_score: int,
    readiness_score: int,
    stress_score: int = 0,
) -> dict:
    """
    综合恢复评分 — 加权求和 + 分级 (§4.6)。

    公式:
        recovery = HRV x 0.30 + Sleep x 0.25 + RHR x 0.20 + Readiness x 0.15 + Stress x 0.10

    分级:
        A ≥ 85  B ≥ 70  C ≥ 55  D ≥ 40  F < 40

    返回:
        {
          "recovery_score": int (0-100),
          "grade": "A" | "B" | "C" | "D" | "F",
          "label": str (emoji + 中文),
          "zone": str,
          "calculation_steps": [str, ...],
          "formula": str,
          "weights": {...},
          "reference": str
        }
    """
    score = round(
        hrv_score * RECOVERY_WEIGHTS["hrv"]
        + sleep_score * RECOVERY_WEIGHTS["sleep"]
        + rhr_score * RECOVERY_WEIGHTS["rhr"]
        + readiness_score * RECOVERY_WEIGHTS["readiness"]
        + stress_score * RECOVERY_WEIGHTS["stress"]
    )
    score = max(0, min(100, score))

    # 分级 (§4.7 阈值)
    if score >= 85:
        grade, label, zone = "A", "🟢 状态极佳", "EXCELLENT"
    elif score >= 70:
        grade, label, zone = "B", "🔵 状态良好", "GOOD"
    elif score >= 55:
        grade, label, zone = "C", "🟡 需要注意", "CAUTION"
    elif score >= 40:
        grade, label, zone = "D", "🟠 恢复不足", "POOR"
    else:
        grade, label, zone = "F", "🔴 需要休息", "CRITICAL"

    steps = [
        f"HRV: {hrv_score} x 0.30 = {hrv_score * 0.30:.2f}",
        f"Sleep: {sleep_score} x 0.25 = {sleep_score * 0.25:.2f}",
        f"RHR: {rhr_score} x 0.20 = {rhr_score * 0.20:.2f}",
        f"Readiness: {readiness_score} x 0.15 = {readiness_score * 0.15:.2f}",
        f"Stress: {stress_score} x 0.10 = {stress_score * 0.10:.2f}",
        f"Total: {hrv_score * 0.30 + sleep_score * 0.25 + rhr_score * 0.20 + readiness_score * 0.15 + stress_score * 0.10:.2f} -> {score}",
    ]

    return {
        "recovery_score": score,
        "weights": dict(RECOVERY_WEIGHTS),
        "grade": grade,
        "label": label,
        "zone": zone,
        "calculation_steps": steps,
        "formula": "recovery = HRV x 0.30 + Sleep x 0.25 + RHR x 0.20 + Readiness x 0.15 + Stress x 0.10",
        "reference": "§4.6, [R2] Buchheit 2014, [R16] Ohayon 2004, [R12] Bosquet 2003, [R21] Garmin",
    }


# ===========================================================================
#  §4.8  check_trend() — 趋势预警 (连续低分 NFOR 检测)
# ===========================================================================

def check_trend(recent_scores: list[int], window: int = _TREND_WINDOW, threshold: int = _TREND_THRESHOLD, streak: int = _TREND_STREAK) -> dict:
    """
    趋势预警 — 连续低分检测 (§4.8)。

    逻辑:
        在最近 window 天中, 连续 streak 天 score < threshold
        触发 Plews 2013 NFOR 高风险预警。

    输入:
        recent_scores: 最近 N 天的恢复评分列表 (降序, 最新在末尾)
        window:        检查窗口天数 (默认 5)
        threshold:     低分阈值 (默认 60)
        streak:        连续天数 (默认 3)

    返回:
        {
          "low_streak": int,
          "window_checked": int,
          "threshold": int,
          "alert": str | None,
          "recent_scores_in_window": [int, ...]
        }
    """
    window_scores = recent_scores[-window:] if len(recent_scores) >= window else list(recent_scores)

    low_streak = 0
    max_streak = 0
    for s in window_scores:
        if s < threshold:
            low_streak += 1
            max_streak = max(max_streak, low_streak)
        else:
            low_streak = 0

    alert = None
    if max_streak >= streak:
        alert = (
            f"⚠️ 连续 {max_streak} 天恢复评分 < {threshold} — "
            "Plews(2013) 框架下 NFOR 高风险。建议安排主动恢复日。"
        )

    return {
        "low_streak": max_streak,
        "window_checked": len(window_scores),
        "threshold": threshold,
        "alert": alert,
        "recent_scores_in_window": window_scores,
    }


# ===========================================================================
#  §4.9  cross_dimension_validation() — 综合指标逻辑验证矩阵
# ===========================================================================

def cross_dimension_validation(
    hrv_pct: float,
    rhr_dev: int,
    sleep_hours: float,
    awake_cnt: int,
    deep_pct: float,
) -> dict:
    """
    5 种复合情景的交叉解读 (§4.9)。

    输入:
        hrv_pct:     HRV 相对基线的百分比变化
        rhr_dev:     RHR 相对基线的偏移量 (bpm)
        sleep_hours: 总睡眠时长 (小时)
        awake_cnt:   夜间清醒次数
        deep_pct:    深睡占比 (%)

    返回:
        {
          "num_patterns_checked": 5,
          "patterns_checked": [...],
          "num_matched": int,
          "matched_patterns": [...]
        }
    """
    patterns = [
        {
            "id": "IDEAL_RECOVERY",
            "label": "理想恢复",
            "condition_desc": "HRV↑↑ RHR↓→ 睡眠优",
            "ref": "[R2] Buchheit 2014",
            "match": (hrv_pct >= -_VAL_HRV_OK
                      and abs(rhr_dev) <= _VAL_RHR_NEUTRAL
                      and sleep_hours >= _VAL_SLEEP_OK
                      and awake_cnt <= _VAL_AWAKE_OK),
        },
        {
            "id": "SYMPATHETIC_FATIGUE",
            "label": "交感疲劳",
            "condition_desc": "HRV↓↓ RHR↑↑ 睡眠差",
            "ref": "[R10] Plews 2013",
            "match": (hrv_pct < -_VAL_HRV_FATIGUE
                      and rhr_dev > _VAL_RHR_FATIGUE
                      and (sleep_hours < _VAL_SLEEP_BAD or awake_cnt >= _VAL_AWAKE_BAD)),
        },
        {
            "id": "PARASYMPATHETIC_REBOUND",
            "label": "副交感反弹",
            "condition_desc": "HRV↑↑↑ RHR↓↓ 睡眠中",
            "ref": "[R9] Recovery Tower Spike",
            "match": hrv_pct > _VAL_HRV_SPIKE and rhr_dev < _VAL_RHR_LOW,
        },
        {
            "id": "SLEEP_DEBT",
            "label": "睡眠债务疲劳",
            "condition_desc": "HRV↓ RHR→ 睡眠差·短",
            "ref": "[R16] Ohayon 2004",
            "match": (-_VAL_HRV_DEBT <= hrv_pct < -_VAL_HRV_OK
                      and abs(rhr_dev) <= _VAL_RHR_NEUTRAL
                      and (sleep_hours < _VAL_SLEEP_BAD or deep_pct < _VAL_DEEP_LOW)),
        },
        {
            "id": "HIGH_LOAD_ADAPTATION",
            "label": "高负荷适应",
            "condition_desc": "HRV↓ RHR↑ 睡眠中",
            "ref": "[R22] Chalencon 2012",
            "match": hrv_pct < -_VAL_HRV_LOAD and 0 < rhr_dev <= _VAL_RHR_LOAD_MAX,
        },
    ]

    matched = [p for p in patterns if p["match"]]
    return {
        "num_patterns_checked": len(patterns),
        "patterns_checked": patterns,
        "num_matched": len(matched),
        "matched_patterns": matched,
    }


# ===========================================================================
#  数据获取层 (JSON 本地数据)
# ===========================================================================

def fetch_from_db(target_date: str | None = None) -> dict | None:
    """从 data/daily_health.json 获取数据 + 历史基线。"""
    if not HEALTH_JSON.exists():
        logger.warning("[json] 数据文件不存在: %s", HEALTH_JSON)
        return None

    with open(HEALTH_JSON, encoding="utf-8") as f:
        data = json.load(f)

    days = data.get("days", {})
    if not days:
        logger.warning("[json] 数据文件为空")
        return None

    valid_dates = sorted(days.keys(), reverse=True)
    latest = valid_dates[0]
    target = target_date if target_date in days else latest
    if target not in days:
        logger.info("[json] %s 不存在, 使用最新: %s", target, latest)
        target = latest

    logger.info("[json] 使用数据: %s (最新: %s)", target, latest)
    day = days[target]

    # 清醒次数: JSON 中 awake_count 由 sync_data.py 直接从 API 的 awakeCount 写入
    awake_cnt = day.get("awake_count") or 0

    # 历史过滤
    hrv_14d = _filter_valid(days, "hrv_last_night_avg", _HRV_HISTORY_DAYS)
    rhr_28d = _filter_valid(days, "resting_hr", _RHR_HISTORY_DAYS)

    sleep_7d = []
    for d, v in sorted(days.items(), reverse=True)[:_SLEEP_HISTORY_DAYS]:
        if isinstance(v, dict) and v.get("sleep_seconds"):
            sleep_7d.append({
                "date": d,
                "total_sec": int(v["sleep_seconds"]),
                "deep_sec":  int(v.get("deep_sleep_seconds") or 0),
            })

    rd_7d = _filter_valid(days, "training_readiness_score", _READINESS_HISTORY_DAYS)
    rd_7d_full = [
        {"date": r["date"], "score": r["value"],
         "level": days[r["date"]].get("training_readiness_level", "")}
        for r in rd_7d
    ]

    return {
        "source": "local_json",
        "has_data": True,
        "date": target,
        "latest_db_date": latest,
        "hrv_raw": {
            "last_night": day.get("hrv_last_night_avg") or 0,
            "weekly_avg": day.get("hrv_weekly_avg") or 0,
            "status":     day.get("hrv_status") or "",
        },
        "rhr_raw": day.get("resting_hr") or 0,
        "stress_raw": {
            "avg_stress_level": day.get("avg_stress_level") or 0,
            "max_stress_level": day.get("max_stress_level") or 0,
        },
        "sleep_raw": {
            "total_seconds":    int(day.get("sleep_seconds") or 0),
            "deep_seconds":     int(day.get("deep_sleep_seconds") or 0),
            "rem_seconds":      int(day.get("rem_sleep_seconds") or 0),
            "awake_count":      awake_cnt,
            "garmin_sleep_score": day.get("sleep_score"),
        },
        "readiness_raw": {
            "score": day.get("training_readiness_score") or 0,
            "level": day.get("training_readiness_level") or "",
        },
        "history": {
            "hrv_14d": hrv_14d,
            "rhr_28d": rhr_28d,
            "sleep_7d": sleep_7d,
            "readiness_7d": rd_7d_full,
        },
        "profile": {
            "vo2max": day.get("vo2_max") or "",
            "bmi":    day.get("bmi"),
            "training_load": day.get("training_load"),
            "training_status": day.get("training_status"),
            "device": "Garmin",
        },
    }


def _filter_valid(days: dict, field: str, max_days: int) -> list[dict]:
    """过滤有效历史记录, 降序, 最多 max_days 条。"""
    items = [
        {"date": d, "value": v[field]}
        for d, v in days.items()
        if isinstance(v, dict) and v.get(field) is not None
    ]
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:max_days]


# ===========================================================================
#  主流程: MorningAdvisor
# ===========================================================================

class MorningAdvisor:
    """
    晨起健康建议引擎 — 单次调用跑完全部 8 个算法落点。

    用法:
        advisor = MorningAdvisor(date_str="2026-07-14")
        result = advisor.run()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    """

    def __init__(self, date_str: str | None = None):
        self.target_date = date_str or date.today().strftime("%Y-%m-%d")

    # ------------------------------------------------------------------
    #  数据获取
    # ------------------------------------------------------------------
    def _fetch_data(self) -> dict:
        """从 data/daily_health.json 获取数据。返回统一数据字典。"""
        db_data = fetch_from_db(self.target_date)

        if db_data:
            return db_data

        # 无任何数据
        return {"source": "empty", "has_data": False, "date": self.target_date}

    # ------------------------------------------------------------------
    #  核心计算
    # ------------------------------------------------------------------
    def _compute(self, data: dict) -> dict:
        """执行全部 8 个算法落点。"""
        result: dict = {
            "date": self.target_date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "engine_version": "1.0",
            "design_doc": "docs/design-morning-advisor.md",
            "data_source": data.get("source", "unknown"),
        }

        if not data.get("has_data"):
            result["error"] = "无可用数据源"
            return result

        history = data.get("history", {})
        profile = data.get("profile", {})

        # ---- §4.1 基线 ----
        baselines = compute_baselines(
            hrv_14d=history.get("hrv_14d", []),
            rhr_28d=history.get("rhr_28d", []),
            sleep_7d=history.get("sleep_7d", []),
            fallback_hrv_weekly_avg=data.get("hrv_raw", {}).get("weekly_avg", 0),
        )
        result["baselines"] = baselines

        # ---- §4.2 HRV 评分 ----
        last_hrv = data["hrv_raw"].get("last_night") or data["hrv_raw"].get("weekly_avg") or 0
        hrv_result = score_hrv(last_hrv, baselines["hrv_baseline_7d"])

        # ---- §4.3 RHR 评分 ----
        rhr_result = score_rhr(data["rhr_raw"], baselines["rhr_baseline_28d"])

        # ---- §4.4 睡眠评分 ----
        sleep_result = score_sleep(
            data["sleep_raw"]["total_seconds"],
            data["sleep_raw"]["deep_seconds"],
            data["sleep_raw"]["rem_seconds"],
            data["sleep_raw"]["awake_count"],
            data["sleep_raw"].get("garmin_sleep_score"),
        )

        # ---- §4.5 准备度评分 ----
        readiness_result = score_readiness(data["readiness_raw"].get("score") or 0)

        # ---- §4.x 压力评分 ----
        stress_level = data.get("stress_raw", {}).get("avg_stress_level") or 0
        stress_result = score_stress(stress_level)

        # 维度汇总
        result["dimension_scores"] = {
            "hrv":      hrv_result,
            "rhr":      rhr_result,
            "sleep":    sleep_result,
            "readiness": readiness_result,
            "stress":   stress_result,
        }

        # ---- §4.6 综合恢复评分 ----
        recovery = compute_recovery(
            hrv_result["score"],
            sleep_result["score"],
            rhr_result["score"],
            readiness_result["score"],
            stress_result["score"],
        )
        result["composite"] = recovery

        # ---- §4.9 综合验证矩阵 ----
        hrv_pct   = hrv_result.get("pct_change_pct") or 0
        rhr_dev   = rhr_result["deviation"]
        sleep_h   = data["sleep_raw"]["total_seconds"] / _SECS_PER_HOUR if data["sleep_raw"]["total_seconds"] else 0
        awake_cnt = data["sleep_raw"]["awake_count"]
        deep_pct  = (data["sleep_raw"]["deep_seconds"] / data["sleep_raw"]["total_seconds"] * 100
                     if data["sleep_raw"]["total_seconds"] > 0 else 0)
        result["multi_dimension_validation"] = cross_dimension_validation(
            hrv_pct, rhr_dev, sleep_h, awake_cnt, deep_pct,
        )

        # ---- §4.8 趋势预警 ----
        # 构建最近 5 天 readiness 评分序列作为趋势输入
        rd_scores = [r["score"] for r in history.get("readiness_7d", [])]
        # 补充当日
        rd_scores.append(readiness_result["score"])
        result["trend"] = check_trend(rd_scores)

        # ---- 衍生指标汇总 (供报告层使用) ----
        result["derived_metrics_summary"] = {
            "hrv_pct_change":        hrv_pct,
            "hrv_ln_change":         hrv_result.get("pct_change"),
            "rhr_deviation_bpm":     rhr_dev,
            "sleep_total_hours":     round(sleep_h, 2),
            "sleep_deep_pct":        deep_pct,
            "sleep_rem_pct":         sleep_result.get("rem_pct", 0),
            "stress_level":          stress_level,
            "stress_score":          stress_result["score"],
            "stress_zone":           stress_result["zone"],
            "training_load":         profile.get("training_load", 0),
            "acwr_percent":          profile.get("acwr_percent", 0),
            "readiness_score_original": data["readiness_raw"].get("score", 0),
        }

        return result

    # ------------------------------------------------------------------
    #  公开接口
    # ------------------------------------------------------------------
    def run(self, pretty: bool = False, output_path: str | None = None) -> dict:
        """
        执行完整分析流程。

        返回结构化 dict (可直接 json.dumps)。
        如果指定 output_path, 同时写入 JSON 文件。
        """
        print(f"🏃 Morning Advisor — {self.target_date}")
        print(f"  数据源: data/daily_health.json")

        # 数据
        data = self._fetch_data()
        logger.info("数据源: %s", data.get("source"))

        # 计算
        result = self._compute(data)

        # 输出
        output = json.dumps(result, ensure_ascii=False, indent=2 if pretty else None)

        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output, encoding="utf-8")
            print(f"  📝 JSON → {path}")

        if pretty:
            print()
            print(output)

        if result.get("composite"):
            comp = result["composite"]
            print(f"  ✅ 恢复评分: {comp['recovery_score']} ({comp['grade']} {comp['label']})")

        if result.get("trend", {}).get("alert"):
            print(f"  ⚠️  {result['trend']['alert']}")

        return result


# ===========================================================================
#  CLI
# ===========================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="晨起健康建议引擎 — 复现 design-morning-advisor.md 全部 8 个算法落点",
    )
    parser.add_argument("--date", "-d", type=str, help="目标日期 YYYY-MM-DD (默认今天)")
    parser.add_argument("--pretty", "-p", action="store_true", help="美化输出 JSON")
    parser.add_argument("--output", "-o", type=str, help="输出 JSON 文件路径")
    args = parser.parse_args()

    advisor = MorningAdvisor(date_str=args.date)
    result = advisor.run(pretty=args.pretty, output_path=args.output)

    if result.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
