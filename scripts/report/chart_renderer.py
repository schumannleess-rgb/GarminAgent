"""
图表渲染器

使用 matplotlib 生成训练报表所需的各类图表。
配色方案：米色系（参考图风格），温暖、专业、易读。

用法:
    from chart_renderer import ChartRenderer
    renderer = ChartRenderer(output_dir="output")
    renderer.render_pace_chart(splits, avg_pace, "output/pace.png")
"""

import os
from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use('Agg')  # 非交互模式
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np


# ==========================================
# 配色方案（米色系）
# ==========================================

class Colors:
    """米色系配色方案"""
    BG = '#FAF7F2'           # 主背景
    CARD_BG = '#FFFFFF'      # 卡片背景
    TEXT_PRIMARY = '#2D2D2D'  # 主文字
    TEXT_SECONDARY = '#888888'  # 次要文字
    TEXT_LIGHT = '#BBBBBB'    # 浅色文字
    ACCENT = '#E8A87C'       # 主色调（暖橙）
    ACCENT_DARK = '#D4845A'  # 深色强调
    CHART_LINE = '#E8A87C'   # 折线色
    CHART_BAR = '#F5D5B8'    # 柱状图色
    CHART_BAR_HIGHLIGHT = '#E8A87C'  # 高亮柱
    GRID = '#EDEDED'         # 网格线

    # 心率区间色
    ZONE_COLORS = ['#7EC8E3', '#8BC34A', '#FFC107', '#FF9800', '#F44336']

    # 训练类型色
    TYPE_COLORS = {
        '轻松跑': '#8BC34A',
        '恢复跑': '#7EC8E3',
        '高强度': '#FF5722',
        '长距离': '#FFC107',
        '节奏跑': '#FF9800',
        '间歇': '#F44336',
    }


def setup_chinese_font():
    """设置中文字体支持"""
    # 尝试常见的中文字体
    font_candidates = [
        'Microsoft YaHei', 'SimHei', 'PingFang SC',
        'Noto Sans CJK SC', 'WenQuanYi Micro Hei',
    ]
    for font_name in font_candidates:
        try:
            fm.findfont(font_name, fallback_to_default=False)
            plt.rcParams['font.sans-serif'] = [font_name]
            plt.rcParams['axes.unicode_minus'] = False
            return
        except Exception:
            continue
    # fallback
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
    plt.rcParams['axes.unicode_minus'] = False


setup_chinese_font()


