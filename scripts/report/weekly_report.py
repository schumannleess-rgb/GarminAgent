"""
周报生成器

将数据聚合 + 图表渲染组装成完整的周报图片。

模块结构（对标需求文档）：
1. 周数据概览（5 宫格）
2. 每日跑量 + 爬升图
3. 训练类型分布
4. 心率区间汇总
5. 健康数据周趋势
6. 本周高光
7. 对比上周
8. 目标进度 + 建议

用法:
    from weekly_report import WeeklyReport
    wr = WeeklyReport(mock=True)
    wr.generate()  # 生成到 output/
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


class WeeklyReport:
    """周报生成器"""

    def __init__(self, mock: bool = True, output_dir: str = None):
        self.aggregator = DataAggregator(mock=mock)
        self.output_dir = Path(output_dir or Path(__file__).resolve().parent / "output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.renderer = ChartRenderer(output_dir=str(self.output_dir))

    def generate(self, weeks_ago: int = 0) -> str:
        """生成完整周报图片

        Returns:
            生成的图片路径
        """
        # 1. 获取数据
        data = self.aggregator.get_weekly_data(weeks_ago)

        # 2. 生成各子图表
        chart_paths = self._render_charts(data)

        # 3. 组装完整周报
        report_path = self._compose_report(data, chart_paths)

        return report_path

    def _render_charts(self, data: dict) -> dict:
        """生成各子图表"""
        paths = {}

        # 每日跑量图
        if data["daily_breakdown"]:
            paths["weekly_distance"] = self.renderer.render_weekly_distance_chart(
                data["daily_breakdown"],
                f"{data['week_start']} ~ {data['week_end']} 跑量"
            )

        # 训练类型分布
        if data["training_types"]:
            paths["training_types"] = self.renderer.render_training_type_donut(
                data["training_types"], "训练类型分布"
            )

        # 心率区间
        if data["hr_zones_week"]["zones"]:
            paths["hr_zones"] = self.renderer.render_hr_zone_donut(
                data["hr_zones_week"]["zones"], "心率区间分布"
            )

        # 健康趋势
        if data["health_trend"]:
            paths["health_trend"] = self.renderer.render_health_trend(
                data["health_trend"], "7天健康趋势"
            )

        return paths

    def _compose_report(self, data: dict, chart_paths: dict) -> str:
        """组装完整周报大图"""
        # 布局：3 行
        # Row 1: 标题 + 5 宫格概览
        # Row 2: 每日跑量图 | 训练类型 + 心率区间
        # Row 3: 健康趋势 | 高光 + 对比 + 进度

        fig = plt.figure(figsize=(16, 20))
        fig.patch.set_facecolor(Colors.BG)

        gs = GridSpec(4, 2, figure=fig, hspace=0.35, wspace=0.3,
                     left=0.06, right=0.94, top=0.95, bottom=0.03)

        # ===== Row 0: 标题 =====
        ax_title = fig.add_subplot(gs[0, :])
        ax_title.set_facecolor(Colors.BG)
        ax_title.axis('off')
        self._draw_title(ax_title, data)

        # ===== Row 1: 5 宫格概览 =====
        ax_summary = fig.add_subplot(gs[1, :])
        ax_summary.set_facecolor(Colors.BG)
        ax_summary.axis('off')
        self._draw_summary_cards(ax_summary, data["summary"])

        # ===== Row 2: 图表 =====
        # 左：每日跑量
        if "weekly_distance" in chart_paths:
            ax_daily = fig.add_subplot(gs[2, 0])
            self._embed_chart(ax_daily, chart_paths["weekly_distance"])

        # 右：训练类型 + 心率区间叠加
        ax_right = fig.add_subplot(gs[2, 1])
        ax_right.axis('off')
        if "training_types" in chart_paths:
            self._embed_chart_small(ax_right, chart_paths["training_types"], 0, 0.5)
        if "hr_zones" in chart_paths:
            self._embed_chart_small(ax_right, chart_paths["hr_zones"], 0.5, 1.0)

        # ===== Row 3: 健康 + 高光 + 进度 =====
        # 左：健康趋势
        if "health_trend" in chart_paths:
            ax_health = fig.add_subplot(gs[3, 0])
            self._embed_chart(ax_health, chart_paths["health_trend"])

        # 右：文字信息
        ax_info = fig.add_subplot(gs[3, 1])
        ax_info.set_facecolor(Colors.BG)
        ax_info.axis('off')
        self._draw_info_panel(ax_info, data)

        # 保存
        report_path = str(self.output_dir / "weekly_report.png")
        fig.savefig(report_path, dpi=150, bbox_inches='tight',
                   facecolor=Colors.BG, edgecolor='none')
        plt.close(fig)

        return report_path

    def _draw_title(self, ax, data: dict):
        """绘制标题区"""
        ws = data["week_start"]
        we = data["week_end"]
        ax.text(0.5, 0.7, f'Weekly Training Report',
               ha='center', va='center', fontsize=28,
               fontweight='bold', color=Colors.TEXT_PRIMARY,
               transform=ax.transAxes)
        ax.text(0.5, 0.3, f'{ws.isoformat()} ~ {we.isoformat()}',
               ha='center', va='center', fontsize=14,
               color=Colors.TEXT_SECONDARY,
               transform=ax.transAxes)

    def _draw_summary_cards(self, ax, summary: dict):
        """绘制 5 宫格概览卡片"""
        metrics = [
            ("总跑量", summary["total_distance_fmt"], ""),
            ("总时长", summary["total_duration_fmt"], ""),
            ("累计爬升", f"{summary['total_elevation']}m", ""),
            ("消耗热量", summary["total_calories_fmt"], ""),
            ("训练天数", f"{summary['training_days']}天", ""),
        ]

        card_width = 0.17
        card_height = 0.8
        start_x = 0.05
        y = 0.1

        for i, (label, value, unit) in enumerate(metrics):
            x = start_x + i * (card_width + 0.02)

            # 卡片背景
            rect = mpatches.FancyBboxPatch(
                (x, y), card_width, card_height,
                boxstyle="round,pad=0.02",
                facecolor=Colors.CARD_BG, edgecolor=Colors.GRID,
                linewidth=1, transform=ax.transAxes
            )
            ax.add_patch(rect)

            # 数值
            ax.text(x + card_width / 2, y + card_height * 0.6,
                   value, ha='center', va='center', fontsize=18,
                   fontweight='bold', color=Colors.TEXT_PRIMARY,
                   transform=ax.transAxes)

            # 标签
            ax.text(x + card_width / 2, y + card_height * 0.2,
                   label, ha='center', va='center', fontsize=10,
                   color=Colors.TEXT_SECONDARY,
                   transform=ax.transAxes)

    def _embed_chart(self, ax, img_path: str):
        """嵌入子图表到指定 axes"""
        ax.axis('off')
        try:
            img = plt.imread(img_path)
            ax.imshow(img, aspect='auto')
        except Exception as e:
            ax.text(0.5, 0.5, f'图表加载失败: {e}', ha='center', va='center',
                   fontsize=12, color=Colors.TEXT_SECONDARY,
                   transform=ax.transAxes)

    def _embed_chart_small(self, ax, img_path: str, y_start: float, y_end: float):
        """在 axes 内嵌入子图表（指定垂直范围）"""
        try:
            img = plt.imread(img_path)
            ax.imshow(img, aspect='auto', extent=[0, 1, y_start, y_end])
        except Exception:
            pass

    def _draw_info_panel(self, ax, data: dict):
        """绘制信息面板（高光 + 对比 + 进度）"""
        y = 0.95
        line_height = 0.06

        # === 本周高光 ===
        ax.text(0.05, y, '本周高光', fontsize=14, fontweight='bold',
               color=Colors.TEXT_PRIMARY, transform=ax.transAxes)
        y -= line_height

        highlights = data.get("highlights", {})
        if highlights.get("best_pace"):
            bp = highlights["best_pace"]
            ax.text(0.05, y, f'最佳配速: {bp["pace"]} ({bp["name"]})',
                   fontsize=10, color=Colors.TEXT_SECONDARY, transform=ax.transAxes)
            y -= line_height * 0.8

        if highlights.get("longest"):
            lo = highlights["longest"]
            ax.text(0.05, y, f'最长距离: {lo["distance"]} ({lo["name"]})',
                   fontsize=10, color=Colors.TEXT_SECONDARY, transform=ax.transAxes)
            y -= line_height * 0.8

        # === 对比上周 ===
        y -= line_height * 0.5
        ax.text(0.05, y, '对比上周', fontsize=14, fontweight='bold',
               color=Colors.TEXT_PRIMARY, transform=ax.transAxes)
        y -= line_height

        vs = data.get("vs_last_week", {})
        ax.text(0.05, y, f'跑量: {vs.get("distance_diff_fmt", "N/A")}',
               fontsize=10, color=Colors.TEXT_SECONDARY, transform=ax.transAxes)
        y -= line_height * 0.8

        hr_diff = vs.get("avg_hr_diff", 0)
        hr_arrow = "↑" if hr_diff > 0 else "↓" if hr_diff < 0 else "→"
        ax.text(0.05, y, f'平均心率: {hr_arrow} {abs(hr_diff)} bpm',
               fontsize=10, color=Colors.TEXT_SECONDARY, transform=ax.transAxes)
        y -= line_height

        # === 目标进度 ===
        y -= line_height * 0.5
        ax.text(0.05, y, '目标进度', fontsize=14, fontweight='bold',
               color=Colors.TEXT_PRIMARY, transform=ax.transAxes)
        y -= line_height

        progress = data.get("progress", {})
        wk = progress.get("weekly_km", 0)
        wt = progress.get("weekly_target_km", 50)
        pct = wk / wt * 100 if wt > 0 else 0

        # 进度条背景
        bar_x, bar_y, bar_w, bar_h = 0.05, y - 0.01, 0.85, 0.025
        rect_bg = mpatches.FancyBboxPatch(
            (bar_x, bar_y), bar_w, bar_h,
            boxstyle="round,pad=0.005",
            facecolor=Colors.GRID, edgecolor='none',
            transform=ax.transAxes
        )
        ax.add_patch(rect_bg)

        # 进度条填充
        fill_w = bar_w * min(pct / 100, 1.0)
        rect_fill = mpatches.FancyBboxPatch(
            (bar_x, bar_y), fill_w, bar_h,
            boxstyle="round,pad=0.005",
            facecolor=Colors.ACCENT, edgecolor='none',
            transform=ax.transAxes
        )
        ax.add_patch(rect_fill)

        ax.text(bar_x + bar_w + 0.02, bar_y + bar_h / 2,
               f'{wk}/{wt}km ({pct:.0f}%)',
               ha='left', va='center', fontsize=10,
               color=Colors.TEXT_PRIMARY, transform=ax.transAxes)

        y -= line_height * 1.5

        # 训练建议
        advice = self._generate_advice(data)
        ax.text(0.05, y, advice, fontsize=10, color=Colors.ACCENT_DARK,
               style='italic', transform=ax.transAxes,
               wrap=True, verticalalignment='top')

    def _generate_advice(self, data: dict) -> str:
        """根据数据生成建议"""
        summary = data.get("summary", {})
        health = data.get("health_trend", [])
        vs = data.get("vs_last_week", {})

        total_km = summary.get("total_distance", 0) / 1000
        days = summary.get("training_days", 0)
        hr_diff = vs.get("avg_hr_diff", 0)

        advice_parts = []

        if total_km >= 40:
            advice_parts.append("本周跑量充足")
        elif total_km >= 25:
            advice_parts.append("本周跑量适中")
        else:
            advice_parts.append("本周跑量偏低，下周可适当增加")

        if days >= 4:
            advice_parts.append("训练频率良好")
        elif days >= 3:
            advice_parts.append("可考虑增加一次轻松跑")

        if hr_diff < -3:
            advice_parts.append("心率下降，有氧能力在提升")

        return "。".join(advice_parts) + "。"


if __name__ == "__main__":
    wr = WeeklyReport(mock=True)
    path = wr.generate()
    print(f"Weekly report generated: {path}")
