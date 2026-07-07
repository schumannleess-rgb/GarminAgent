"""
统一样式常量

所有报表共享的样式定义，避免硬编码分散。
修改这里会全局影响所有报表的视觉风格。
"""

from dataclasses import dataclass
from typing import Dict, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── 中文字体配置 ──
plt.rcParams["font.sans-serif"] = ["Noto Sans SC", "DengXian", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


@dataclass(frozen=True)
class ReportColors:
    """报表颜色方案"""
    bg: str
    card_bg: str
    text_primary: str
    text_secondary: str
    text_light: str
    accent: str
    accent_dark: str
    bar_normal: str
    bar_highlight: str
    hr_zone_1: str
    hr_zone_2: str
    hr_zone_3: str
    hr_zone_4: str
    hr_zone_5: str

    @property
    def hr_zones(self) -> list:
        return [
            self.hr_zone_1, self.hr_zone_2, self.hr_zone_3,
            self.hr_zone_4, self.hr_zone_5,
        ]


# ── 5 种报表的配色方案 ──

MORNING_COLORS = ReportColors(
    bg="#FFFFFF",
    card_bg="#F8F9FA",
    text_primary="#1A1A1A",
    text_secondary="#666666",
    text_light="#AAAAAA",
    accent="#E8A87C",
    accent_dark="#D4845A",
    bar_normal="#F5D5B8",
    bar_highlight="#E8A87C",
    hr_zone_1="#4FC3F7",
    hr_zone_2="#81C784",
    hr_zone_3="#FFD54F",
    hr_zone_4="#FFB74D",
    hr_zone_5="#E57373",
)

DAILY_COLORS = ReportColors(
    bg="#FAF7F2",
    card_bg="#FFFFFF",
    text_primary="#2D2D2D",
    text_secondary="#888888",
    text_light="#BBBBBB",
    accent="#E8A87C",
    accent_dark="#D4845A",
    bar_normal="#F5D5B8",
    bar_highlight="#E8A87C",
    hr_zone_1="#4FC3F7",
    hr_zone_2="#81C784",
    hr_zone_3="#FFD54F",
    hr_zone_4="#FFB74D",
    hr_zone_5="#E57373",
)

WEEKLY_COLORS = ReportColors(
    bg="#FAF7F2",
    card_bg="#FFFFFF",
    text_primary="#2D2D2D",
    text_secondary="#888888",
    text_light="#BBBBBB",
    accent="#E8A87C",
    accent_dark="#D4845A",
    bar_normal="#F5D5B8",
    bar_highlight="#E8A87C",
    hr_zone_1="#4FC3F7",
    hr_zone_2="#81C784",
    hr_zone_3="#FFD54F",
    hr_zone_4="#FFB74D",
    hr_zone_5="#E57373",
)

MONTHLY_COLORS = ReportColors(
    bg="#F5F0EB",
    card_bg="#FFFFFF",
    text_primary="#2D2D2D",
    text_secondary="#888888",
    text_light="#BBBBBB",
    accent="#E8A87C",
    accent_dark="#D4845A",
    bar_normal="#F5D5B8",
    bar_highlight="#E8A87C",
    hr_zone_1="#4FC3F7",
    hr_zone_2="#81C784",
    hr_zone_3="#FFD54F",
    hr_zone_4="#FFB74D",
    hr_zone_5="#E57373",
)

RACE_COLORS = ReportColors(
    bg="#1A1A1A",
    card_bg="#2A2A2A",
    text_primary="#FFFFFF",
    text_secondary="#BBBBBB",
    text_light="#888888",
    accent="#FFD700",
    accent_dark="#FFA500",
    bar_normal="#555555",
    bar_highlight="#FFD700",
    hr_zone_1="#4FC3F7",
    hr_zone_2="#81C784",
    hr_zone_3="#FFD54F",
    hr_zone_4="#FFB74D",
    hr_zone_5="#E57373",
)

# ── 状态色 ──

STATUS_GOOD = "#4CAF50"
STATUS_NORMAL = "#FFC107"
STATUS_WARNING = "#FF9800"
STATUS_DANGER = "#F44336"


def readiness_color(score: int) -> str:
    """根据准备度分数返回状态色"""
    if score >= 80:
        return STATUS_GOOD
    elif score >= 60:
        return STATUS_NORMAL
    elif score >= 40:
        return STATUS_WARNING
    else:
        return STATUS_DANGER


def trend_color(change_pct: float, inverse: bool = False) -> str:
    """
    根据变化百分比返回颜色。
    inverse=True 时反转（用于 RHR 等越低越好的指标）。
    """
    if inverse:
        change_pct = -change_pct
    if change_pct > 2:
        return STATUS_GOOD  # 进步
    elif change_pct < -2:
        return STATUS_DANGER  # 退步
    else:
        return STATUS_NORMAL  # 持平


# ── 字体层级 ──

@dataclass(frozen=True)
class ReportFonts:
    """字体大小定义"""
    title: int
    subtitle: int
    hero: int
    body: int
    caption: int


MORNING_FONTS = ReportFonts(title=32, subtitle=16, hero=64, body=14, caption=11)
DAILY_FONTS = ReportFonts(title=26, subtitle=14, hero=40, body=12, caption=10)
WEEKLY_FONTS = ReportFonts(title=24, subtitle=14, hero=36, body=12, caption=10)
MONTHLY_FONTS = ReportFonts(title=30, subtitle=16, hero=40, body=12, caption=10)
RACE_FONTS = ReportFonts(title=38, subtitle=18, hero=56, body=14, caption=11)


# ── 报表尺寸（英寸） ──

@dataclass(frozen=True)
class ReportSize:
    """报表尺寸定义"""
    width: float
    height: float
    dpi: int


MORNING_SIZE = ReportSize(width=1080/150, height=1920/150, dpi=150)  # 手机竖版
DAILY_SIZE = ReportSize(width=12, height=16, dpi=150)
WEEKLY_SIZE = ReportSize(width=12, height=16, dpi=150)
MONTHLY_SIZE = ReportSize(width=12, height=30, dpi=150)
RACE_SIZE = ReportSize(width=12, height=30, dpi=150)


# ── 布局常量 ──

CARD_RADIUS = 0.03          # 卡片圆角半径
CARD_PADDING = 0.02          # 卡片内边距
SECTION_SPACING = 0.015      # 模块间距
AI_INSIGHT_LEFT_LINE = 3     # AI Insight 左侧竖线宽度
AI_INSIGHT_BG_ALPHA = 0.08   # AI Insight 背景透明度
PROGRESS_BAR_HEIGHT = 0.012  # 进度条高度
