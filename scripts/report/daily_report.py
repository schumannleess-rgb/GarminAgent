"""
Daily Report — 单次训练复盘

数据感风格，标准海报。
核心情绪：Focus（专注）

信息结构：
1. Header — 训练标题 + 日期/地点
2. Hero Data — Distance / Duration / Pace / Elevation
3. Recovery + Efficiency 双模块
4. Pace Split Chart
5. AI Insight
6. Trend Comparison
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs
from matplotlib.patches import FancyBboxPatch
from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_styles import (
    DAILY_COLORS as COLORS,
    DAILY_FONTS as FONTS,
    DAILY_SIZE as SIZE,
    trend_color,
    CARD_RADIUS, CARD_PADDING, SECTION_SPACING,
    AI_INSIGHT_LEFT_LINE, AI_INSIGHT_BG_ALPHA,
)
from data_aggregator import DataAggregator
from ai_narrator import AINarrator


class DailyReport:
    """Daily Report 生成器"""

    def __init__(self, mock: bool = True):
        self.mock = mock
        self.aggregator = DataAggregator(mock=mock)
        self.narrator = AINarrator()

    def generate(self, activity_id: int = None) -> str:
        """生成 Daily Report，返回文件路径"""
        data = self.aggregator.get_post_run_data(activity_id)

        activity = data["activity"]
        splits = data["splits"]
        health = data["health_before"]

        # 提取数据
        distance = activity.get("distance", 0) / 1000  # m -> km
        duration_secs = activity.get("duration", 0)
        duration_fmt = self._format_duration(duration_secs)
        avg_speed = activity.get("averageSpeed", 0)
        pace = self._format_pace(avg_speed) if avg_speed > 0 else "--"
        elevation = activity.get("elevationGain", 0)
        name = activity.get("activityName", "Training")
        date_str = activity.get("startTimeLocal", "")[:10]

        # Recovery
        hrv = self.aggregator._extract_hrv(health)
        sleep_score = self.aggregator._extract_sleep_score(health)
        recovery_time = self.aggregator._calc_recovery_time(health)

        # Efficiency
        efficiency = self.aggregator._calc_efficiency_metrics(activity)
        hr_drift = self.aggregator._calc_hr_drift(splits)

        # AI Insight
        ai_insight = self.narrator.generate_daily_insight(
            activity={"pace": pace, "distance": distance, "avg_hr": activity.get("averageHR", 0), "splits": splits},
            efficiency={"hr_drift": hr_drift, "cadence": efficiency["cadence"]},
        )

        # HR Zones
        hr_zones = data.get("hr_zones", [])

        # 绘图
        fig = self._draw(
            name=name, date_str=date_str,
            distance=distance, duration=duration_fmt, pace=pace, elevation=elevation,
            hrv=hrv, sleep_score=sleep_score, recovery_time=recovery_time,
            efficiency=efficiency, hr_drift=hr_drift,
            splits=splits, hr_zones=hr_zones,
            ai_insight=ai_insight,
        )

        output = Path(__file__).resolve().parent / "output" / "daily_report.png"
        output.parent.mkdir(exist_ok=True)
        fig.savefig(str(output), dpi=SIZE.dpi, bbox_inches="tight",
                    facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return str(output)

    def _draw(self, name, date_str, distance, duration, pace, elevation,
              hrv, sleep_score, recovery_time,
              efficiency, hr_drift, splits, hr_zones, ai_insight):
        """绘制 Daily Report"""
        fig = plt.figure(figsize=(SIZE.width, SIZE.height), dpi=SIZE.dpi)
        fig.set_facecolor(COLORS.bg)

        grid = gs.GridSpec(
            5, 2, figure=fig,
            height_ratios=[0.8, 1, 1.2, 1.5, 1],
            hspace=0.12, wspace=0.25,
            left=0.08, right=0.92, top=0.95, bottom=0.04,
        )

        # ── Row 0: Header ──
        ax_header = fig.add_subplot(grid[0, :])
        ax_header.set_xlim(0, 1)
        ax_header.set_ylim(0, 1)
        ax_header.axis("off")
        ax_header.set_facecolor(COLORS.bg)
        ax_header.text(0.5, 0.7, name, fontsize=FONTS.title,
                       color=COLORS.text_primary, ha="center", va="center",
                       fontweight="bold", fontfamily="sans-serif")
        ax_header.text(0.5, 0.2, date_str, fontsize=FONTS.caption,
                       color=COLORS.text_light, ha="center", va="center",
                       fontfamily="sans-serif")

        # ── Row 1: Hero Data ──
        ax_hero = fig.add_subplot(grid[1, :])
        ax_hero.set_xlim(0, 1)
        ax_hero.set_ylim(0, 1)
        ax_hero.axis("off")
        ax_hero.set_facecolor(COLORS.bg)

        hero_items = [
            (f"{distance:.1f}", "km"),
            (duration, ""),
            (pace, "min/km"),
            (f"{elevation}", "m"),
        ]
        for i, (val, unit) in enumerate(hero_items):
            x = 0.12 + i * 0.23
            ax_hero.text(x, 0.65, val, fontsize=FONTS.hero,
                         color=COLORS.text_primary, ha="center", va="center",
                         fontweight="bold", fontfamily="sans-serif")
            ax_hero.text(x, 0.2, unit, fontsize=FONTS.caption,
                         color=COLORS.text_light, ha="center", va="center",
                         fontfamily="sans-serif")

        # ── Row 2: Recovery + Efficiency ──
        ax_rec = fig.add_subplot(grid[2, 0])
        ax_eff = fig.add_subplot(grid[2, 1])

        self._draw_metric_block(ax_rec, "Recovery", [
            ("HRV", f"{hrv} ms"),
            ("Sleep", f"{sleep_score}/100"),
            ("Recovery", recovery_time),
        ])
        self._draw_metric_block(ax_eff, "Efficiency", [
            ("Cadence", f"{efficiency['cadence']} spm"),
            ("Stride", f"{efficiency['stride_length']:.2f} m"),
            ("GCT", f"{efficiency['ground_contact_time']} ms"),
            ("Vert Ratio", f"{efficiency['vertical_ratio']}%"),
            ("HR Drift", f"{'+' if hr_drift >= 0 else ''}{hr_drift}%"),
        ])

        # ── Row 3: Pace Chart ──
        ax_pace = fig.add_subplot(grid[3, :])
        self._draw_pace_chart(ax_pace, splits)

        # ── Row 4: AI Insight ──
        ax_ai = fig.add_subplot(grid[4, :])
        self._draw_ai_insight(ax_ai, ai_insight)

        return fig

    def _draw_metric_block(self, ax, title, items):
        """绘制指标块"""
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_facecolor(COLORS.bg)

        ax.text(0.5, 0.95, title, fontsize=FONTS.body,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")

        y = 0.75
        for label, value in items:
            ax.text(0.1, y, label, fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="left", va="center",
                    fontfamily="sans-serif")
            ax.text(0.9, y, value, fontsize=FONTS.caption,
                    color=COLORS.text_primary, ha="right", va="center",
                    fontfamily="sans-serif", fontweight="bold")
            y -= 0.18

    def _draw_pace_chart(self, ax, splits):
        """绘制配速拆分图"""
        if not splits:
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            ax.text(0.5, 0.5, "No split data", fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="center", va="center")
            return

        paces = []
        hrs = []
        for s in splits:
            speed = s.get("averageSpeed", 0)
            if speed > 0:
                paces.append(1000 / speed / 60)  # m/s -> min/km
            else:
                paces.append(0)
            hrs.append(s.get("averageHR", 0))

        n = len(paces)
        x = np.arange(n)

        # 配速柱状图（倒序）
        colors = [COLORS.accent if p == max(paces) and p > 0 else COLORS.bar_normal for p in paces]
        ax.bar(x, paces, color=colors, width=0.6, edgecolor="none")

        # 平均配速线
        avg_pace = sum(p for p in paces if p > 0) / max(1, len([p for p in paces if p > 0]))
        if avg_pace > 0:
            ax.axhline(y=avg_pace, color=COLORS.accent_dark, linestyle="--",
                       linewidth=1, alpha=0.6)

        ax.set_ylabel("Pace (min/km)", fontsize=FONTS.caption,
                       color=COLORS.text_light, fontfamily="sans-serif")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{i+1}km" for i in range(n)],
                           fontsize=FONTS.caption, color=COLORS.text_light)
        ax.invert_yaxis()
        ax.set_facecolor(COLORS.bg)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(COLORS.text_light)
        ax.spines["bottom"].set_color(COLORS.text_light)

        # 心率折线（右 Y 轴）
        ax2 = ax.twinx()
        ax2.plot(x, hrs, color="#E57373", marker="o", markersize=3, linewidth=1.5)
        ax2.set_ylabel("HR (bpm)", fontsize=FONTS.caption,
                        color="#E57373", fontfamily="sans-serif")
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_color("#E57373")
        ax2.tick_params(axis="y", colors="#E57373", labelsize=FONTS.caption)

    def _draw_ai_insight(self, ax, text):
        """绘制 AI Insight"""
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_facecolor(COLORS.bg)

        ax.plot([0.06, 0.06], [0.15, 0.85], color=COLORS.accent,
                linewidth=AI_INSIGHT_LEFT_LINE, solid_capstyle="round")

        rect = FancyBboxPatch(
            (0.08, 0.15), 0.9, 0.7,
            boxstyle=f"round,pad=0.02,rounding_size={CARD_RADIUS}",
            facecolor=COLORS.accent, alpha=AI_INSIGHT_BG_ALPHA,
            edgecolor="none",
        )
        ax.add_patch(rect)

        ax.text(0.12, 0.82, "AI Insight", fontsize=FONTS.caption,
                color=COLORS.accent, ha="left", va="center",
                fontfamily="sans-serif", fontweight="bold")
        ax.text(0.5, 0.45, text, fontsize=FONTS.body,
                color=COLORS.text_primary, ha="center", va="center",
                fontfamily="sans-serif", wrap=True, linespacing=1.5)

    @staticmethod
    def _format_duration(secs):
        """格式化时长"""
        h = int(secs) // 3600
        m = (int(secs) % 3600) // 60
        s = int(secs) % 60
        return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"

    @staticmethod
    def _format_pace(speed_ms):
        """格式化配速 (m/s -> min/km)"""
        pace_secs = 1000 / speed_ms
        m = int(pace_secs) // 60
        s = int(pace_secs) % 60
        return f"{m}:{s:02d}"


if __name__ == "__main__":
    report = DailyReport(mock=True)
    path = report.generate()
    print(f"Daily Report generated: {path}")