class ChartRenderer:
    """图表渲染器"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_pace_chart(
        self, splits: list, avg_pace: float,
        title: str = "配速拆分", save_path: str = None
    ) -> str:
        """渲染每公里配速柱状图 + 心率折线叠加

        Args:
            splits: 圈数据列表，每项含 averageSpeed, averageHR
            avg_pace: 平均配速（秒/公里）
            title: 图表标题
            save_path: 保存路径

        Returns:
            保存的图片路径
        """
        fig, ax1 = plt.subplots(figsize=(10, 4.5))
        fig.patch.set_facecolor(Colors.BG)
        ax1.set_facecolor(Colors.BG)

        # 数据准备
        km_labels = [f"{i+1}km" for i in range(len(splits))]
        paces = [1000 / (s["averageSpeed"] * 60) if s.get("averageSpeed") else 0 for s in splits]
        hrs = [s.get("averageHR", 0) for s in splits]

        # 配速柱状图
        pace_minutes = [int(p) for p in paces]
        pace_seconds = [int((p - int(p)) * 60) for p in paces]
        bar_colors = [Colors.CHART_BAR_HIGHLIGHT if p == max(paces) or p == min(paces)
                      else Colors.CHART_BAR for p in paces]

        bars = ax1.bar(km_labels, paces, color=bar_colors, width=0.6, zorder=2)
        ax1.set_ylabel('配速 (min/km)', color=Colors.TEXT_PRIMARY, fontsize=10)
        ax1.tick_params(axis='y', labelcolor=Colors.TEXT_PRIMARY)

        # 平均配速参考线
        if avg_pace > 0:
            ax1.axhline(y=avg_pace, color=Colors.ACCENT_DARK, linestyle='--',
                       linewidth=1.5, alpha=0.7, label=f'平均 {int(avg_pace)}:{int((avg_pace%1)*60):02d}')

        # Y轴格式化（配速）
        ax1.invert_yaxis()  # 配速越快越上面
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, _: f"{int(x)}:{int((x%1)*60):02d}"
        ))

        # 心率折线（右轴）
        ax2 = ax1.twinx()
        ax2.plot(km_labels, hrs, color='#FF6B6B', marker='o', linewidth=2,
                markersize=5, zorder=3, label='心率')
        ax2.set_ylabel('心率 (bpm)', color='#FF6B6B', fontsize=10)
        ax2.tick_params(axis='y', labelcolor='#FF6B6B')

        # 网格
        ax1.grid(axis='y', color=Colors.GRID, linewidth=0.5, alpha=0.5)
        ax1.set_axisbelow(True)

        # 标题和图例
        ax1.set_title(title, fontsize=14, color=Colors.TEXT_PRIMARY, pad=15)
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right',
                  framealpha=0.8, fontsize=9)

        plt.tight_layout()
        save_path = save_path or str(self.output_dir / "pace_chart.png")
        fig.savefig(save_path, dpi=150, bbox_inches='tight',
                   facecolor=Colors.BG, edgecolor='none')
        plt.close(fig)
        return save_path

    def render_hr_zone_donut(
        self, zones: dict, title: str = "心率区间分布",
        save_path: str = None
    ) -> str:
        """渲染心率区间环形图

        Args:
            zones: {1: secs, 2: secs, 3: secs, 4: secs, 5: secs}
            title: 图表标题
            save_path: 保存路径
        """
        fig, ax = plt.subplots(figsize=(5, 5))
        fig.patch.set_facecolor(Colors.BG)

        zone_labels = ['Z1 恢复', 'Z2 有氧', 'Z3 耐力', 'Z4 阈值', 'Z5 无氧']
        values = [zones.get(i, 0) for i in range(1, 6)]
        total = sum(values)

        if total == 0:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center',
                   fontsize=16, color=Colors.TEXT_SECONDARY)
            ax.set_title(title, fontsize=14, color=Colors.TEXT_PRIMARY)
            plt.tight_layout()
            save_path = save_path or str(self.output_dir / "hr_zone_donut.png")
            fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=Colors.BG)
            plt.close(fig)
            return save_path

        # 只显示有时长的区间
        filtered = [(l, v, c) for l, v, c in zip(zone_labels, values, Colors.ZONE_COLORS) if v > 0]
        if not filtered:
            filtered = [(zone_labels[0], 1, Colors.ZONE_COLORS[0])]

        labels, vals, colors = zip(*filtered)
        percentages = [v / total * 100 for v in vals]

        # 环形图
        wedges, texts, autotexts = ax.pie(
            vals, labels=None, colors=colors, autopct='',
            startangle=90, pctdistance=0.75,
            wedgeprops=dict(width=0.4, edgecolor=Colors.BG, linewidth=2)
        )

        # 中心文字
        ax.text(0, 0, f'{total//60}分钟', ha='center', va='center',
               fontsize=18, fontweight='bold', color=Colors.TEXT_PRIMARY)

        # 图例
        legend_labels = [f'{l} {p:.0f}%' for l, p in zip(labels, percentages)]
        ax.legend(wedges, legend_labels, loc='center left',
                bbox_to_anchor=(-0.15, -0.15), fontsize=9, framealpha=0)

        ax.set_title(title, fontsize=14, color=Colors.TEXT_PRIMARY, pad=15)

        plt.tight_layout()
        save_path = save_path or str(self.output_dir / "hr_zone_donut.png")
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=Colors.BG)
        plt.close(fig)
        return save_path

    def render_weekly_distance_chart(
        self, daily_data: list, title: str = "本周跑量",
        save_path: str = None
    ) -> str:
        """渲染每日跑量柱状图 + 爬升折线

        Args:
            daily_data: 每日明细列表，含 date, distance, elevation
            title: 图表标题
            save_path: 保存路径
        """
        fig, ax1 = plt.subplots(figsize=(10, 4.5))
        fig.patch.set_facecolor(Colors.BG)
        ax1.set_facecolor(Colors.BG)

        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        distances_km = [d["distance"] / 1000 for d in daily_data]
        elevations = [d["elevation"] for d in daily_data]

        # 根据天数选择标签：7天用星期，否则用日期
        n = len(daily_data)
        if n <= 7:
            labels = weekday_names[:n]
            tick_fontsize = 9
        else:
            labels = [d.get("date", "")
                     .strftime("%d") if hasattr(d.get("date", ""), "strftime")
                     else str(d.get("date", ""))[-2:] for d in daily_data]
            tick_fontsize = 7

        # 柱状图（跑量）
        x = range(n)
        bar_colors = []
        for d in daily_data:
            if d["distance"] == 0:
                bar_colors.append(Colors.TEXT_LIGHT)
            else:
                bar_colors.append(Colors.CHART_BAR_HIGHLIGHT if d["distance"] == max(
                    dd["distance"] for dd in daily_data) and d["distance"] > 0
                    else Colors.CHART_BAR)

        bars = ax1.bar(x, distances_km, color=bar_colors, width=0.5, zorder=2)
        ax1.set_ylabel('跑量 (km)', color=Colors.TEXT_PRIMARY, fontsize=10)
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, fontsize=tick_fontsize, rotation=45 if n > 14 else 0)

        # 柱状图上标注距离
        for bar, dist in zip(bars, distances_km):
            if dist > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                        f'{dist:.1f}', ha='center', va='bottom',
                        fontsize=8, color=Colors.TEXT_PRIMARY)

        # 爬升折线（右轴）
        if any(e > 0 for e in elevations):
            ax2 = ax1.twinx()
            ax2.plot(x, elevations, color='#8BC34A', marker='s', linewidth=2,
                    markersize=6, zorder=3, label='爬升')
            ax2.set_ylabel('爬升 (m)', color='#8BC34A', fontsize=10)
            ax2.tick_params(axis='y', labelcolor='#8BC34A')

        # 网格
        ax1.grid(axis='y', color=Colors.GRID, linewidth=0.5, alpha=0.5)
        ax1.set_axisbelow(True)

        ax1.set_title(title, fontsize=14, color=Colors.TEXT_PRIMARY, pad=15)
        plt.tight_layout()
        save_path = save_path or str(self.output_dir / "weekly_distance.png")
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=Colors.BG)
        plt.close(fig)
        return save_path

    def render_health_trend(
        self, health_data: list, title: str = "健康趋势",
        save_path: str = None
    ) -> str:
        """渲染 7 天健康趋势图（HRV + 静息心率 + 睡眠评分）

        Args:
            health_data: 7 天健康数据列表
            title: 图表标题
            save_path: 保存路径
        """
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
        fig.patch.set_facecolor(Colors.BG)
        for ax in (ax1, ax2, ax3):
            ax.set_facecolor(Colors.BG)

        days = len(health_data)
        x = range(days)
        day_labels = [f'Day {i+1}' for i in range(days)]

        # HRV 趋势
        hrv_vals = [h.get("hrv", {}).get("hrvSummary", {}).get("lastNightAvg", 0) for h in health_data]
        ax1.plot(x, hrv_vals, color='#E8A87C', marker='o', linewidth=2, markersize=6)
        ax1.fill_between(x, hrv_vals, alpha=0.15, color='#E8A87C')
        ax1.set_ylabel('HRV (ms)', fontsize=10, color=Colors.TEXT_PRIMARY)
        ax1.set_title(title, fontsize=14, color=Colors.TEXT_PRIMARY, pad=10)
        ax1.grid(axis='y', color=Colors.GRID, linewidth=0.5, alpha=0.5)

        # 静息心率
        rhr_vals = []
        for h in health_data:
            try:
                val = h.get("resting_hr", {}).get("allMetrics", {}).get("metricsMap", {}).get("WELLNESS_RESTING_HEART_RATE", [{}])[0].get("value", 0)
            except (IndexError, AttributeError):
                val = 0
            rhr_vals.append(val)
        ax2.plot(x, rhr_vals, color='#FF6B6B', marker='s', linewidth=2, markersize=6)
        ax2.fill_between(x, rhr_vals, alpha=0.15, color='#FF6B6B')
        ax2.set_ylabel('静息心率 (bpm)', fontsize=10, color=Colors.TEXT_PRIMARY)
        ax2.grid(axis='y', color=Colors.GRID, linewidth=0.5, alpha=0.5)

        # 睡眠评分
        sleep_vals = [h.get("sleep", {}).get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value", 0)
                     for h in health_data]
        ax3.bar(x, sleep_vals, color=Colors.CHART_BAR, width=0.5, zorder=2)
        ax3.set_ylabel('睡眠评分', fontsize=10, color=Colors.TEXT_PRIMARY)
        ax3.set_xticks(x)
        ax3.set_xticklabels(day_labels, fontsize=9)
        ax3.grid(axis='y', color=Colors.GRID, linewidth=0.5, alpha=0.5)

        plt.tight_layout()
        save_path = save_path or str(self.output_dir / "health_trend.png")
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=Colors.BG)
        plt.close(fig)
        return save_path

    def render_training_type_donut(
        self, types: dict, title: str = "训练类型分布",
        save_path: str = None
    ) -> str:
        """渲染训练类型分布环形图"""
        fig, ax = plt.subplots(figsize=(5, 5))
        fig.patch.set_facecolor(Colors.BG)

        if not types:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center',
                   fontsize=16, color=Colors.TEXT_SECONDARY)
            save_path = save_path or str(self.output_dir / "training_type_donut.png")
            fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=Colors.BG)
            plt.close(fig)
            return save_path

        labels = list(types.keys())
        values = [types[t]["duration"] for t in labels]
        colors = [Colors.TYPE_COLORS.get(t, '#999999') for t in labels]
        total = sum(values)

        wedges, texts, autotexts = ax.pie(
            values, labels=None, colors=colors, autopct='',
            startangle=90, pctdistance=0.75,
            wedgeprops=dict(width=0.4, edgecolor=Colors.BG, linewidth=2)
        )

        ax.text(0, 0, f'{total//60}分钟', ha='center', va='center',
               fontsize=18, fontweight='bold', color=Colors.TEXT_PRIMARY)

        legend_labels = [f'{l} {v/total*100:.0f}%' for l, v in zip(labels, values)]
        ax.legend(wedges, legend_labels, loc='center left',
                bbox_to_anchor=(-0.15, -0.15), fontsize=9, framealpha=0)

        ax.set_title(title, fontsize=14, color=Colors.TEXT_PRIMARY, pad=15)
        plt.tight_layout()
        save_path = save_path or str(self.output_dir / "training_type_donut.png")
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=Colors.BG)
        plt.close(fig)
        return save_path

    def render_monthly_trend(
        self, weekly_trend: list, title: str = "周跑量趋势",
        save_path: str = None
    ) -> str:
        """渲染月度周趋势柱状图"""
        fig, ax1 = plt.subplots(figsize=(10, 4.5))
        fig.patch.set_facecolor(Colors.BG)
        ax1.set_facecolor(Colors.BG)

        weeks = [f"第{w['week_num']}周" for w in weekly_trend]
        distances = [w["distance"] / 1000 for w in weekly_trend]
        elevations = [w["elevation"] for w in weekly_trend]

        x = range(len(weekly_trend))
        bars = ax1.bar(x, distances, color=Colors.CHART_BAR, width=0.5, zorder=2)
        ax1.set_ylabel('跑量 (km)', color=Colors.TEXT_PRIMARY, fontsize=10)
        ax1.set_xticks(x)
        ax1.set_xticklabels(weeks, fontsize=10)

        for bar, dist in zip(bars, distances):
            if dist > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                        f'{dist:.1f}', ha='center', va='bottom',
                        fontsize=9, color=Colors.TEXT_PRIMARY)

        if any(e > 0 for e in elevations):
            ax2 = ax1.twinx()
            ax2.plot(x, elevations, color='#8BC34A', marker='s', linewidth=2,
                    markersize=6, zorder=3)
            ax2.set_ylabel('爬升 (m)', color='#8BC34A', fontsize=10)

        ax1.grid(axis='y', color=Colors.GRID, linewidth=0.5, alpha=0.5)
        ax1.set_axisbelow(True)
        ax1.set_title(title, fontsize=14, color=Colors.TEXT_PRIMARY, pad=15)

        plt.tight_layout()
        save_path = save_path or str(self.output_dir / "monthly_trend.png")
        fig.savefig(save_path, dpi=150, bbox_inches='tight', facecolor=Colors.BG)
        plt.close(fig)
        return save_path
