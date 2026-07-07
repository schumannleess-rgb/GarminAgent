"""
风险检测引擎

分析训练数据，识别潜在风险并生成预警。
用于 Weekly Report 的 Risk Alert 模块。
"""

from datetime import datetime, timedelta


class RiskDetector:
    """训练风险检测器"""

    # 风险阈值
    HRV_DROP_THRESHOLD = -10      # HRV 下降超过 10% 触发预警
    HRV_CONSECUTIVE_DAYS = 3      # HRV 连续下降天数
    LOAD_HIGH_DAYS = 5            # 高负荷连续天数
    LOAD_INCREASE_PCT = 20        # 周跑量增幅超过 20%
    SLEEP_LOW_THRESHOLD = 60      # 睡眠评分低于 60
    SLOW_DOWN_PCT = 10            # 配速下降超过 10%

    def detect_all(self, weekly_data: dict) -> list:
        """检测所有风险，返回预警列表"""
        alerts = []

        alerts.extend(self._check_hrv_trend(weekly_data))
        alerts.extend(self._check_load_balance(weekly_data))
        alerts.extend(self._check_sleep_quality(weekly_data))
        alerts.extend(self._check_recovery_status(weekly_data))

        return alerts

    def _check_hrv_trend(self, data: dict) -> list:
        """检测 HRV 趋势"""
        alerts = []
        health_trend = data.get("health_trend", [])

        if len(health_trend) < 3:
            return alerts

        # 提取 HRV 值
        hrv_values = []
        for h in health_trend:
            hrv = h.get("hrv", {})
            if isinstance(hrv, dict):
                val = hrv.get("hrvSummary", {}).get("lastNightAvg", 0)
            elif isinstance(hrv, (int, float)):
                val = hrv
            else:
                val = 0
            if val > 0:
                hrv_values.append(val)

        if len(hrv_values) < 3:
            return alerts

        # 检查连续下降
        consecutive_drop = 0
        for i in range(1, len(hrv_values)):
            if hrv_values[i] < hrv_values[i-1]:
                consecutive_drop += 1
            else:
                consecutive_drop = 0

        if consecutive_drop >= self.HRV_CONSECUTIVE_DAYS:
            alerts.append(
                f"HRV 连续 {consecutive_drop} 天下降"
                f"（{hrv_values[0]} → {hrv_values[-1]}ms），建议减少训练强度。"
            )

        # 检查总降幅
        if len(hrv_values) >= 2:
            baseline = sum(hrv_values[:3]) / min(3, len(hrv_values))
            latest = hrv_values[-1]
            change_pct = (latest - baseline) / baseline * 100
            if change_pct < self.HRV_DROP_THRESHOLD:
                alerts.append(
                    f"HRV 较基线下降 {abs(change_pct):.0f}%"
                    f"（{baseline:.0f} → {latest}ms），恢复不足。"
                )

        return alerts

    def _check_load_balance(self, data: dict) -> list:
        """检测训练负荷"""
        alerts = []
        vs_last_week = data.get("vs_last_week", {})

        # 周跑量增幅过大
        distance_diff = vs_last_week.get("distance_diff", 0)
        if distance_diff > 0:
            # 计算增幅百分比（需要上周数据作为基数）
            load = data.get("load", {})
            current_distance = load.get("distance", 0)
            if current_distance > 0 and distance_diff > 0:
                last_week_distance = current_distance - distance_diff
                if last_week_distance > 0:
                    increase_pct = distance_diff / last_week_distance * 100
                    if increase_pct > self.LOAD_INCREASE_PCT:
                        alerts.append(
                            f"周跑量较上周增加 {increase_pct:.0f}%，"
                            f"增幅过大，建议控制在 10-15% 以内。"
                        )

        return alerts

    def _check_sleep_quality(self, data: dict) -> list:
        """检测睡眠质量"""
        alerts = []
        health_trend = data.get("health_trend", [])

        if len(health_trend) < 3:
            return alerts

        # 检查睡眠评分
        low_sleep_days = 0
        for h in health_trend:
            sleep = h.get("sleep", {})
            if isinstance(sleep, dict):
                score = sleep.get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value", 0)
            elif isinstance(sleep, (int, float)):
                score = sleep
            else:
                score = 0
            if 0 < score < self.SLEEP_LOW_THRESHOLD:
                low_sleep_days += 1

        if low_sleep_days >= 3:
            alerts.append(
                f"本周有 {low_sleep_days} 天睡眠评分低于 {self.SLEEP_LOW_THRESHOLD}，"
                f"可能影响恢复质量。"
            )

        return alerts

    def _check_recovery_status(self, data: dict) -> list:
        """检测恢复状态"""
        alerts = []
        recovery = data.get("recovery_trend", {})
        direction = recovery.get("trend_direction", "stable")

        if direction == "declining":
            alerts.append(
                "恢复状态持续下降，建议安排 1-2 天主动恢复。"
            )

        return alerts
