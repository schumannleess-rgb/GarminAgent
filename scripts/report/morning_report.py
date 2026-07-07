"""
Morning Report — 身体状态卡

极简风格，竖版，手机截图即分享。
核心情绪：Calm（安静的高级感）

信息结构：
1. Readiness Score（大数字）
2. Recovery + Sleep 双列
3. AI Insight（引用块）
4. Today's Suggestion
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_styles import (
    MORNING_COLORS as COLORS,
    MORNING_FONTS as FONTS,
    MORNING_SIZE as SIZE,
    readiness_color,
    CARD_RADIUS, AI_INSIGHT_LEFT_LINE, AI_INSIGHT_BG_ALPHA,
)
from data_aggregator import DataAggregator
from ai_narrator import AINarrator


class MorningReport:
    """Morning Report 生成器"""

    def __init__(self, mock: bool = True):
        self.mock = mock
        self.aggregator = DataAggregator(mock=mock)
        self.narrator = AINarrator()

    def generate(self) -> str:
        """生成 Morning Report，返回文件路径"""
        data = self.aggregator.get_morning_call_data()
        health = data["health"]
        training_advice = data["training_advice"]

        # 提取健康指标
        hrv = self.aggregator._extract_hrv(health)
        rhr = self.aggregator._extract_rhr(health)
        sleep_score = self.aggregator._extract_sleep_score(health)
        sleep_duration = self.aggregator._extract_sleep_duration(health)
        readiness = training_advice.get("readiness_score", 50)
        recovery_time = self.aggregator._calc_recovery_time(health)
        fatigue = self.aggregator._calc_fatigue_level(health)

        # AI Insight
        hrv_baseline = self.aggregator._calc_hrv_baseline(data.get("week_health_trend", []))
        insight_health = {
            "hrv": hrv, "hrv_baseline": hrv_baseline, "rhr": rhr,
            "sleep_score": sleep_score, "sleep_duration": sleep_duration,
            "readiness": readiness,
        }
        ai_insight = self.narrator.generate_morning_insight(insight_health)
        suggestion = self.narrator.generate_morning_suggestion(insight_health)

        # 绘图
        fig = self._draw(
            readiness=readiness,
            hrv=hrv, rhr=rhr,
            sleep_score=sleep_score, sleep_duration=sleep_duration,
            recovery_time=recovery_time, fatigue=fatigue,
            ai_insight=ai_insight, suggestion=suggestion,
        )

        output = Path(__file__).resolve().parent / "output" / "morning_report.png"
        output.parent.mkdir(exist_ok=True)
        fig.savefig(str(output), dpi=SIZE.dpi, bbox_inches="tight",
                    facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close(fig)
        return str(output)

    def _draw(self, readiness, hrv, rhr, sleep_score, sleep_duration,
              recovery_time, fatigue, ai_insight, suggestion):
        """绘制 Morning Report"""
        fig = plt.figure(figsize=(SIZE.width, SIZE.height), dpi=SIZE.dpi)
        fig.set_facecolor(COLORS.bg)

        # 使用 GridSpec 布局
        import matplotlib.gridspec as gs
        grid = gs.GridSpec(
            5, 2, figure=fig,
            height_ratios=[3, 1.5, 1.2, 2, 1],
            hspace=0.08, wspace=0.3,
            left=0.1, right=0.9, top=0.92, bottom=0.05,
        )

        # ── Row 0: Readiness Score ──
        ax_score = fig.add_subplot(grid[0, :])
        ax_score.set_xlim(0, 1)
        ax_score.set_ylim(0, 1)
        ax_score.axis("off")
        ax_score.set_facecolor(COLORS.bg)

        color = readiness_color(readiness)
        ax_score.text(0.5, 0.7, "Morning Readiness", fontsize=FONTS.subtitle,
                      color=COLORS.text_secondary, ha="center", va="center",
                      fontfamily="sans-serif")
        ax_score.text(0.5, 0.35, str(readiness), fontsize=FONTS.hero,
                      color=color, ha="center", va="center", fontweight="bold",
                      fontfamily="sans-serif")
        # 状态描述
        if readiness >= 80:
            status = "Ready for Quality Training"
        elif readiness >= 60:
            status = "Moderate — Proceed with Caution"
        else:
            status = "Rest Recommended"
        ax_score.text(0.5, 0.05, status, fontsize=FONTS.caption,
                      color=COLORS.text_light, ha="center", va="center",
                      fontfamily="sans-serif")

        # ── Row 1: Recovery + Sleep ──
        ax_recovery = fig.add_subplot(grid[1, 0])
        ax_sleep = fig.add_subplot(grid[1, 1])

        for ax, title, items in [
            (ax_recovery, "Recovery", [
                ("HRV", f"{hrv} ms"),
                ("Resting HR", f"{rhr} bpm"),
                ("Fatigue", fatigue),
            ]),
            (ax_sleep, "Sleep", [
                ("Score", f"{sleep_score}/100"),
                ("Duration", sleep_duration),
            ]),
        ]:
            self._draw_metric_block(ax, title, items)

        # ── Row 2: Recovery Time ──
        ax_rec_time = fig.add_subplot(grid[2, :])
        ax_rec_time.set_xlim(0, 1)
        ax_rec_time.set_ylim(0, 1)
        ax_rec_time.axis("off")
        ax_rec_time.set_facecolor(COLORS.bg)
        ax_rec_time.text(0.5, 0.5, f"Recovery Time:  {recovery_time}",
                         fontsize=FONTS.body, color=COLORS.text_secondary,
                         ha="center", va="center", fontfamily="sans-serif")

        # ── Row 3: AI Insight ──
        ax_ai = fig.add_subplot(grid[3, :])
        self._draw_ai_insight(ax_ai, ai_insight)

        # ── Row 4: Today's Suggestion ──
        ax_suggest = fig.add_subplot(grid[4, :])
        ax_suggest.set_xlim(0, 1)
        ax_suggest.set_ylim(0, 1)
        ax_suggest.axis("off")
        ax_suggest.set_facecolor(COLORS.bg)

        ax_suggest.text(0.5, 0.85, "Today's Suggestion", fontsize=FONTS.body,
                        color=COLORS.text_secondary, ha="center", va="center",
                        fontfamily="sans-serif", fontweight="bold")
        lines = [
            f"Training:  {suggestion['type']}",
            f"Duration:  {suggestion['duration']}",
            f"Intensity:  {suggestion['intensity']}",
        ]
        ax_suggest.text(0.5, 0.35, "\n".join(lines), fontsize=FONTS.caption,
                        color=COLORS.text_primary, ha="center", va="center",
                        fontfamily="sans-serif", linespacing=1.6)

        return fig

    def _draw_metric_block(self, ax, title, items):
        """绘制指标块（标题 + 多行指标）"""
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_facecolor(COLORS.bg)

        # 标题
        ax.text(0.5, 0.92, title, fontsize=FONTS.body,
                color=COLORS.text_secondary, ha="center", va="center",
                fontfamily="sans-serif", fontweight="bold")

        # 指标
        y = 0.65
        for label, value in items:
            ax.text(0.15, y, label, fontsize=FONTS.caption,
                    color=COLORS.text_light, ha="left", va="center",
                    fontfamily="sans-serif")
            ax.text(0.85, y, value, fontsize=FONTS.caption,
                    color=COLORS.text_primary, ha="right", va="center",
                    fontfamily="sans-serif", fontweight="bold")
            y -= 0.22

    def _draw_ai_insight(self, ax, text):
        """绘制 AI Insight 引用块"""
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_facecolor(COLORS.bg)

        # 左侧竖线
        ax.plot([0.08, 0.08], [0.15, 0.85], color=COLORS.accent,
                linewidth=AI_INSIGHT_LEFT_LINE, solid_capstyle="round")

        # 背景框
        rect = FancyBboxPatch(
            (0.1, 0.15), 0.88, 0.7,
            boxstyle=f"round,pad=0.02,rounding_size={CARD_RADIUS}",
            facecolor=COLORS.accent, alpha=AI_INSIGHT_BG_ALPHA,
            edgecolor="none",
        )
        ax.add_patch(rect)

        # 标签
        ax.text(0.15, 0.82, "AI Insight", fontsize=FONTS.caption,
                color=COLORS.accent, ha="left", va="center",
                fontfamily="sans-serif", fontweight="bold")

        # 文本
        ax.text(0.5, 0.45, text, fontsize=FONTS.body,
                color=COLORS.text_primary, ha="center", va="center",
                fontfamily="sans-serif", wrap=True,
                linespacing=1.5)


if __name__ == "__main__":
    report = MorningReport(mock=True)
    path = report.generate()
    print(f"Morning Report generated: {path}")
