"""
Morning Call 早间日报

模块结构（对标需求文档）：
1. 今日身体状态评分
2. 近7日训练负荷趋势
3. 今日训练建议
4. 天气参考（占位）
5. 本周目标提醒

用法:
    from morning_call import MorningCall
    mc = MorningCall(mock=True)
    mc.generate()
"""

import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_aggregator import DataAggregator
from chart_renderer import ChartRenderer, Colors
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec


class MorningCall:
    """Morning Call 早间日报生成器"""

    def __init__(self, mock: bool = True, output_dir: str = None):
        self.aggregator = DataAggregator(mock=mock)
        self.output_dir = Path(output_dir or Path(__file__).resolve().parent / "output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.renderer = ChartRenderer(output_dir=str(self.output_dir))

    def generate(self) -> str:
        data = self.aggregator.get_morning_call_data()
        chart_paths = self._render_charts(data)
        report_path = self._compose_report(data, chart_paths)
        return report_path

    def _render_charts(self, data: dict) -> dict:
        paths = {}
        week_health = data.get("week_health_trend", [])
        if week_health:
            paths["health_trend"] = self.renderer.render_health_trend(
                week_health, "近7天健康趋势"
            )
        return paths

    def _compose_report(self, data: dict, chart_paths: dict) -> str:
        fig = plt.figure(figsize=(16, 18))
        fig.patch.set_facecolor(Colors.BG)

        gs = GridSpec(3, 2, figure=fig, hspace=0.35, wspace=0.3,
                     left=0.06, right=0.94, top=0.95, bottom=0.03)

        # Row 0: 今日状态评分（全宽）
        ax_status = fig.add_subplot(gs[0, :])
        ax_status.set_facecolor(Colors.BG)
        ax_status.axis('off')
        self._draw_status_score(ax_status, data["health"], data.get("training_advice", {}))

        # Row 1: 健康趋势 | 训练建议
        if "health_trend" in chart_paths:
            ax_health = fig.add_subplot(gs[1, 0])
            self._embed_chart(ax_health, chart_paths["health_trend"])

        ax_advice = fig.add_subplot(gs[1, 1])
        ax_advice.set_facecolor(Colors.BG)
        ax_advice.axis('off')
        self._draw_training_advice(ax_advice, data.get("training_advice", {}))

        # Row 2: 训练负荷 | 目标提醒
        ax_load = fig.add_subplot(gs[2, 0])
        ax_load.set_facecolor(Colors.BG)
        ax_load.axis('off')
        self._draw_week_load(ax_load, data.get("week_activities", []))

        ax_goal = fig.add_subplot(gs[2, 1])
        ax_goal.set_facecolor(Colors.BG)
        ax_goal.axis('off')
        self._draw_goal_reminder(ax_goal)

        report_path = str(self.output_dir / "morning_call.png")
        fig.savefig(report_path, dpi=150, bbox_inches='tight',
                   facecolor=Colors.BG, edgecolor='none')
        plt.close(fig)
        return report_path

    def _draw_status_score(self, ax, health: dict, advice: dict):
        today = date.today().isoformat()
        ax.text(0.5, 0.85, f'Morning Call - {today}', ha='center', va='center',
               fontsize=26, fontweight='bold', color=Colors.TEXT_PRIMARY,
               transform=ax.transAxes)

        # 综合状态评级
        level = advice.get("readiness_level", "MODERATE")
        level_text = {"HIGH": "优", "MODERATE": "一般", "LOW": "需休息"}.get(level, level)
        score = advice.get("readiness_score", 50)
        level_color = {"HIGH": '#4CAF50', "MODERATE": '#FFC107', "LOW": '#F44336'}.get(level, '#999')

        # 状态卡片
        rect = mpatches.FancyBboxPatch(
            (0.35, 0.35), 0.3, 0.40,
            boxstyle="round,pad=0.03",
            facecolor=Colors.CARD_BG, edgecolor=level_color,
            linewidth=3, transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(0.5, 0.62, level_text, ha='center', va='center', fontsize=36,
               fontweight='bold', color=level_color, transform=ax.transAxes)
        ax.text(0.5, 0.48, f'准备度 {score}分', ha='center', va='center', fontsize=14,
               color=Colors.TEXT_SECONDARY, transform=ax.transAxes)

        # HRV / RHR / 睡眠
        hrv = health.get("hrv", {}).get("hrvSummary", {})
        rhr_raw = health.get("resting_hr", {})
        try:
            rhr_val = rhr_raw.get("allMetrics", {}).get("metricsMap", {}).get("WELLNESS_RESTING_HEART_RATE", [{}])[0].get("value", 0)
        except (IndexError, AttributeError):
            rhr_val = 0
        sleep = health.get("sleep", {}).get("dailySleepDTO", {})
        sleep_score = sleep.get("sleepScores", {}).get("overall", {}).get("value", "--")
        sleep_h = sleep.get("sleepTimeSeconds", 0) // 3600

        info_items = [
            (f'HRV: {hrv.get("lastNightAvg", "--")} ms', f'7日均: {hrv.get("weeklyAvg", "--")}'),
            (f'静息心率: {int(rhr_val)} bpm', ''),
            (f'睡眠: {sleep_score}分 ({sleep_h}h)', ''),
        ]

        x_positions = [0.08, 0.38, 0.68]
        for i, (line1, line2) in enumerate(info_items):
            ax.text(x_positions[i], 0.22, line1, fontsize=11, color=Colors.TEXT_PRIMARY,
                   transform=ax.transAxes)
            if line2:
                ax.text(x_positions[i], 0.12, line2, fontsize=10, color=Colors.TEXT_SECONDARY,
                       transform=ax.transAxes)

    def _draw_training_advice(self, ax, advice: dict):
        ax.text(0.05, 0.95, '今日训练建议', fontsize=14, fontweight='bold',
               color=Colors.TEXT_PRIMARY, transform=ax.transAxes)

        intensity = advice.get("intensity", "轻松跑")
        tip = advice.get("advice", "")

        y = 0.80
        ax.text(0.05, y, f'建议强度: {intensity}', fontsize=14, fontweight='bold',
               color=Colors.ACCENT, transform=ax.transAxes)
        y -= 0.15
        ax.text(0.05, y, tip, fontsize=11, color=Colors.TEXT_SECONDARY,
               transform=ax.transAxes, wrap=True, verticalalignment='top')

    def _draw_week_load(self, ax, week_acts: list):
        ax.text(0.05, 0.95, '本周训练负荷', fontsize=14, fontweight='bold',
               color=Colors.TEXT_PRIMARY, transform=ax.transAxes)

        total_km = sum(a.get("distance", 0) for a in week_acts) / 1000
        total_dur = sum(a.get("duration", 0) for a in week_acts) / 60
        count = len(week_acts)

        y = 0.80
        items = [
            ('训练次数', f'{count} 次'),
            ('累计跑量', f'{total_km:.1f} km'),
            ('累计时长', f'{total_dur:.0f} 分钟'),
        ]
        for label, val in items:
            ax.text(0.05, y, label, fontsize=10, color=Colors.TEXT_SECONDARY,
                   transform=ax.transAxes)
            ax.text(0.95, y, val, fontsize=11, fontweight='bold',
                   color=Colors.TEXT_PRIMARY, ha='right', transform=ax.transAxes)
            y -= 0.18

    def _draw_goal_reminder(self, ax):
        ax.text(0.05, 0.95, '本周目标', fontsize=14, fontweight='bold',
               color=Colors.TEXT_PRIMARY, transform=ax.transAxes)
        ax.text(0.05, 0.75, '设定你的训练目标', fontsize=11,
               color=Colors.TEXT_SECONDARY, transform=ax.transAxes)
        ax.text(0.05, 0.55, 'Keep going!', fontsize=16, fontweight='bold',
               color=Colors.ACCENT, transform=ax.transAxes)

    def _embed_chart(self, ax, img_path: str):
        ax.axis('off')
        try:
            img = plt.imread(img_path)
            ax.imshow(img, aspect='auto')
        except Exception as e:
            ax.text(0.5, 0.5, f'图表加载失败: {e}', ha='center', va='center',
                   fontsize=12, color=Colors.TEXT_SECONDARY, transform=ax.transAxes)


if __name__ == "__main__":
    mc = MorningCall(mock=True)
    path = mc.generate()
    print(f"Morning Call: {path}")
