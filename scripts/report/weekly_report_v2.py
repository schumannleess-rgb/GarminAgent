"""
Weekly Report — 趋势与恢复

分析感风格，标准海报。
核心情绪：Analysis（分析感）

信息结构：
1. Header — 周报标题 + 日期范围
2. Weekly Load — 四大数字
3. Recovery Trend + Efficiency Trend（sparkline）
4. Daily Distance 图表
5. AI Coach Summary
6. Risk Alert（条件显示）
7. Training Distribution + vs Last Week
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs
from matplotlib.patches import FancyBboxPatch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_styles import (
    WEEKLY_COLORS as COLORS,
    WEEKLY_FONTS as FONTS,
    WEEKLY_SIZE as SIZE,
    trend_color, readiness_color,
    CARD_RADIUS, AI_INSIGHT_LEFT_LINE, AI_INSIGHT_BG_ALPHA,
)
from data_aggregator import DataAggregator
from ai_narrator import AINarrator
from risk_detector import RiskDetector


class WeeklyReportV2:
    """Weekly Report v2 生成器"""

    def __init__(self, mock: bool = True):
        self.mock = mock
        self.aggregator = DataAggregator(mock=mock)
        self.narrator = AINarrator()
        self.risk_detector = RiskDetector()

    def generate(self, weeks_ago: int = 0) -> str:
        """生成 Weekly Report，返回文件路径"""
        data = self.aggregator.get_weekly_data(weeks_ago)

        summary = data["summary"]
        daily = data["daily_breakdown"]
        health_trend = data["health_trend"]
        hr_zones = data["hr_zones_week"]
        vs_last = data["vs_last_week"]

        # Recovery Trend
        hrv_values = []
        rhr_values = []
        sleep_values = []
        for h in health_trend:
            hrv_val = self.aggregator._extract_hrv(h)
            rhr_val = self.aggregator._extract_rhr(h)
            sleep_val = self.aggregator._extract_sleep_score(h)
            if hrv_val > 0:
                hrv_values.append(hrv_val)
            if rhr_val > 0:
                rhr_values.append(rhr_val)
            if sleep_val > 0:
                sleep_values.append(sleep_val)

        # Efficiency Trend（简化：用 HR Zones 变化估算）
        eff_trend = {
            "pace_vs_hr": round(-vs_last.get("avg_hr_diff", 0) * 0.5, 1),
            "efficiency_score": round(-vs_last.get("avg_hr_diff", 0) * 0.3, 1),
        }

        # AI Coach
        weekly_data_for_ai = {
            "load": {"distance": summary["total_distance"] / 1000},
            "recovery_trend": {"trend_direction": "stable"},
            "efficiency_trend": eff_trend,
            "risk_alerts": [],
        }
        ai_coach = self.narrator.generate_weekly_coach(weekly_data_for_ai)

        # Risk Alerts
        risk_alerts = self.risk_detector.detect_all(data)

        # 绘图
        fig = self._draw(
            week_start=data["week_start"], week_end=data["week_end"],
            summary=summary, daily=daily,
            hrv_values=hrv_values, rhr_values=rhr_values, sleep_values=sleep_values,
            hr_zones=hr_zones, vs_last=vs_last,
            ai_coach=ai_coach, risk_alerts=risk_alerts,
            eff_trend=eff_trend,
        )

        output = Path(__file__).resolve().parent / "output" / "weekly_report_v2.png"
        output.parent.mkdir(exist_ok=True)
        fig.savefig(str(output), dpi=SIZE.dpi, bbox_inches="tight",
                    facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return str(output)

    def _draw(self, week_start, week_end, summary, daily,
              hrv_values, rhr_values, sleep_values,
              hr_zones, vs_last, ai_coach, risk_alerts, eff_trend):
        """绘制 Weekly Report"""
        fig = plt.figure(figsize=(SIZE.width, SIZE.height), dpi=SIZE.dpi)
        fig.set_facecolor(COLORS.bg)

        n_rows = 7 if risk_alerts else 6
        grid = gs.GridSpec(
            n_rows, 2, figure=fig,
            height_ratios=[0.6, 1, 1.2, 1.5, 1.2, 0.8, 0.8][:n_rows],
            hspace=0.12, wspace=0.25,
            left=0.08, right=0.92, top=0.95, bottom=0.04,
        )

        row = 0

        # ── Row 0: Header ──
        ax = fig.add_subplot(grid[row, :])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)
        ax.text(0.5, 0.7, "Weekly Training Report", fontsize=FONTS.title,
                color=COLORS.text_primary, ha="center", va="center",
                fontweight="bold", fontfamily="sans-serif")
        ax.text(0.5, 0.2, f"{week_start} ~ {week_end}", fontsize=FONTS.caption,
                color=COLORS.text_light, ha="center", va="center", fontfamily="sans-serif")
        row += 1

        # ── Row 1: Weekly Load ──
        ax = fig.add_subplot(grid[row, :])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)
        hero_items = [
            (summary["total_distance_fmt"], "Distance"),
            (summary["total_duration_fmt"], "Time"),
            (f"{summary['total_elevation']}", "Elevation"),
            (summary["total_calories_fmt"], "Calories"),
        ]
        for i, (val, label) in enumerate(hero_items):
            x = 0.12 + i * 0.23
            ax.text(x, 0.7, val, fontsize=FONTS.hero,
                    color=COLORS.text_primary, ha="center", va="center",
                    fontweight="bold", fontfamily="sans-serif")
            ax.text(x, 0.25, label, fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="center", va="center",
                    fontfamily="sans-serif")
        row += 1

        # ── Row 2: Recovery + Efficiency Trends ──
        ax_rec = fig.add_subplot(grid[row, 0])
        ax_eff = fig.add_subplot(grid[row, 1])
        self._draw_sparkline_block(ax_rec, "Recovery Trend", [
            ("HRV", hrv_values, "ms"),
            ("RHR", rhr_values, "bpm"),
            ("Sleep", sleep_values, ""),
        ])
        self._draw_sparkline_block(ax_eff, "Efficiency Trend", [
            ("Pace/HR", [], ""),
            ("Score", [], ""),
        ], metrics=[
            (f"{eff_trend['pace_vs_hr']:+.1f}%", "Pace/HR"),
            (f"{eff_trend['efficiency_score']:+.1f}%", "Efficiency"),
        ])
        row += 1

        # ── Row 3: Daily Distance Chart ──
        ax_daily = fig.add_subplot(grid[row, :])
        self._draw_daily_distance(ax_daily, daily)
        row += 1

        # ── Row 4: AI Coach Summary ──
        ax_ai = fig.add_subplot(grid[row, :])
        self._draw_ai_block(ax_ai, "AI Coach Summary", ai_coach)
        row += 1

        # ── Row 5: Risk Alert (conditional) ──
        if risk_alerts:
            ax_risk = fig.add_subplot(grid[row, :])
            self._draw_risk_alert(ax_risk, risk_alerts)
            row += 1

        # ── Last Row: Training Distribution + vs Last Week ──
        ax_dist = fig.add_subplot(grid[row, 0])
        ax_vs = fig.add_subplot(grid[row, 1])
        self._draw_training_dist(ax_dist, hr_zones)
        self._draw_vs_last_week(ax_vs, vs_last)

        return fig

    def _draw_sparkline_block(self, ax, title, spark_data, metrics=None):
        """绘制 sparkline 块"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)

        ax.text(0.5, 0.95, title, fontsize=FONTS.body,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")

        if metrics:
            y = 0.65
            for val, label in metrics:
                ax.text(0.15, y, label, fontsize=FONTS.caption,
                        color=COLORS.text_light, ha="left", va="center")
                color = trend_color(float(val.replace("%", "").replace("+", "")))
                ax.text(0.85, y, val, fontsize=FONTS.caption,
                        color=color, ha="right", va="center", fontweight="bold")
                y -= 0.25
        elif spark_data:
            y = 0.7
            for label, values, unit in spark_data:
                if values:
                    current = values[-1]
                    change = ((values[-1] - values[0]) / values[0] * 100) if len(values) > 1 and values[0] > 0 else 0
                    arrow = "↑" if change > 2 else ("↓" if change < -2 else "→")
                    ax.text(0.15, y, label, fontsize=FONTS.caption,
                            color=COLORS.text_light, ha="left", va="center")
                    ax.text(0.85, y, f"{current} {unit} {arrow}",
                            fontsize=FONTS.caption, color=COLORS.text_primary,
                            ha="right", va="center", fontweight="bold")
                y -= 0.2

    def _draw_daily_distance(self, ax, daily):
        """绘制每日跑量图"""
        distances = [d["distance"] / 1000 for d in daily]
        elevations = [d["elevation"] for d in daily]
        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        x = np.arange(len(distances))
        colors = [COLORS.accent if d == max(distances) and d > 0 else
                  COLORS.bar_normal if d > 0 else "#E0E0E0" for d in distances]

        ax.bar(x, distances, color=colors, width=0.6, edgecolor="none")
        ax.set_xticks(x)
        ax.set_xticklabels(weekdays[:len(distances)], fontsize=FONTS.caption,
                           color=COLORS.text_light)
        ax.set_ylabel("km", fontsize=FONTS.caption, color=COLORS.text_light)
        ax.set_title("Daily Distance", fontsize=FONTS.body,
                      color=COLORS.text_secondary, fontfamily="sans-serif", pad=8)
        ax.set_facecolor(COLORS.bg)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(COLORS.text_light)
        ax.spines["bottom"].set_color(COLORS.text_light)

    def _draw_ai_block(self, ax, title, text):
        """绘制 AI 引用块"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)

        ax.plot([0.06, 0.06], [0.15, 0.85], color=COLORS.accent,
                linewidth=AI_INSIGHT_LEFT_LINE, solid_capstyle="round")
        rect = FancyBboxPatch(
            (0.08, 0.15), 0.9, 0.7,
            boxstyle=f"round,pad=0.02,rounding_size={CARD_RADIUS}",
            facecolor=COLORS.accent, alpha=AI_INSIGHT_BG_ALPHA, edgecolor="none",
        )
        ax.add_patch(rect)
        ax.text(0.12, 0.82, title, fontsize=FONTS.caption,
                color=COLORS.accent, ha="left", va="center",
                fontfamily="sans-serif", fontweight="bold")
        ax.text(0.5, 0.45, text, fontsize=FONTS.body,
                color=COLORS.text_primary, ha="center", va="center",
                fontfamily="sans-serif", wrap=True, linespacing=1.5)

    def _draw_risk_alert(self, ax, alerts):
        """绘制风险预警"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.set_facecolor("#FFF3E0")
        rect = FancyBboxPatch(
            (0.02, 0.1), 0.96, 0.8,
            boxstyle=f"round,pad=0.02,rounding_size={CARD_RADIUS}",
            facecolor="#FF9800", alpha=0.15, edgecolor="#FF9800", linewidth=1,
        )
        ax.add_patch(rect)
        text = "\n".join(f"  {a}" for a in alerts)
        ax.text(0.5, 0.5, text, fontsize=FONTS.caption,
                color="#E65100", ha="center", va="center",
                fontfamily="sans-serif", linespacing=1.6)

    def _draw_training_dist(self, ax, hr_zones):
        """绘制训练强度分布"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)

        ax.text(0.5, 0.95, "Training Distribution", fontsize=FONTS.caption,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")

        pcts = hr_zones.get("percentages", {})
        colors = COLORS.hr_zones if hasattr(COLORS, 'hr_zones') else ["#4FC3F7", "#81C784", "#FFD54F", "#FFB74D", "#E57373"]
        y = 0.75
        for i in range(1, 6):
            pct = pcts.get(i, 0)
            ax.text(0.15, y, f"Z{i}", fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="left", va="center")
            ax.barh(y, pct / 100 * 0.6, left=0.3, height=0.08,
                    color=colors[i-1], alpha=0.8)
            ax.text(0.3 + pct / 100 * 0.6 + 0.02, y, f"{pct:.0f}%",
                    fontsize=FONTS.caption, color=COLORS.text_primary,
                    ha="left", va="center")
            y -= 0.15

    def _draw_vs_last_week(self, ax, vs_last):
        """绘制对比上周"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)

        ax.text(0.5, 0.95, "vs Last Week", fontsize=FONTS.caption,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")

        items = [
            ("Distance", vs_last.get("distance_diff_fmt", "--")),
            ("Avg HR", f"{vs_last.get('avg_hr_diff', 0):+d} bpm"),
        ]
        y = 0.7
        for label, val in items:
            ax.text(0.15, y, label, fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="left", va="center")
            ax.text(0.85, y, val, fontsize=FONTS.caption,
                    color=COLORS.text_primary, ha="right", va="center",
                    fontweight="bold")
            y -= 0.25


if __name__ == "__main__":
    report = WeeklyReportV2(mock=True)
    path = report.generate()
    print(f"Weekly Report generated: {path}")
