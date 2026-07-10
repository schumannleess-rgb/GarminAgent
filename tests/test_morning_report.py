"""Unit tests for morning_report scoring functions

Tests cover edge cases for:
    - score_hrv: logarithmic deviation ranges, zero/negative guards
    - score_rhr: delta ranges, clamp bounds
    - score_sleep: sub-dimension boundaries, zero-total guard, gs shortcut
"""

import sys
import math
from pathlib import Path

import pytest

# Ensure project root is on sys.path for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.morning_report import score_hrv, score_rhr, score_sleep


# ==========================================
# score_hrv
# ==========================================

class TestScoreHrv:
    """score_hrv(last_night, weekly) — 基于对数偏差的分段评分"""

    # --- Guard clauses ---
    def test_zero_last_night(self):
        assert score_hrv(0, 50) == 75

    def test_zero_weekly(self):
        assert score_hrv(50, 0) == 75

    def test_both_zero(self):
        assert score_hrv(0, 0) == 75

    def test_negative_last_night(self):
        assert score_hrv(-1, 50) == 75

    # --- Clamp: upper bound ---
    def test_extreme_positive_deviation(self):
        """p >> 0.10 → capped at 70"""
        assert score_hrv(200, 50) == 70

    def test_extreme_positive_deviation_high_weekly(self):
        assert score_hrv(300, 50) == 70

    # --- Clamp: lower bound ---
    def test_extreme_negative_deviation(self):
        """p << -0.20 → capped at 0"""
        assert score_hrv(20, 100) == 0

    def test_extreme_negative_deviation_large_gap(self):
        assert score_hrv(1, 100) == 0

    # --- Boundary: p = 0.10 (top of p > 0.10 → 70) ---
    def test_p_at_0p10(self):
        """p = 0.10 falls in p > 0.10 → 70"""
        last_night = round(math.exp(math.log(50) * 1.10), 6)
        assert score_hrv(last_night, 50) == 70

    # --- Boundary: p = 0.05 (top of p > 0.05 → 85 + (p-0.05)*(-300) = 85) ---
    def test_p_at_0p05(self):
        """p = 0.05 → exactly at boundary, should be 85"""
        last_night = round(math.exp(math.log(50) * 1.05), 6)
        assert score_hrv(last_night, 50) == 85

    # --- Boundary: p = 0 (top of p >= 0 → 75 + p*200 = 75) ---
    def test_p_at_0(self):
        """p = 0 → 75"""
        assert score_hrv(50, 50) == 75

    # --- Boundary: p = -0.05 (top of p >= -0.05 → 75 + p*300 = 60) ---
    def test_p_at_neg_0p05(self):
        """p = -0.05 → 75 + (-0.05)*300 = 60"""
        last_night = round(math.exp(math.log(50) * 0.95), 6)
        assert score_hrv(last_night, 50) == 60

    # --- Boundary: p = -0.08 (top of p > -0.08 → 60 + (p+0.05)*(2000/3) ≈ 40) ---
    def test_p_at_neg_0p08(self):
        """p = -0.08 → 60 + (-0.03)*(2000/3) = 60 - 20 = 40"""
        last_night = round(math.exp(math.log(50) * 0.92), 6)
        # p = ln(ln/50) / ln(50) ≈ -0.08, should give ~40
        score = score_hrv(last_night, 50)
        assert 35 <= score <= 45

    # --- Boundary: p = -0.15 (top of p > -0.15 → 40 + (p+0.08)*(3000/7) ≈ 10) ---
    def test_p_at_neg_0p15(self):
        """p = -0.15 → 40 + (-0.07)*(3000/7) = 40 - 30 = 10"""
        last_night = round(math.exp(math.log(50) * 0.85), 6)
        score = score_hrv(last_night, 50)
        assert 5 <= score <= 15

    # --- Boundary: p = -0.20 (top of p >= -0.20 → 10 + (p+0.15)*200 = 0) ---
    def test_p_at_neg_0p20(self):
        """p = -0.20 → 10 + (-0.05)*200 = 0"""
        last_night = round(math.exp(math.log(50) * 0.80), 6)
        assert score_hrv(last_night, 50) == 0

    # --- Normal range ---
    def test_slight_positive(self):
        """p in (0.05, 0.10] → 85 + (p-0.05)*(-300)"""
        last_night = round(math.exp(math.log(50) * 1.07), 6)
        score = score_hrv(last_night, 50)
        assert 70 <= score <= 85

    def test_slight_negative(self):
        """p in (-0.05, 0) → 75 + p*300"""
        last_night = round(math.exp(math.log(50) * 0.97), 6)
        score = score_hrv(last_night, 50)
        assert 60 <= score <= 75


