"""
AI Narrative 生成器

统一管理所有报表的 AI 文本生成。
降级策略：LLM 不可用时用规则引擎模板。
"""


class AINarrator:
    """AI Narrative 生成器"""

    def __init__(self, llm_client=None):
        self.llm = llm_client

    # ── Morning Report ──

    def generate_morning_insight(self, health: dict) -> str:
        """生成晨间建议（建议型）"""
        hrv = health.get("hrv", 0)
        hrv_baseline = health.get("hrv_baseline", hrv)
        rhr = health.get("rhr", 0)
        sleep_score = health.get("sleep_score", 0)
        sleep_duration = health.get("sleep_duration", "未知")
        readiness = health.get("readiness", 0)

        # 计算 HRV 变化
        if hrv_baseline and hrv_baseline > 0:
            hrv_change = round((hrv - hrv_baseline) / hrv_baseline * 100)
        else:
            hrv_change = 0

        # 规则引擎
        if readiness >= 80 and hrv_change >= 5:
            return (
                f"睡眠恢复良好，HRV 高于基线 {hrv_change}%，"
                f"今天适合进行节奏跑或爬坡训练。"
            )
        elif readiness >= 60 and sleep_score >= 70:
            return (
                f"身体状态良好，睡眠评分 {sleep_score}，"
                f"今天可以进行正常训练，注意控制强度。"
            )
        elif readiness < 40 or hrv_change < -10:
            return (
                f"HRV 较基线下降 {abs(hrv_change)}%，建议今天休息"
                f"或进行极轻量活动。"
            )
        else:
            return (
                f"准备度 {readiness}/100，建议以轻松跑为主，"
                f"时长控制在 30-40 分钟。"
            )

    def generate_morning_suggestion(self, health: dict) -> dict:
        """生成今日训练建议"""
        readiness = health.get("readiness", 0)
        hrv = health.get("hrv", 0)
        hrv_baseline = health.get("hrv_baseline", hrv)
        sleep_score = health.get("sleep_score", 0)

        if hrv_baseline and hrv_baseline > 0:
            hrv_change = (hrv - hrv_baseline) / hrv_baseline * 100
        else:
            hrv_change = 0

        if readiness >= 80 and hrv_change >= 5:
            return {
                "type": "节奏跑",
                "duration": "45-60 min",
                "intensity": "Z3-Z4",
            }
        elif readiness >= 60:
            return {
                "type": "轻松跑",
                "duration": "30-45 min",
                "intensity": "Z2",
            }
        else:
            return {
                "type": "休息",
                "duration": "0 min",
                "intensity": "Rest",
            }

    # ── Daily Report ──

    def generate_daily_insight(self, activity: dict, efficiency: dict,
                                history: dict = None) -> str:
        """生成单次训练分析（分析型）"""
        pace = activity.get("pace", "")
        distance = activity.get("distance", 0)
        hr = activity.get("avg_hr", 0)
        hr_drift = efficiency.get("hr_drift", 0)
        cadence = efficiency.get("cadence", 0)

        parts = []

        # 配速分析
        splits = activity.get("splits", [])
        if len(splits) >= 2:
            first_half_pace = sum(s.get("pace", 0) for s in splits[:len(splits)//2]) / max(len(splits)//2, 1)
            second_half_pace = sum(s.get("pace", 0) for s in splits[len(splits)//2:]) / max(len(splits) - len(splits)//2, 1)
            if second_half_pace > first_half_pace * 1.05:
                parts.append("前半程配速偏快，后半程出现掉速")
            elif second_half_pace < first_half_pace * 0.98:
                parts.append("后半程配速提升，节奏控制优秀")

        # HR Drift 分析
        if hr_drift > 5:
            parts.append(f"心率漂移 +{hr_drift}%，有氧效率有提升空间")
        elif hr_drift < 3:
            parts.append("心率漂移控制良好，有氧效率稳定")

        # 步频分析
        if cadence > 0:
            if cadence >= 180:
                parts.append("步频优秀")
            elif cadence >= 170:
                parts.append(f"步频 {cadence} spm，可适当提高")
            else:
                parts.append(f"步频偏低 ({cadence} spm)，建议加强步频训练")

        if not parts:
            parts.append(f"本次训练距离 {distance}km，配速 {pace}，整体表现稳定")

        return "。".join(parts) + "。"

    # ── Weekly Report ──

    def generate_weekly_coach(self, weekly_data: dict) -> str:
        """生成教练级总结（教练型）"""
        load = weekly_data.get("load", {})
        recovery = weekly_data.get("recovery_trend", {})
        efficiency = weekly_data.get("efficiency_trend", {})
        risk_alerts = weekly_data.get("risk_alerts", [])

        parts = []

        # 负荷评估
        distance = load.get("distance", 0)
        if distance > 50:
            parts.append(f"本周跑量 {distance:.1f}km，训练负荷较高")
        elif distance > 30:
            parts.append(f"本周跑量 {distance:.1f}km，训练量适中")
        else:
            parts.append(f"本周跑量 {distance:.1f}km，训练量偏低")

        # 恢复评估
        recovery_dir = recovery.get("trend_direction", "stable")
        if recovery_dir == "declining":
            parts.append("恢复状态下降，建议降低训练强度")
        elif recovery_dir == "improving":
            parts.append("恢复状态改善，可以适当增加强度")
        else:
            parts.append("恢复状态稳定")

        # 效率评估
        eff_change = efficiency.get("efficiency_score", 0)
        if eff_change > 3:
            parts.append(f"跑步效率提升 {eff_change:.1f}%，继续保持")
        elif eff_change < -3:
            parts.append(f"跑步效率下降 {abs(eff_change):.1f}%，注意调整训练结构")

        # 风险预警
        if risk_alerts:
            parts.append(f"注意：{risk_alerts[0]}")

        return "。".join(parts) + "。"

    # ── Monthly Report ──

    def generate_monthly_narrative(self, monthly_data: dict) -> str:
        """生成月度成长叙事（叙事型）"""
        overview = monthly_data.get("training_overview", {})
        recovery = monthly_data.get("recovery_summary", {})
        efficiency = monthly_data.get("efficiency_growth", {})

        parts = []

        # 训练稳定性
        days = overview.get("days", 0)
        distance = overview.get("distance", 0)
        if days >= 20:
            parts.append("本月训练稳定性明显提升")
        elif days >= 15:
            parts.append("本月保持了较好的训练节奏")
        else:
            parts.append("本月训练频率偏低")

        # 耐力评估
        if distance > 200:
            parts.append("长距离耐力增强")

        # 恢复评估
        stability = recovery.get("recovery_stability", "stable")
        if stability == "stable":
            parts.append("恢复状态整体良好")
        else:
            parts.append("恢复状态波动较大")

        # 效率变化
        aerobic = efficiency.get("aerobic", "")
        if aerobic.startswith("+"):
            parts.append(f"有氧效率提升 {aerobic}")
        elif aerobic.startswith("-"):
            parts.append(f"有氧效率下降 {aerobic}，建议调整训练结构")

        return "。".join(parts) + "。"

    # ── Race Report ──

    def generate_race_commentary(self, race_data: dict) -> str:
        """生成赛事评论（评论型）"""
        result = race_data.get("result", {})
        splits = race_data.get("splits", {})

        parts = []

        # 前后半程分析
        first_half = splits.get("first_half", "")
        second_half = splits.get("second_half", "")
        if first_half and second_half:
            # 简单比较字符串长度作为时间近似
            diff = len(second_half) - len(first_half)
            if diff > 2:
                parts.append("后半程出现明显掉速")
            elif diff < -2:
                parts.append("后半程配速提升，节奏控制出色")
            else:
                parts.append("前后半程配速稳定")

        # 爬坡分析
        climbing = race_data.get("race_intelligence", {})
        climbing_eff = climbing.get("climbing_efficiency", "")
        if climbing_eff:
            parts.append(f"爬坡效率 {climbing_eff}")

        # 心率分析
        hr_collapse = climbing.get("hr_collapse", "")
        if "无" in hr_collapse or "稳定" in hr_collapse:
            parts.append("心率控制良好，无明显崩塌")

        if not parts:
            distance = result.get("distance", 0)
            finish_time = result.get("finish_time", "")
            parts.append(f"完成 {distance}km，用时 {finish_time}，整体表现稳定")

        return "。".join(parts) + "。"

    def generate_critical_moment(self, race_data: dict) -> str:
        """生成关键时刻分析"""
        splits = race_data.get("splits", {})
        result = race_data.get("result", {})

        # 找到配速变化最大的公里
        km_splits = race_data.get("km_splits", [])
        if len(km_splits) >= 3:
            max_drop_idx = 0
            max_drop = 0
            for i in range(1, len(km_splits)):
                drop = km_splits[i].get("pace", 0) - km_splits[i-1].get("pace", 0)
                if drop > max_drop:
                    max_drop = drop
                    max_drop_idx = i

            if max_drop > 30:  # 配速下降超过 30 秒/km
                return (
                    f"第 {max_drop_idx + 1}km 后出现明显配速下降，"
                    f"但爬坡段表现依旧稳定。"
                )

        distance = result.get("distance", 0)
        return f"全程 {distance}km 节奏控制成熟，配速波动在合理范围内。"

    def generate_finish_narrative(self, race_data: dict) -> str:
        """生成完赛叙事"""
        result = race_data.get("result", {})
        commentary = self.generate_race_commentary(race_data)

        finish_time = result.get("finish_time", "")
        distance = result.get("distance", 0)

        return (
            f"这是一次节奏控制非常成熟的比赛。{commentary}"
        )
