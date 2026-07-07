"""
Race Report — 高光时刻与电影感

深色背景，冲击力风格。
核心情绪：Epic（电影感）

信息结构：
1. Hero — 赛事名称 + 核心数据
2. Split Analysis — 前半 vs 后半 + 爬升/下坡
3. Charts — 配速拆分 + 心率区间
4. Critical Moment — 关键时刻
5. Race Intelligence — 四维分析
6. Finish Narrative — 完赛叙事 + 名言
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
    RACE_COLORS as COLORS,
    RACE_FONTS as FONTS,
    RACE_SIZE as SIZE,
    trend_color,
    CARD_RADIUS, AI_INSIGHT_LEFT_LINE, AI_INSIGHT_BG_ALPHA,
)
from data_aggregator import DataAggregator
from ai_narrator import AINarrator


class RaceReport:
    """Race Report 生成器"""

    def __init__(self, mock: bool = True):
        self.mock = mock
        self.aggregator = DataAggregator(mock=mock)
        self.narrator = AINarrator()

    def generate(self, activity_id: int = None) -> str:
        """生成 Race Report，返回文件路径"""
        data = self.aggregator.get_race_data(activity_id)

        result = data["result"]
        splits = data["splits"]
        hr_zones = data["hr_zones"]
        km_splits = data["km_splits"]
        race_intel = data["race_intelligence"]
        first_half = data["first_half_time"]
        second_half = data["second_half_time"]
        hr_drift = data["hr_drift"]

        # AI Commentary
        race_data_for_ai = {
            "result": result,
            "splits": {"first_half": first_half, "second_half": second_half},
            "race_intelligence": race_intel,
            "km_splits": km_splits,
        }
        commentary = self.narrator.generate_race_commentary(race_data_for_ai)
        critical_moment = self.narrator.generate_critical_moment(race_data_for_ai)
        finish_narrative = self.narrator.generate_finish_narrative(race_data_for_ai)

        # 绘图
        fig = self._draw(
            result=result, splits=splits, hr_zones=hr_zones,
            km_splits=km_splits, race_intel=race_intel,
            first_half=first_half, second_half=second_half,
            hr_drift=hr_drift, commentary=commentary,
            critical_moment=critical_moment, finish_narrative=finish_narrative,
        )

        output = Path(__file__).resolve().parent / "output" / "race_report.png"
        output.parent.mkdir(exist_ok=True)
        fig.savefig(str(output), dpi=SIZE.dpi, bbox_inches="tight",
                    facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return str(output)

    def _draw(self, result, splits, hr_zones, km_splits, race_intel,
              first_half, second_half, hr_drift, commentary,
              critical_moment, finish_narrative):
        """绘制 Race Report"""
        fig = plt.figure(figsize=(SIZE.width, SIZE.height), dpi=SIZE.dpi)
        fig.set_facecolor(COLORS.bg)

        grid = gs.GridSpec(
            6, 2, figure=fig,
            height_ratios=[1.5, 1, 1.2, 0.8, 1, 1.2],
            hspace=0.15, wspace=0.25,
            left=0.08, right=0.92, top=0.96, bottom=0.03,
        )

        row = 0

        # ── Row 0: Hero ──
        ax = fig.add_subplot(grid[row, :])
        self._draw_hero(ax, result)
        row += 1

        # ── Row 1: Split Analysis ──
        ax = fig.add_subplot(grid[row, :])
        self._draw_split_analysis(ax, first_half, second_half, race_intel)
        row += 1

        # ── Row 2: Charts — Pace + HR Zones ──
        ax_pace = fig.add_subplot(grid[row, 0])
        ax_hr = fig.add_subplot(grid[row, 1])
        self._draw_pace_chart(ax_pace, km_splits)
        self._draw_hr_zones(ax_hr, hr_zones)
        row += 1

        # ── Row 3: Critical Moment ──
        ax = fig.add_subplot(grid[row, :])
        self._draw_critical_moment(ax, critical_moment)
        row += 1

        # ── Row 4: Race Intelligence ──
        ax = fig.add_subplot(grid[row, :])
        self._draw_race_intelligence(ax, race_intel)
        row += 1

        # ── Row 5: Finish Narrative ──
        ax = fig.add_subplot(grid[row, :])
        self._draw_finish_narrative(ax, finish_narrative)

        return fig

    def _draw_hero(self, ax, result):
        """Hero — 赛事名称 + 核心数据"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.set_facecolor(COLORS.bg)

        # 顶部金色装饰线
        ax.plot([0.15, 0.85], [0.92, 0.92], color=COLORS.accent,
                linewidth=2, alpha=0.6)

        name = result.get("name", "Race")
        ax.text(0.5, 0.7, name, fontsize=FONTS.title,
                color=COLORS.text_primary, ha="center", va="center",
                fontweight="bold", fontfamily="sans-serif")

        date_str = result.get("date", "")
        ax.text(0.5, 0.55, date_str, fontsize=FONTS.caption,
                color=COLORS.text_light, ha="center", va="center",
                fontfamily="sans-serif")

        # 核心三数据
        dist_m = result.get('distance', 0)
        dist_km = dist_m / 1000 if dist_m > 100 else dist_m
        hero_items = [
            (f"{dist_km:.1f}" if dist_km < 100 else f"{dist_km:.0f}", "km"),
            (result.get("finish_time", "--"), ""),
            (f"{result.get('elevation', 0)}", "m"),
        ]
        for i, (val, unit) in enumerate(hero_items):
            x = 0.2 + i * 0.3
            ax.text(x, 0.32, val, fontsize=FONTS.hero,
                    color=COLORS.accent, ha="center", va="center",
                    fontweight="bold", fontfamily="sans-serif")
            ax.text(x, 0.12, unit, fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="center", va="center",
                    fontfamily="sans-serif")

    def _draw_split_analysis(self, ax, first_half, second_half, race_intel):
        """Split Analysis — 前半 vs 后半"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.set_facecolor(COLORS.bg)

        ax.text(0.5, 0.92, "Split Analysis", fontsize=FONTS.body,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")

        # 前半 vs 后半
        items = [
            ("First Half", first_half, 0.25),
            ("Second Half", second_half, 0.75),
        ]
        for label, time_str, x in items:
            ax.text(x, 0.65, time_str, fontsize=FONTS.hero,
                    color=COLORS.text_primary, ha="center", va="center",
                    fontweight="bold", fontfamily="sans-serif")
            ax.text(x, 0.35, label, fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="center", va="center",
                    fontfamily="sans-serif")

        # 分隔线
        ax.plot([0.5, 0.5], [0.3, 0.85], color=COLORS.text_light,
                linewidth=0.5, alpha=0.3)

    def _draw_pace_chart(self, ax, km_splits):
        """配速拆分图"""
        if not km_splits:
            ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
            ax.set_facecolor(COLORS.bg)
            ax.text(0.5, 0.5, "No split data", fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="center", va="center")
            return

        paces = []
        hrs = []
        for s in km_splits:
            speed = s.get("averageSpeed", 0)
            if speed > 0:
                paces.append(1000 / speed / 60)
            else:
                paces.append(0)
            hrs.append(s.get("averageHR", 0))

        n = len(paces)
        x = np.arange(n)

        # 渐变色配速柱状图
        max_pace = max(paces) if paces else 1
        colors = []
        for p in paces:
            if p > 0:
                intensity = p / max_pace
                r = int(255 * intensity)
                g = int(215 * (1 - intensity * 0.5))
                b = int(0)
                colors.append(f"#{r:02x}{g:02x}{b:02x}")
            else:
                colors.append("#555555")

        ax.bar(x, paces, color=colors, width=0.6, edgecolor="none")

        ax.set_ylabel("Pace (min/km)", fontsize=FONTS.caption,
                       color=COLORS.text_light, fontfamily="sans-serif")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{i+1}" for i in range(n)],
                           fontsize=FONTS.caption, color=COLORS.text_light)
        ax.invert_yaxis()
        ax.set_facecolor(COLORS.bg)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(COLORS.text_light)
        ax.spines["bottom"].set_color(COLORS.text_light)
        ax.tick_params(colors=COLORS.text_light, labelsize=FONTS.caption)
        ax.set_title("Pace Split", fontsize=FONTS.caption,
                      color=COLORS.text_secondary, fontfamily="sans-serif", pad=6)

    def _draw_hr_zones(self, ax, hr_zones):
        """心率区间分布"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.set_facecolor(COLORS.bg)

        ax.text(0.5, 0.92, "HR Zones", fontsize=FONTS.caption,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")

        total = sum(z.get("secsInZone", 0) for z in hr_zones) if hr_zones else 1
        zone_colors = ["#4FC3F7", "#81C784", "#FFD54F", "#FFB74D", "#E57373"]
        y = 0.78
        for i, z in enumerate(hr_zones):
            secs = z.get("secsInZone", 0)
            pct = secs / total * 100 if total > 0 else 0
            zone_num = z.get("zoneNumber", i + 1)
            color = zone_colors[i % len(zone_colors)]

            ax.text(0.12, y, f"Z{zone_num}", fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="left", va="center")
            ax.barh(y, pct / 100 * 0.55, left=0.25, height=0.08,
                    color=color, alpha=0.8)
            ax.text(0.25 + pct / 100 * 0.55 + 0.02, y, f"{pct:.0f}%",
                    fontsize=FONTS.caption, color=COLORS.text_primary,
                    ha="left", va="center")
            y -= 0.15

    def _draw_critical_moment(self, ax, text):
        """Critical Moment — 关键时刻"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.set_facecolor(COLORS.bg)

        ax.plot([0.06, 0.06], [0.15, 0.85], color=COLORS.accent,
                linewidth=AI_INSIGHT_LEFT_LINE, solid_capstyle="round")
        rect = FancyBboxPatch(
            (0.08, 0.15), 0.9, 0.7,
            boxstyle=f"round,pad=0.02,rounding_size={CARD_RADIUS}",
            facecolor=COLORS.accent, alpha=0.1, edgecolor="none",
        )
        ax.add_patch(rect)

        ax.text(0.12, 0.82, "Critical Moment", fontsize=FONTS.caption,
                color=COLORS.accent, ha="left", va="center",
                fontfamily="sans-serif", fontweight="bold")
        ax.text(0.5, 0.45, text, fontsize=FONTS.body,
                color=COLORS.text_primary, ha="center", va="center",
                fontfamily="sans-serif", wrap=True, linespacing=1.5)

    def _draw_race_intelligence(self, ax, race_intel):
        """Race Intelligence — 四维分析"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.set_facecolor(COLORS.bg)

        ax.text(0.5, 0.92, "Race Intelligence", fontsize=FONTS.body,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")

        items = [
            ("Fuel Timing", race_intel.get("fuel_timing", "--")),
            ("HR Collapse", race_intel.get("hr_collapse", "--")),
            ("Climbing", race_intel.get("climbing_efficiency", "--")),
            ("Downhill", race_intel.get("downhill_control", "--")),
        ]
        positions = [(0.25, 0.65), (0.75, 0.65), (0.25, 0.25), (0.75, 0.25)]
        for (label, value), (px, py) in zip(items, positions):
            ax.text(px, py + 0.12, label, fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="center", va="center",
                    fontfamily="sans-serif")
            ax.text(px, py - 0.05, value, fontsize=FONTS.caption,
                    color=COLORS.text_primary, ha="center", va="center",
                    fontfamily="sans-serif", fontweight="bold")

    def _draw_finish_narrative(self, ax, text):
        """Finish Narrative — 完赛叙事"""
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.set_facecolor(COLORS.bg)

        # 杂志引用样式
        ax.plot([0.06, 0.06], [0.1, 0.9], color=COLORS.accent,
                linewidth=AI_INSIGHT_LEFT_LINE, solid_capstyle="round")
        rect = FancyBboxPatch(
            (0.08, 0.1), 0.9, 0.8,
            boxstyle=f"round,pad=0.02,rounding_size={CARD_RADIUS}",
            facecolor=COLORS.accent, alpha=0.08, edgecolor="none",
        )
        ax.add_patch(rect)

        ax.text(0.12, 0.85, "Finish", fontsize=FONTS.caption,
                color=COLORS.accent, ha="left", va="center",
                fontfamily="sans-serif", fontweight="bold")
        ax.text(0.5, 0.5, text, fontsize=FONTS.body,
                color=COLORS.text_primary, ha="center", va="center",
                fontfamily="sans-serif", wrap=True, linespacing=1.6)

        # 名言收尾
        ax.text(0.5, 0.12, '"The miracle is not that I finished, but that I had the courage to start."',
                fontsize=FONTS.caption, color=COLORS.text_light,
                ha="center", va="center", fontfamily="sans-serif",
                fontstyle="italic", alpha=0.6)


if __name__ == "__main__":
    report = RaceReport(mock=True)
    path = report.generate()
    print(f"Race Report generated: {path}")
