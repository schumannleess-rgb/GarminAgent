"""
Monthly Report — 成长与仪式感

分析风格，长海报。
核心情绪：Achievement（仪式感）

信息结构：
1. Opening Hero — 大标题 + 月份
2. Achievement — 核心成就（先于 Training Overview）
3. Training Overview — 四大数字
4. Recovery Summary + Efficiency Growth（左右布局）
5. Weekly Trend 图表
6. AI Monthly Narrative
7. Personal Best（奖牌样式）
8. Next Month Goal
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs
from matplotlib.patches import FancyBboxPatch, Circle
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_styles import (
    MONTHLY_COLORS as COLORS,
    MONTHLY_FONTS as FONTS,
    MONTHLY_SIZE as SIZE,
    trend_color,
    CARD_RADIUS, AI_INSIGHT_LEFT_LINE, AI_INSIGHT_BG_ALPHA,
)
from data_aggregator import DataAggregator
from ai_narrator import AINarrator


class MonthlyReport:
    """Monthly Report 生成器"""

    def __init__(self, mock: bool = True):
        self.mock = mock
        self.aggregator = DataAggregator(mock=mock)
        self.narrator = AINarrator()

    def generate(self, months_ago: int = 0) -> str:
        """生成 Monthly Report，返回文件路径"""
        data = self.aggregator.get_monthly_data(months_ago)

        summary = data["summary"]
        weekly_trend = data["weekly_trend"]
        highlights = data["highlights"]
        pb_records = data.get("pb_records", {})

        # 从 highlights 构建成就
        achievements = self._build_achievements(highlights, summary)

        # AI Narrative
        monthly_data_for_ai = {
            "training_overview": {
                "days": summary.get("training_days", 0),
                "distance": summary.get("total_distance", 0) / 1000,
            },
            "recovery_summary": {"recovery_stability": "stable"},
            "efficiency_growth": {"aerobic": "+0%", "cadence_stability": "+0%", "hr_drift": "+0%"},
        }
        ai_narrative = self.narrator.generate_monthly_narrative(monthly_data_for_ai)

        # 绘图
        fig = self._draw(
            month_start=data["month_start"],
            summary=summary,
            achievements=achievements,
            weekly_trend=weekly_trend,
            highlights=highlights,
            pb_records=pb_records,
            ai_narrative=ai_narrative,
        )

        output = Path(__file__).resolve().parent / "output" / "monthly_report.png"
        output.parent.mkdir(exist_ok=True)
        fig.savefig(str(output), dpi=SIZE.dpi, bbox_inches="tight",
                    facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return str(output)

    def _build_achievements(self, highlights, summary):
        """从 highlights 和 summary 构建成就列表"""
        items = []
        bp = highlights.get("best_pace", {})
        if bp.get("pace"):
            items.append(f"Best Pace: {bp['pace']} ({bp.get('name', '')})")
        lo = highlights.get("longest", {})
        if lo.get("distance"):
            items.append(f"Longest Run: {lo['distance']} ({lo.get('name', '')})")
        me = highlights.get("most_elevation", {})
        if me.get("elevation"):
            items.append(f"Most Elevation: {me['elevation']} ({me.get('name', '')})")
        if not items:
            items = ["Keep training, achievements await!"]
        return items

    def _draw(self, month_start, summary, achievements, weekly_trend,
              highlights, pb_records, ai_narrative):
        """绘制 Monthly Report"""
        fig = plt.figure(figsize=(SIZE.width, SIZE.height), dpi=SIZE.dpi)
        fig.set_facecolor(COLORS.bg)

        grid = gs.GridSpec(
            8, 2, figure=fig,
            height_ratios=[1.5, 1, 0.8, 1, 1.2, 1.2, 1, 0.8],
            hspace=0.15, wspace=0.25,
            left=0.08, right=0.92, top=0.96, bottom=0.03,
        )

        row = 0

        # ── Row 0: Opening Hero ──
        ax = fig.add_subplot(grid[row, :])
        self._draw_hero(ax, month_start)
        row += 1

        # ── Row 1: Achievement ──
        ax = fig.add_subplot(grid[row, :])
        self._draw_achievements(ax, achievements)
        row += 1

        # ── Row 2: Training Overview ──
        ax = fig.add_subplot(grid[row, :])
        self._draw_training_overview(ax, summary)
        row += 1

        # ── Row 3: Recovery + Efficiency Growth ──
        ax_rec = fig.add_subplot(grid[row, 0])
        ax_eff = fig.add_subplot(grid[row, 1])
        self._draw_recovery_summary(ax_rec, summary)
        self._draw_efficiency_growth(ax_eff)
        row += 1

        # ── Row 4: Weekly Trend ──
        ax_trend = fig.add_subplot(grid[row, :])
        self._draw_weekly_trend(ax_trend, weekly_trend)
        row += 1

        # ── Row 5: AI Monthly Narrative ──
        ax_ai = fig.add_subplot(grid[row, :])
        self._draw_ai_narrative(ax_ai, ai_narrative)
        row += 1

        # ── Row 6: Personal Best ──
        ax_pb = fig.add_subplot(grid[row, :])
        self._draw_personal_best(ax_pb, pb_records)
        row += 1

        # ── Row 7: Next Month Goal ──
        ax_goal = fig.add_subplot(grid[row, :])
        self._draw_next_month_goal(ax_goal)

        return fig

    def _draw_hero(self, ax, month_start):
        """Opening Hero — 大标题"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        rect = FancyBboxPatch(
            (0, 0), 1, 1,
            boxstyle="round,pad=0",
            facecolor=COLORS.accent, alpha=0.12, edgecolor="none",
        )
        ax.add_patch(rect)
        ax.set_facecolor(COLORS.bg)

        month_names = ["", "January", "February", "March", "April",
                       "May", "June", "July", "August", "September",
                       "October", "November", "December"]
        month_label = month_names[month_start.month] if month_start.month <= 12 else "Month"

        ax.text(0.5, 0.65, f"{month_label.upper()} RECAP",
                fontsize=FONTS.title, color=COLORS.text_primary,
                ha="center", va="center", fontweight="bold",
                fontfamily="sans-serif")
        ax.text(0.5, 0.3, str(month_start.year),
                fontsize=FONTS.hero, color=COLORS.accent,
                ha="center", va="center", fontweight="bold",
                fontfamily="sans-serif", alpha=0.4)

    def _draw_achievements(self, ax, achievements):
        """Achievement — 核心成就（徽章样式）"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)

        ax.text(0.5, 0.92, "Monthly Achievements", fontsize=FONTS.body,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")

        badge_colors = ["#FFD700", "#C0C0C0", "#CD7F32"]
        y = 0.7
        for i, item in enumerate(achievements[:3]):
            color = badge_colors[i % len(badge_colors)]
            circle = Circle((0.08, y), 0.025, transform=ax.transAxes,
                           facecolor=color, alpha=0.3, edgecolor=color, linewidth=1.5)
            ax.add_patch(circle)
            ax.text(0.08, y, str(i + 1), fontsize=FONTS.caption,
                    color=color, ha="center", va="center", fontweight="bold",
                    transform=ax.transAxes)
            ax.text(0.14, y, item, fontsize=FONTS.caption,
                    color=COLORS.text_primary, ha="left", va="center",
                    fontfamily="sans-serif")
            y -= 0.22

    def _draw_training_overview(self, ax, summary):
        """Training Overview — 四大数字"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)

        hero_items = [
            (summary["total_distance_fmt"], "Distance"),
            (summary["total_duration_fmt"], "Time"),
            (f"{summary['total_elevation']}", "Elevation"),
            (f"{summary.get('training_days', 0)}", "Days"),
        ]
        for i, (val, label) in enumerate(hero_items):
            x = 0.12 + i * 0.23
            ax.text(x, 0.7, val, fontsize=FONTS.hero,
                    color=COLORS.text_primary, ha="center", va="center",
                    fontweight="bold", fontfamily="sans-serif")
            ax.text(x, 0.25, label, fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="center", va="center",
                    fontfamily="sans-serif")

    def _draw_recovery_summary(self, ax, summary):
        """Recovery Summary"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)

        ax.text(0.5, 0.95, "Recovery Summary", fontsize=FONTS.body,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")

        avg_hr = summary.get("avg_hr", 0)
        training_days = summary.get("training_days", 0)
        items = [
            ("Avg HR", f"{avg_hr} bpm"),
            ("Training Days", f"{training_days} days"),
            ("Stability", "Stable"),
        ]
        y = 0.7
        for label, value in items:
            ax.text(0.15, y, label, fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="left", va="center",
                    fontfamily="sans-serif")
            ax.text(0.85, y, value, fontsize=FONTS.caption,
                    color=COLORS.text_primary, ha="right", va="center",
                    fontfamily="sans-serif", fontweight="bold")
            y -= 0.25

    def _draw_efficiency_growth(self, ax):
        """Efficiency Growth"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)

        ax.text(0.5, 0.95, "Efficiency Growth", fontsize=FONTS.body,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")

        items = [
            ("Aerobic", "+0%"),
            ("Cadence", "+0%"),
            ("HR Drift", "+0%"),
        ]
        y = 0.7
        for label, val_str in items:
            ax.text(0.15, y, label, fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="left", va="center",
                    fontfamily="sans-serif")
            ax.text(0.85, y, val_str, fontsize=FONTS.caption,
                    color=COLORS.text_primary, ha="right", va="center",
                    fontfamily="sans-serif", fontweight="bold")
            y -= 0.25

    def _draw_weekly_trend(self, ax, weekly_trend):
        """Weekly Trend — 周跑量趋势图"""
        if not weekly_trend:
            ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
            ax.set_facecolor(COLORS.bg)
            ax.text(0.5, 0.5, "No weekly trend data", fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="center", va="center")
            return

        distances = [w.get("distance", 0) / 1000 for w in weekly_trend]
        elevations = [w.get("elevation", 0) for w in weekly_trend]
        n = len(distances)
        x = np.arange(n)

        colors = [COLORS.accent if d == max(distances) and d > 0 else
                  COLORS.bar_normal if d > 0 else "#E0E0E0" for d in distances]

        ax.bar(x, distances, color=colors, width=0.5, edgecolor="none")
        ax.set_xticks(x)
        ax.set_xticklabels([f"W{i+1}" for i in range(n)],
                           fontsize=FONTS.caption, color=COLORS.text_light)
        ax.set_ylabel("km", fontsize=FONTS.caption, color=COLORS.text_light)
        ax.set_title("Weekly Trend", fontsize=FONTS.body,
                      color=COLORS.text_secondary, fontfamily="sans-serif", pad=8)
        ax.set_facecolor(COLORS.bg)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(COLORS.text_light)
        ax.spines["bottom"].set_color(COLORS.text_light)

        if any(e > 0 for e in elevations):
            ax2 = ax.twinx()
            ax2.plot(x, elevations, color=COLORS.accent_dark, marker="s",
                     markersize=4, linewidth=1.5, linestyle="--")
            ax2.set_ylabel("Elevation (m)", fontsize=FONTS.caption,
                           color=COLORS.accent_dark, fontfamily="sans-serif")
            ax2.spines["top"].set_visible(False)
            ax2.spines["right"].set_color(COLORS.accent_dark)
            ax2.tick_params(axis="y", colors=COLORS.accent_dark, labelsize=FONTS.caption)

    def _draw_ai_narrative(self, ax, text):
        """AI Monthly Narrative — 杂志编辑推荐样式"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)

        ax.plot([0.06, 0.06], [0.1, 0.9], color=COLORS.accent,
                linewidth=AI_INSIGHT_LEFT_LINE, solid_capstyle="round")
        rect = FancyBboxPatch(
            (0.08, 0.1), 0.9, 0.8,
            boxstyle=f"round,pad=0.02,rounding_size={CARD_RADIUS}",
            facecolor=COLORS.accent, alpha=AI_INSIGHT_BG_ALPHA, edgecolor="none",
        )
        ax.add_patch(rect)

        ax.text(0.12, 0.85, "AI Monthly Narrative", fontsize=FONTS.caption,
                color=COLORS.accent, ha="left", va="center",
                fontfamily="sans-serif", fontweight="bold")
        ax.text(0.5, 0.45, text, fontsize=FONTS.body,
                color=COLORS.text_primary, ha="center", va="center",
                fontfamily="sans-serif", wrap=True, linespacing=1.6)

    def _draw_personal_best(self, ax, pb_records):
        """Personal Best — 奖牌/徽章样式"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)

        ax.text(0.5, 0.92, "Personal Best", fontsize=FONTS.body,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")

        labels = {"5k": "5K", "10k": "10K", "half_marathon": "Half",
                  "full_marathon": "Full", "trail": "Trail"}
        medal_colors = ["#FFD700", "#FFD700", "#C0C0C0", "#CD7F32", "#CD7F32"]

        y = 0.75
        for i, (dist, info) in enumerate(pb_records.items()):
            label = labels.get(dist, dist)
            time_str = info.get("time", "--")
            date_str = info.get("date", "--")
            color = medal_colors[i % len(medal_colors)]

            circle = Circle((0.1, y), 0.025, transform=ax.transAxes,
                           facecolor=color, alpha=0.25, edgecolor=color, linewidth=1.5)
            ax.add_patch(circle)
            ax.text(0.1, y, "★", fontsize=FONTS.caption,
                    color=color, ha="center", va="center",
                    transform=ax.transAxes)
            ax.text(0.16, y, f"{label}:  {time_str}", fontsize=FONTS.caption,
                    color=COLORS.text_primary, ha="left", va="center",
                    fontfamily="sans-serif", fontweight="bold")
            ax.text(0.85, y, date_str, fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="right", va="center",
                    fontfamily="sans-serif")
            y -= 0.18

        if not pb_records:
            ax.text(0.5, 0.5, "No PB records yet", fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="center", va="center")

    def _draw_next_month_goal(self, ax):
        """Next Month Goal"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.set_facecolor(COLORS.bg)

        ax.text(0.5, 0.7, "Next Month Goals", fontsize=FONTS.body,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")
        ax.text(0.5, 0.3, "Keep pushing forward.", fontsize=FONTS.caption,
                color=COLORS.text_light, ha="center", va="center",
                fontfamily="sans-serif")


if __name__ == "__main__":
    report = MonthlyReport(mock=True)
    path = report.generate()
    print(f"Monthly Report generated: {path}")