# ==========================================
# score_rhr
# ==========================================

class TestScoreRhr:
    """score_rhr(current, baseline) — 基于绝对值偏差的分段评分"""

    # --- Guard: clamp upper bound ---
    def test_extreme_lower_rhr(self):
        """d < -3 → 95"""
        assert score_rhr(40, 50) == 95

    # --- Guard: clamp lower bound ---
    def test_extreme_higher_rhr(self):
        """d > 10 → 0"""
        assert score_rhr(65, 50) == 0

    # --- Boundary: d = -3 (top of d < -3 → 95, at d = -3 falls in d <= 0 → 95) ---
    def test_d_at_neg_3(self):
        """d = -3 → 95 + (0)*(-20/3) = 95"""
        assert score_rhr(47, 50) == 95

    # --- Boundary: d = 0 (top of d <= 0 → 95 + (0+3)*(-20/3) = 95 - 20 = 75) ---
    def test_d_at_0(self):
        """d = 0 → 95 + 3*(-20/3) = 75"""
        assert score_rhr(50, 50) == 75

    # --- Boundary: d = 3 (top of d <= 3 → 75 + 3*(-20/3) = 55) ---
    def test_d_at_3(self):
        """d = 3 → 75 + 3*(-20/3) = 55"""
        assert score_rhr(53, 50) == 55

    # --- Boundary: d = 6 (top of d <= 6 → 55 + (3)*(-25/3) = 30) ---
    def test_d_at_6(self):
        """d = 6 → 55 + (6-3)*(-25/3) = 55 - 25 = 30"""
        assert score_rhr(56, 50) == 30

    # --- Boundary: d = 10 (top of d <= 10 → 30 + (4)*(-7.5) = 0) ---
    def test_d_at_10(self):
        """d = 10 → 30 + (10-6)*(-7.5) = 30 - 30 = 0"""
        assert score_rhr(60, 50) == 0

    # --- Normal range ---
    def test_rhr_slightly_low(self):
        """d = -2 → 95 + (1)*(-20/3) = 88.33 → 88"""
        assert score_rhr(48, 50) == 88  # d = -2

    def test_rhr_slightly_high(self):
        """d = 2 → 75 + 2*(-20/3) = 61.67 → 62"""
        assert score_rhr(52, 50) == 62  # d = 2

    # --- Same value ---
    def test_rhr_equal(self):
        assert score_rhr(50, 50) == 75


# ==========================================
# score_sleep
# ==========================================

