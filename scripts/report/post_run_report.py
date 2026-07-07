"""
跑后即时报表

模块结构（对标需求文档）：
1. 本次运动头部概览
2. 配速拆分（核心图表）
3. 心率区间分布
4. 跑步专项指标
5. 海拔剖面
6. 身体状态对比
7. 历史对比
8. 目标进度

用法:
    from post_run_report import PostRunReport
    pr = PostRunReport(mock=True)
    pr.generate()
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
import numpy as np


class PostRunReport:
    """跑后即时报表生成器"""

    def __init__(self, mock: bool = True, output_dir: str = None):
        self.aggregator = DataAggregator(mock=mock)
        self.output_dir = Path(output_dir or Path(__file__).resolve().parent / "output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.renderer = ChartRenderer(output_dir=str(self.output_dir))

    def generate(self, activity_id: int = None) -> str:
        """生成跑后报表"""
        data = self.aggregator.get_post_run_data(activity_id)
        chart_paths = self._render_charts(data)
        report_path = self._compose_report(data, chart_paths)
        return report_path

    def _render_charts(self, data: dict) -> dict:
        paths = {}
        activity = data["activity"]
        splits = data["splits"]
        hr_zones = data["hr_zones"]

        # 配速拆分图
        if splits:
            avg_speed = activity.get("averageSpeed", 0)
            avg_pace = 1000 / (avg_speed * 60) if avg_speed > 0 else 0
            paths["pace"] = self.renderer.render_pace_chart(
                splits, avg_pace, "配速拆分"
            )

        # 心率区间环形图
        if hr_zones:
            zone_dict = {z["zoneNumber"]: z["secsInZone"] for z in hr_zones}
            paths["hr_zones"] = self.renderer.render_hr_zone_donut(
                zone_dict, "心率区间分布"
            )

        return paths

    def _compose_report(self, data: dict, chart_paths: dict) -> str:
        fig = plt.figure(figsize=(16, 22))
        fig.patch.set_facecolor(Colors.BG)

        gs = GridSpec(4, 2, figure=fig, hspace=0.35, wspace=0.3,
                     left=0.06, right=0.94, top=0.95, bottom=0.03)

        # Row 0: 标题 + 概览
        ax_header = fig.add_subplot(gs[0, :])
        ax_header.set_facecolor(Colors.BG)
        ax_header.axis('off')
        self._draw_header(ax_header, data["activity"])

        # Row 1: 配速图 | 心率区间
        if "pace" in chart_paths:
            ax_pace = fig.add_subplot(gs[1, 0])
            self._embed_chart(ax_pace, chart_paths["pace"])

        if "hr_zones" in chart_paths:
            ax_hr = fig.add_subplot(gs[1, 1])
            self._embed_chart(ax_hr, chart_paths["hr_zones"])

        # Row 2: 跑步指标 | 身体状态
        ax_metrics = fig.add_subplot(gs[2, 0])
        ax_metrics.set_facecolor(Colors.BG)
        ax_metrics.axis('off')
        self._draw_running_metrics(ax_metrics, data["activity"])

        ax_health = fig.add_subplot(gs[2, 1])
        ax_health.set_facecolor(Colors.BG)
        ax_health.axis('off')
        self._draw_health_compare(ax_health, data["health_before"])

        # Row 3: 历史对比 | 目标进度
        ax_history = fig.add_subplot(gs[3, 0])
        ax_history.set_facecolor(Colors.BG)
        ax_history.axis('off')
        self._draw_history_compare(ax_history, data["history_compare"])

        ax_progress = fig.add_subplot(gs[3, 1])
        ax_progress.set_facecolor(Colors.BG)
        ax_progress.axis('off')
        self._draw_progress(ax_progress, data["progress"])

        report_path = str(self.output_dir / "post_run_report.png")
        fig.savefig(report_path, dpi=150, bbox_inches='tight',
                   facecolor=Colors.BG, edgecolor='none')
        plt.close(fig)
        return report_path

    def _draw_header(self, ax, activity: dict):
        name = activity.get("activityName", "跑步")
        dist = activity.get("distance", 0) / 1000
        dur = activity.get("duration", 0)
        dur_h = int(dur // 3600)
        dur_m = int((dur % 3600) // 60)
        dur_s = int(dur % 60)
        avg_speed = activity.get("averageSpeed", 0)
        avg_pace = 1000 / (avg_speed * 60) if avg_speed > 0 else 0
        pace_m = int(avg_pace)
        pace_s = int((avg_pace - pace_m) * 60)
        avg_hr = activity.get("averageHR", 0)
        cal = activity.get("calories", 0)
        elev = activity.get("elevationGain", 0)

        ax.text(0.5, 0.75, name, ha='center', va='center', fontsize=28,
               fontweight='bold', color=Colors.TEXT_PRIMARY, transform=ax.transAxes)
        ax.text(0.5, 0.45, 'Post-Run Report', ha='center', va='center', fontsize=14,
               color=Colors.TEXT_SECONDARY, transform=ax.transAxes)

        metrics = [
            (f'{dist:.1f}', '距离 (km)'),
            (f'{dur_h}:{dur_m:02d}:{dur_s:02d}', '时长'),
            (f'{pace_m}:{pace_s:02d}', '配速 (min/km)'),
            (f'{int(avg_hr)}', '心率 (bpm)'),
            (f'{cal}', '热量 (kcal)'),
            (f'{elev}m', '爬升'),
        ]
        card_w = 0.14
        start_x = 0.05
        for i, (val, label) in enumerate(metrics):
            x = start_x + i * (card_w + 0.02)
            rect = mpatches.FancyBboxPatch(
                (x, 0.05), card_w, 0.28,
                boxstyle="round,pad=0.02",
                facecolor=Colors.CARD_BG, edgecolor=Colors.GRID,
                linewidth=1, transform=ax.transAxes)
            ax.add_patch(rect)
            ax.text(x + card_w / 2, 0.22, val, ha='center', va='center',
                   fontsize=16, fontweight='bold', color=Colors.TEXT_PRIMARY,
                   transform=ax.transAxes)
            ax.text(x + card_w / 2, 0.10, label, ha='center', va='center',
                   fontsize=9, color=Colors.TEXT_SECONDARY, transform=ax.transAxes)

    def _draw_running_metrics(self, ax, activity: dict):
        ax.text(0.05, 0.95, '跑步专项指标', fontsize=14, fontweight='bold',
               color=Colors.TEXT_PRIMARY, transform=ax.transAxes)

        metrics = [
            ('步频', f'{activity.get("averageRunningCadenceInStepsPerMinute", 0)} spm'),
            ('步幅', f'{activity.get("avgStrideLength", 0)} cm'),
            ('触地时间', f'{activity.get("avgGroundContactTime", 0)} ms'),
            ('垂直振幅', f'{activity.get("avgVerticalOscillation", 0)} cm'),
            ('垂直比', f'{activity.get("avgVerticalRatio", 0)}%'),
            ('左右平衡', f'{activity.get("avgGctBalance", 50)}%'),
            ('有氧效果', f'{activity.get("aerobicTrainingEffect", 0)}'),
            ('无氧效果', f'{activity.get("anaerobicTrainingEffect", 0)}'),
        ]

        y = 0.85
        for label, val in metrics:
            ax.text(0.05, y, label, fontsize=10, color=Colors.TEXT_SECONDARY,
                   transform=ax.transAxes)
            ax.text(0.95, y, val, fontsize=10, fontweight='bold',
                   color=Colors.TEXT_PRIMARY, ha='right', transform=ax.transAxes)
            y -= 0.10

    def _draw_health_compare(self, ax, health: dict):
        ax.text(0.05, 0.95, '身体状态', fontsize=14, fontweight='bold',
               color=Colors.TEXT_PRIMARY, transform=ax.transAxes)

        hrv = health.get("hrv", {}).get("hrvSummary", {})
        sleep = health.get("sleep", {}).get("dailySleepDTO", {})
        rhr_raw = health.get("resting_hr", {})
        try:
            rhr = rhr_raw.get("allMetrics", {}).get("metricsMap", {}).get("WELLNESS_RESTING_HEART_RATE", [{}])[0].get("value", 0)
        except (IndexError, AttributeError):
            rhr = 0

        items = [
            ('HRV', f'{hrv.get("lastNightAvg", "--")} ms ({hrv.get("status", "--")})'),
            ('静息心率', f'{int(rhr)} bpm' if rhr else '--'),
            ('睡眠评分', f'{sleep.get("sleepScores", {}).get("overall", {}).get("value", "--")}'),
            ('睡眠时长', f'{sleep.get("sleepTimeSeconds", 0) // 3600}h {(sleep.get("sleepTimeSeconds", 0) % 3600) // 60}m'),
        ]

        y = 0.85
        for label, val in items:
            ax.text(0.05, y, label, fontsize=10, color=Colors.TEXT_SECONDARY,
                   transform=ax.transAxes)
            ax.text(0.95, y, str(val), fontsize=10, fontweight='bold',
                   color=Colors.TEXT_PRIMARY, ha='right', transform=ax.transAxes)
            y -= 0.15

    def _draw_history_compare(self, ax, compare: dict):
        ax.text(0.05, 0.95, '历史对比', fontsize=14, fontweight='bold',
               color=Colors.TEXT_PRIMARY, transform=ax.transAxes)
        note = compare.get("note", "暂无历史对比数据")
        ax.text(0.05, 0.75, note, fontsize=10, color=Colors.TEXT_SECONDARY,
               transform=ax.transAxes)

    def _draw_progress(self, ax, progress: dict):
        ax.text(0.05, 0.95, '目标进度', fontsize=14, fontweight='bold',
               color=Colors.TEXT_PRIMARY, transform=ax.transAxes)

        wk = progress.get("weekly_km", 0)
        wt = progress.get("weekly_target_km", 50)
        mk = progress.get("monthly_km", 0)
        mt = progress.get("monthly_target_km", 200)

        y = 0.80
        for current, target, label in [(wk, wt, '本周'), (mk, mt, '本月')]:
            pct = current / target * 100 if target > 0 else 0
            ax.text(0.05, y, f'{label}: {current}/{target}km ({pct:.0f}%)',
                   fontsize=10, color=Colors.TEXT_SECONDARY, transform=ax.transAxes)
            bar_x, bar_y, bar_w, bar_h = 0.05, y - 0.05, 0.85, 0.025
            rect_bg = mpatches.FancyBboxPatch(
                (bar_x, bar_y), bar_w, bar_h,
                boxstyle="round,pad=0.005",
                facecolor=Colors.GRID, edgecolor='none',
                transform=ax.transAxes)
            ax.add_patch(rect_bg)
            fill_w = bar_w * min(pct / 100, 1.0)
            rect_fill = mpatches.FancyBboxPatch(
                (bar_x, bar_y), fill_w, bar_h,
                boxstyle="round,pad=0.005",
                facecolor=Colors.ACCENT, edgecolor='none',
                transform=ax.transAxes)
            ax.add_patch(rect_fill)
            y -= 0.20

    def _embed_chart(self, ax, img_path: str):
        ax.axis('off')
        try:
            img = plt.imread(img_path)
            ax.imshow(img, aspect='auto')
        except Exception as e:
            ax.text(0.5, 0.5, f'图表加载失败: {e}', ha='center', va='center',
                   fontsize=12, color=Colors.TEXT_SECONDARY, transform=ax.transAxes)


if __name__ == "__main__":
    pr = PostRunReport(mock=True)
    path = pr.generate()
    print(f"Post-run report: {path}")