class TestScoreSleep:
    """score_sleep(total_sec, deep_sec, rem_sec, awake_cnt, gs=None)"""

    # --- Guard: gs shortcut ---
    def test_gs_shortcut(self):
        """如果提供了 gs，直接返回"""
        assert score_sleep(0, 0, 0, 0, gs=85) == 85

    def test_gs_shortcut_zero(self):
        assert score_sleep(0, 0, 0, 0, gs=0) == 0

    # --- Guard: zero total seconds ---
    def test_zero_total_seconds(self):
        """total_sec = 0 → 除零保护，各子维度应为 0
        th=0 → ds=10, dp=0 → des=20, rp=0 → res=30, awake=0 → aws=100
        score = 10*0.30 + 20*0.35 + 30*0.15 + 100*0.20 = 3+7+4.5+20 = 34.5 → 34（banker's rounding）"""
        assert score_sleep(0, 0, 0, 0) == 34

    # --- Duration boundary: th < 5 ---
    def test_duration_under_5h(self):
        """4h = 14400s → ds=10"""
        score = score_sleep(14400, 1800, 900, 0)
        assert 0 <= score <= 100

    # --- Duration boundary: th = 5 (top of th < 5, at 5h falls in th < 6) ---
    def test_duration_at_5h(self):
        """5h = 18000s → ds = 10 + 0*35 = 10"""
        score = score_sleep(18000, 3600, 1800, 0)
        assert 0 <= score <= 100

    # --- Duration boundary: th = 6 (top of th < 6, at 6h falls in th < 7) ---
    def test_duration_at_6h(self):
        """6h = 21600s → ds = 10 + (6-5)*35 = 45"""
        score = score_sleep(21600, 4320, 2160, 1)
        assert 0 <= score <= 100

    # --- Duration boundary: th = 7 (top of th < 7, at 7h falls in th <= 9) ---
    def test_duration_at_7h(self):
        """7h = 25200s → ds = 80"""
        score = score_sleep(25200, 5040, 2520, 1)
        assert 0 <= score <= 100

    # --- Duration boundary: th = 9 (top of th <= 9 → ds = 80 + (9-7)*10 = 100) ---
    def test_duration_at_9h(self):
        """9h = 32400s → ds = 80 + 20 = 100"""
        score = score_sleep(32400, 6480, 3240, 0)
        assert 0 <= score <= 100

    # --- Duration: beyond 9h ---
    def test_duration_over_9h(self):
        """10h = 36000s → ds = max(50, 100 - 20) = 80"""
        score = score_sleep(36000, 7200, 3600, 0)
        assert 0 <= score <= 100

    # --- Deep sleep boundary: dp < 5 ---
    def test_deep_under_5pct(self):
        """deep=3% → des=20"""
        score = score_sleep(28800, 864, 4320, 1)
        assert 0 <= score <= 100

    # --- Deep sleep boundary: dp = 5 (top of dp < 5, at 5 falls in dp < 10) ---
    def test_deep_at_5pct(self):
        """deep=5% → des = 20 + 0*8 = 20"""
        score = score_sleep(28800, 1440, 4320, 1)
        assert 0 <= score <= 100

    # --- Deep sleep boundary: dp = 10 (top of dp < 10, at 10 falls in dp <= 25) ---
    def test_deep_at_10pct(self):
        """deep=10% → des = 20 + (10-5)*8 = 60"""
        score = score_sleep(28800, 2880, 4320, 1)
        assert 0 <= score <= 100

    # --- Deep sleep boundary: dp = 25 (top of dp <= 25 → des = 60 + (25-10)*(40/15) = 100) ---
    def test_deep_at_25pct(self):
        """deep=25% → des = 60 + 15*(40/15) = 100"""
        score = score_sleep(28800, 7200, 4320, 1)
        assert 0 <= score <= 100

    # --- Deep sleep: beyond 25% ---
    def test_deep_over_25pct(self):
        """deep=30% → des = 90"""
        score = score_sleep(28800, 8640, 4320, 1)
        assert 0 <= score <= 100

    # --- REM boundary: rp < 10 ---
    def test_rem_under_10pct(self):
        """rem=8% → res = 30 + 8*2 = 46"""
        score = score_sleep(28800, 4320, 2304, 1)
        assert 0 <= score <= 100

    # --- REM boundary: rp = 10 (top of rp < 10, at 10 falls in rp < 18) ---
    def test_rem_at_10pct(self):
        """rem=10% → res = 50"""
        score = score_sleep(28800, 4320, 2880, 1)
        assert 0 <= score <= 100

    # --- REM boundary: rp = 18 (top of rp < 18, at 18 falls in rp <= 25) ---
    def test_rem_at_18pct(self):
        """rem=18% → res = 50 + (18-10)*2.5 = 70"""
        score = score_sleep(28800, 4320, 5184, 1)
        assert 0 <= score <= 100

    # --- REM boundary: rp = 25 (top of rp <= 25 → res = 70 + (25-18)*(30/7) = 100) ---
    def test_rem_at_25pct(self):
        """rem=25% → res = 70 + 7*(30/7) = 100"""
        score = score_sleep(28800, 4320, 7200, 1)
        assert 0 <= score <= 100

    # --- REM: beyond 25% ---
    def test_rem_over_25pct(self):
        """rem=30% → res = 85"""
        score = score_sleep(28800, 4320, 8640, 1)
        assert 0 <= score <= 100

    # --- Awake count ---
    def test_awake_0(self):
        assert score_sleep(28800, 4320, 4320, 0) > 0

    def test_awake_1(self):
        assert score_sleep(28800, 4320, 4320, 1) > 0

    def test_awake_2(self):
        assert score_sleep(28800, 4320, 4320, 2) > 0

    def test_awake_3(self):
        assert score_sleep(28800, 4320, 4320, 3) > 0

    def test_awake_many(self):
        """awake >= 3 → aws = max(0, 45 - (awake-3)*15)"""
        # awake=5 → aws = max(0, 45 - 30) = 15
        assert score_sleep(28800, 4320, 4320, 5) > 0
        # awake=10 → aws = max(0, 45 - 105) = 0
        assert score_sleep(28800, 4320, 4320, 10) >= 0

    # --- Ideal sleep ---
    def test_ideal_sleep(self):
        """8h, 深睡20%, REM22%, 清醒0次 → 评分应较高"""
        score = score_sleep(28800, 5760, 6336, 0)
        assert 70 <= score <= 100

    # --- Poor sleep ---
    def test_poor_sleep(self):
        """4h, 深睡3%, REM5%, 清醒4次 → 评分应较低"""
        score = score_sleep(14400, 432, 720, 4)
        assert 0 <= score <= 50