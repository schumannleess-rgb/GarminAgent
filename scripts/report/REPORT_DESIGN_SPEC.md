# Garmin Training Report — Presentation Layer 规范

> 版本: v2.0 设计规范
> 日期: 2026-05-20
> 范围: 仅 Presentation Layer（信息架构 + 视觉层次 + 情绪定位）
> 不涉及: API、数据同步、Schema、Analytics Engine、算法实现

---

## 一、设计哲学

### 核心原则

| 原则 | 说明 |
|------|------|
| **少而精** | 高级感 = 少而精，不是数据堆砌 |
| **信息设计** | Information Design，不是 Dashboard |
| **情绪分层** | 每种报表有独立的情绪定位 |
| **叙事感** | 用数据讲故事，不是列数据 |

### 三大核心模块

所有报表围绕三个核心模块构建：

| 模块 | 定位 | 数据来源 |
|------|------|---------|
| **AI Insights** | 智能解读，产品价值核心 | LLM 生成 |
| **Recovery** | 身体恢复状态 | HRV / RHR / Sleep / Readiness |
| **Efficiency** | 运动效率指标 | Cadence / Stride / GCT / VO / HR Drift |

### 视觉参考

目标风格对标：
- **Apple Health** — 安静的高级感
- **WHOOP** — 数据密度 + 分析深度
- **Oura** — 极简 + 健康聚焦

---

## 二、五种报表总览

| 报表 | 定位 | 风格 | 核心情绪 | 尺寸 | 场景 |
|------|------|------|---------|------|------|
| **Morning Report** | 身体状态卡 | 极简 | Calm | 竖版手机卡 | 每日晨起 |
| **Daily Report** | 单日训练分析 | 数据感 | Focus | 标准海报 | 跑步后 |
| **Weekly Report** | 趋势与恢复 | 分析感 | Analysis | 标准海报 | 每周日 |
| **Monthly Report** | 成长总结 | 仪式感 | Achievement | 长海报 | 每月末 |
| **Race Report** | 高光时刻 | 电影感 | Epic | 长海报 | 比赛后 |

### 情绪矩阵

```
Calm ←————————————→ Epic
Morning    Daily    Weekly    Monthly    Race
 极简      数据感    分析感    仪式感     电影感
```

---

## 三、Morning Report（最重要）

### 定位
- **传播性最强**的报表
- 小卡片，竖版，手机截图即分享
- 核心情绪：**Calm**（安静的高级感）
- **不要做成 dashboard**，要像 Apple Health / WHOOP / Oura

### 信息结构

```
┌─────────────────────────────┐
│                             │
│     Morning Readiness       │
│                             │
│           82                │  ← 大数字，居中
│    Ready for Quality        │
│       Training              │  ← 状态描述
│                             │
├─────────────────────────────┤
│                             │
│  Recovery    │    Sleep     │
│  ─────────   │   ─────────  │
│  HRV: 64ms   │  Score: 78   │
│  RHR: 44bpm  │  Duration:   │
│              │   7h 32m     │
│  Fatigue     │              │
│  Recovery:   │              │
│   14h        │              │
│                             │
├─────────────────────────────┤
│                             │
│  ┌───────────────────────┐  │
│  │  AI Insight           │  │
│  │                       │  │
│  │  睡眠恢复良好，HRV     │  │
│  │  高于基线 9%，今天     │  │
│  │  适合进行节奏跑或      │  │
│  │  爬坡训练。           │  │
│  │                       │  │
│  └───────────────────────┘  │
│                             │
├─────────────────────────────┤
│                             │
│  Today's Suggestion         │
│  ─────────────────          │
│  Training: 节奏跑           │
│  Duration: 45 min           │
│  Intensity: Z3-Z4           │
│                             │
└─────────────────────────────┘
```

### 信息密度

| 区域 | 数据量 | 目的 |
|------|--------|------|
| Readiness Score | 1 个数字 | 一眼判断状态 |
| Recovery | 4-5 个指标 | 身体恢复详情 |
| Sleep | 2-3 个指标 | 睡眠质量 |
| AI Insight | 1 段话 | 智能解读 |
| Suggestion | 3 行 | 今日行动指南 |

**总数据量: ~12 个数据点**（极简）

### 视觉要求

- **留白**是最重要的设计元素
- 背景：纯白或极浅灰（不是米色）
- 字体：大号数字 + 小号说明
- 颜色：只用状态色（绿/黄/红）+ 中性色
- 无图表，纯文字 + 数字
- 竖版比例：9:16 或 3:4

---

## 四、Daily Report（单次训练复盘）

### 定位
- 单次训练的深度分析
- 核心情绪：**Focus**（专注）
- 重点不是"统计"，而是"今天跑得怎么样"
- 训练表现必须和恢复关联

### 信息结构

```
┌─────────────────────────────────────────┐
│                                         │
│  Evening Mountain Tempo                 │  ← 训练标题
│  2026-05-20 · 无锡 · 22°C 晴           │  ← 日期/地点/天气
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  6.5 km    0:59:09    9:07    17m      │  ← 四大核心数字
│  Distance  Duration   Pace   Elev.     │
│                                         │
├────────────────────┬────────────────────┤
│                    │                    │
│  Recovery          │  Efficiency        │
│  ─────────         │  ────────────      │
│  Readiness: 82     │  Cadence: 176      │
│  HRV: 64ms         │  Stride: 1.08m     │
│  Sleep: 78         │  GCT: 248ms        │
│  Recovery: 14h     │  Vert Ratio: 8.2%  │
│                    │  HR Drift: +3.2%   │
│                    │                    │
├────────────────────┴────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐    │
│  │  Pace Split Chart               │    │
│  │  (per-km pace bars + HR line)   │    │
│  └─────────────────────────────────┘    │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐    │
│  │  AI Insight                     │    │
│  │                                 │    │
│  │  后半程心率漂移明显下降，       │    │
│  │  说明有氧效率正在提升。         │    │
│  │  爬坡段配速稳定性较上周提升。   │    │
│  └─────────────────────────────────┘    │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  vs Last 7 Days        vs Last 30 Days  │
│  ─────────────         ──────────────   │
│  Pace: ↑ 3%            Pace: ↑ 5%       │
│  Efficiency: ↑ 4%      Efficiency: ↑ 7% │
│                                         │
└─────────────────────────────────────────┘
```

### 信息密度

| 区域 | 数据量 | 目的 |
|------|--------|------|
| Header | 3 行 | 训练元信息 |
| Hero Data | 4 个数字 | 核心表现 |
| Recovery | 4 个指标 | 身体状态 |
| Efficiency | 5 个指标 | 运动效率（核心高级感） |
| Pace Chart | 1 个图表 | 配速分析 |
| AI Insight | 1-2 段话 | 智能解读 |
| Trend Comparison | 2 组对比 | 进步可视化 |

**总数据量: ~20 个数据点**（适中）

### 视觉要求

- 背景：米色系（延续现有）
- Hero Data 四个数字要大，占视觉重心
- Efficiency 模块用**特殊卡片样式**突出（区别于普通 App）
- AI Insight 用引用块样式
- Trend Comparison 用箭头 + 百分比
- 标准比例：3:4 或 4:5

---

## 五、Weekly Report（趋势与恢复）

### 定位
- 周度趋势分析
- 核心情绪：**Analysis**（分析感）
- 核心是**累积疲劳**和**恢复质量**
- 不要太"海报"，要有分析深度

### 信息结构

```
┌─────────────────────────────────────────┐
│                                         │
│  Weekly Training Report                 │
│  2026-05-18 ~ 2026-05-24               │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Weekly Load                            │
│  ────────────                           │
│  42.5 km │ 5:32:00 │ 320m │ 2,840 kcal │
│  Total Dist │ Time │ Elev │ Calories    │
│                                         │
├────────────────────┬────────────────────┤
│                    │                    │
│  Recovery Trend    │  Efficiency Trend  │
│  ──────────────    │  ────────────────  │
│  HRV: 62 → 58 ↓    │  Pace/HR: ↑ 3%    │
│  RHR: 44 → 46 ↑    │  Cadence: 176→178  │
│  Sleep: 75 → 72 ↓   │  Efficiency: ↑ 4%  │
│                    │                    │
│  [7天趋势图]       │  [趋势图]          │
│                    │                    │
├────────────────────┴────────────────────┤
│                                         │
│  Daily Distance Overview                │
│  ──────────────────────                 │
│  [7天跑量柱状图 + 爬升线]               │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐    │
│  │  AI Coach Summary               │    │
│  │                                 │    │
│  │  本周整体恢复稳定，但高强度      │    │
│  │  训练占比偏高。建议下周增加      │    │
│  │  Z2 跑比例以改善恢复质量。       │    │
│  └─────────────────────────────────┘    │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Risk Alert                             │
│  ────────────                           │
│  ⚠ Acute Load 已连续 5 天高于推荐范围   │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Training Distribution     vs last week │
│  ────────────────────      ──────────── │
│  Z1: 15%  Z2: 35%          Distance: ↑8%│
│  Z3: 30%  Z4: 15%          Load: ↑12%   │
│  Z5: 5%                     Recovery: ↓3%│
│                                         │
└─────────────────────────────────────────┘
```

### 信息密度

| 区域 | 数据量 | 目的 |
|------|--------|------|
| Weekly Load | 4 个数字 | 本周总量 |
| Recovery Trend | 3 个趋势 + 图表 | 恢复质量追踪 |
| Efficiency Trend | 3 个趋势 + 图表 | 效率变化 |
| Daily Distance | 1 个图表 | 跑量分布 |
| AI Coach Summary | 1-2 段话 | 教练级建议 |
| Risk Alert | 0-1 条 | 风险预警 |
| Training Distribution | 5 个区间 + 对比 | 强度分析 |

**总数据量: ~25 个数据点**（较高）

### 视觉要求

- 背景：米色系
- Recovery 和 Efficiency 用**左右对比布局**
- 趋势用**迷你折线图**（sparkline 风格）
- AI Coach Summary 用**特殊样式**突出
- Risk Alert 用**警告色**（红色/橙色）
- 标准比例：3:4

---

## 六、Monthly Report（成长总结）

### 定位
- 月度成长叙事
- 核心情绪：**Achievement**（仪式感）
- 重要的是**成长感**，不是统计感
- 需要 Narrative（叙事感）

### 信息结构

```
┌─────────────────────────────────────────┐
│                                         │
│  ┌─────────────────────────────────┐    │
│  │                                 │    │
│  │      [大图: 山脊/长距离/赛事]    │    │
│  │                                 │    │
│  │      APRIL RECAP                │    │
│  │      2026                       │    │
│  │                                 │    │
│  └─────────────────────────────────┘    │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Achievement                            │  ← 先放成就，不是跑量
│  ──────────                             │
│  🏆 Highest Weekly Load: 127 km         │
│  🏔 New Climbing PB: 3,290m             │
│  🏃 Longest Trail Run: 27.94 km         │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Training Overview                      │
│  ────────────────                       │
│  422.71 km │ 43:16:25 │ 18,684m │ 25天  │
│  Distance  │ Time     │ Elev    │ Days  │
│                                         │
├────────────────────┬────────────────────┤
│                    │                    │
│  Recovery Summary  │  Efficiency Growth │
│  ──────────────    │  ────────────────  │
│  Avg HRV: 62ms     │  Aerobic: +7%      │
│  Sleep Consistency │  Cadence: +4%      │
│    85%             │  HR Drift: -6%     │
│  Recovery Stable   │                    │
│                    │  [趋势图]          │
├────────────────────┴────────────────────┤
│                                         │
│  Weekly Trend                           │
│  ────────────                           │
│  [4周跑量趋势图]                         │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐    │
│  │  AI Monthly Narrative           │    │
│  │                                 │    │
│  │  本月训练稳定性明显提升，        │    │
│  │  长距离耐力增强。恢复状态        │    │
│  │  整体良好，但高强度训练后        │    │
│  │  恢复时间偏长。                 │    │
│  └─────────────────────────────────┘    │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Personal Best                          │
│  ─────────────                          │
│  5K: 19:12    10K: 39:38    Half: 1:27  │
│  Full: 3:03:14    Trail 27K: 5:48:07    │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Next Month Goal                        │
│  ───────────────                        │
│  月跑量 450-500 km                       │
│  加强速度与阈值训练                      │
│  提升高距离耐力                          │
│                                         │
└─────────────────────────────────────────┘
```

### 信息密度

| 区域 | 数据量 | 目的 |
|------|--------|------|
| Hero Image | 1 张图 | 视觉冲击 |
| Achievement | 3 个成就 | 核心亮点 |
| Training Overview | 4 个数字 | 总量概览 |
| Recovery Summary | 3 个指标 | 恢复追踪 |
| Efficiency Growth | 3 个变化量 | 进步可视化 |
| Weekly Trend | 1 个图表 | 周度变化 |
| AI Narrative | 1-2 段话 | 成长叙事 |
| PB Records | 5 个成绩 | 个人最佳 |
| Next Month Goal | 3-4 行 | 下月方向 |

**总数据量: ~25 个数据点**（较高，但有叙事主线）

### 视觉要求

- **Opening Hero 必须有大图**（山脊、赛事、高光瞬间）
- Achievement 放在 Training Overview **之前**
- AI Narrative 用**特殊样式**，像杂志编辑推荐
- PB Records 用**奖牌/徽章**样式
- 整体比例：长海报 2:5 或 1:3

---

## 七、Race Report（最容易出圈）

### 定位
- 赛事高光复盘
- 核心情绪：**Epic**（电影感）
- 最容易在社交媒体传播
- 需要**叙事弧线**

### 信息结构

```
┌─────────────────────────────────────────┐
│                                         │
│  ┌─────────────────────────────────┐    │
│  │                                 │    │
│  │      [赛事照片]                 │    │
│  │                                 │    │
│  │      峨眉山越野                 │    │
│  │      27.94 km · 3290m+          │    │
│  │      5:48:07                    │    │
│  │                                 │    │
│  └─────────────────────────────────┘    │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Split Analysis                         │
│  ──────────────                         │
│  前半: 2:48:12  │  后半: 2:59:55        │
│  爬升段: +1,800m │  下坡段: -1,490m     │
│                                         │
├────────────────────┬────────────────────┤
│                    │                    │
│  [配速拆分图]      │  [心率区间分布]     │
│                    │                    │
├────────────────────┴────────────────────┤
│                                         │
│  Critical Moment                        │
│  ───────────────                        │
│  32km 后出现明显配速下降，              │
│  但爬坡段表现依旧稳定。                 │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Race Intelligence                      │
│  ────────────────                       │
│  Fuel Timing: 每 45min 补给一次         │
│  HR Collapse: 无明显心率崩塌            │
│  Climbing Efficiency: 128m/km           │
│  Downhill Control: 配速稳定             │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐    │
│  │  Finish Narrative               │    │
│  │                                 │    │
│  │  这是一次节奏控制非常成熟的      │    │
│  │  比赛。尽管后半程出现疲劳，      │    │
│  │  但爬坡段表现依旧稳定。          │    │
│  │                                 │    │
│  │  "不是终点有多远，而是自己      │    │
│  │   能走多远。"                   │    │
│  └─────────────────────────────────┘    │
│                                         │
└─────────────────────────────────────────┘
```

### 信息密度

| 区域 | 数据量 | 目的 |
|------|--------|------|
| Hero | 1 张图 + 3 个数字 | 视觉冲击 |
| Split Analysis | 4 个数据 | 前后半对比 |
| Charts | 2 个图表 | 配速 + 心率 |
| Critical Moment | 1 段话 | 关键时刻 |
| Race Intelligence | 4 个维度 | 深度分析 |
| Finish Narrative | 1-2 段话 | 叙事收尾 |

**总数据量: ~15 个数据点**（精炼）

### 视觉要求

- **必须有赛事照片**作为 Hero
- 整体风格像**运动品牌广告**
- 配速图用**渐变色**表示强度
- Finish Narrative 用**杂志引用**样式
- 可加名言收尾
- 比例：长海报 2:5

---

## 八、信息密度对比

| 报表 | 数据点数 | 图表数 | 文字段落 | 信息密度 |
|------|---------|--------|---------|---------|
| Morning | ~12 | 0 | 2-3 | ★☆☆☆☆ 极简 |
| Daily | ~20 | 1 | 3-4 | ★★★☆☆ 适中 |
| Weekly | ~25 | 3-4 | 2-3 | ★★★★☆ 较高 |
| Monthly | ~25 | 2-3 | 3-4 | ★★★★☆ 较高 |
| Race | ~15 | 2 | 3-4 | ★★☆☆☆ 精炼 |

### 信息密度与情绪的关系

```
极简 ──────────────────────────── 繁复
  │                                │
  Morning    Race    Daily    Weekly/Monthly
  (Calm)    (Epic)  (Focus)   (Analysis/Achievement)
```

**关键洞察**：
- 情绪越安静（Calm），数据越少
- 情绪越激烈（Epic），数据越精炼但视觉冲击越强
- 分析型（Analysis）数据密度最高

---

## 九、三大核心模块在各报表中的分布

### Recovery 模块

| 报表 | Recovery 呈现方式 |
|------|------------------|
| Morning | **主角** — Readiness Score + HRV/RHR/Sleep 全量 |
| Daily | **配角** — 小模块，4 个指标 |
| Weekly | **趋势** — 7 天 HRV/RHR/Sleep 趋势图 |
| Monthly | **总结** — 月度平均 + 一致性 |
| Race | **缺席** — 赛事报表不需要恢复数据 |

### Efficiency 模块

| 报表 | Efficiency 呈现方式 |
|------|-------------------|
| Morning | **缺席** — 晨报不需要效率数据 |
| Daily | **核心** — Cadence/Stride/GCT/VO/HR Drift 全量 |
| Weekly | **趋势** — 效率指标周度变化 |
| Monthly | **成长** — 效率指标月度增长百分比 |
| Race | **深度** — Climbing Efficiency/Downhill Control |

### AI Insights 模块

| 报表 | AI Insight 呈现方式 |
|------|-------------------|
| Morning | **建议型** — 今天适合什么训练 |
| Daily | **分析型** — 这次训练表现如何 |
| Weekly | **教练型** — 本周总结 + 下周建议 |
| Monthly | **叙事型** — 本月成长故事 |
| Race | **评论型** — 赛事关键时刻解读 |

---

## 十、视觉差异化规范

### 背景色

| 报表 | 背景色 | 说明 |
|------|--------|------|
| Morning | `#FFFFFF` 纯白 | 安静、干净 |
| Daily | `#FAF7F2` 米色 | 延续现有风格 |
| Weekly | `#FAF7F2` 米色 | 延续现有风格 |
| Monthly | `#F5F0EB` 浅米色 | 略深，仪式感 |
| Race | `#1A1A1A` 深色 | 电影感、冲击力 |

### 字体层级

| 元素 | Morning | Daily | Weekly | Monthly | Race |
|------|---------|-------|--------|---------|------|
| 主标题 | 28pt | 24pt | 22pt | 28pt | 36pt |
| 副标题 | 16pt | 14pt | 14pt | 16pt | 18pt |
| 大数字 | 48pt | 36pt | 32pt | 36pt | 48pt |
| 正文 | 14pt | 12pt | 12pt | 12pt | 14pt |
| 说明文字 | 11pt | 10pt | 10pt | 10pt | 11pt |

### 特殊样式

| 样式 | 用于 | 效果 |
|------|------|------|
| 引用块 | AI Insight | 左侧竖线 + 浅色背景 |
| 状态色 | Recovery/Ready | 绿/黄/红 |
| 箭头 | Trend Comparison | ↑↓ + 百分比 |
| 进度条 | Goal Progress | 圆角矩形 + 渐变 |
| 警告块 | Risk Alert | 红色/橙色背景 |
| 奖牌 | PB Records | 金银铜色圆形 |
| 大图 | Monthly Hero / Race Hero | 全宽图片 + 叠加文字 |

---

## 十一、数据需求清单（给 Data Layer 的输入）

### Morning Report 需要的数据

```yaml
morning_report:
  readiness_score: int          # 0-100
  readiness_level: string       # 优/一般/需休息
  hrv_last_night: int           # ms
  hrv_baseline: int             # ms (7天平均)
  rhr: int                      # bpm
  sleep_score: int              # 0-100
  sleep_duration: string        # "7h 32m"
  fatigue_level: string         # 低/中/高
  recovery_time: string         # "14h"
  ai_insight: string            # LLM 生成
  suggestion:
    training_type: string       # 轻松跑/节奏跑/休息
    duration: string            # "45 min"
    intensity: string           # Z2/Z3-Z4/Rest
```

### Daily Report 需要的数据

```yaml
daily_report:
  activity:
    name: string
    date: string
    location: string
    weather: string
    distance: float             # km
    duration: string            # "0:59:09"
    pace: string                # "9:07"
    elevation: int              # m
  recovery:
    readiness: int
    hrv: int
    sleep_score: int
    recovery_time: string
  efficiency:
    cadence: int                # spm
    stride_length: float        # m
    ground_contact_time: int    # ms
    vertical_ratio: float       # %
    hr_drift: float             # %
  splits: []                    # per-km data
  hr_zones: []                  # zone distribution
  ai_insight: string
  trend_comparison:
    vs_7d: { pace: "+3%", efficiency: "+4%" }
    vs_30d: { pace: "+5%", efficiency: "+7%" }
```

### Weekly Report 需要的数据

```yaml
weekly_report:
  week_start: date
  week_end: date
  load:
    distance: float
    duration: string
    elevation: int
    calories: int
  recovery_trend:
    hrv_daily: [int]            # 7 个值
    rhr_daily: [int]
    sleep_daily: [int]
    trend_direction: string     # improving/stable/declining
  efficiency_trend:
    pace_vs_hr: float           # % change
    cadence_trend: [int]
    efficiency_score: float     # % change
  daily_breakdown: []
  ai_coach_summary: string
  risk_alerts: [string]         # 0-N 条
  training_distribution:
    z1: float
    z2: float
    z3: float
    z4: float
    z5: float
  vs_last_week: {}
```

### Monthly Report 需要的数据

```yaml
monthly_report:
  month: string                 # "2026年05月"
  hero_image: string            # 图片路径（可选）
  achievements: []              # 3 个核心成就
  training_overview:
    distance: float
    duration: string
    elevation: int
    days: int
  recovery_summary:
    avg_hrv: int
    sleep_consistency: float    # %
    recovery_stability: string  # stable/volatile
  efficiency_growth:
    aerobic: string             # "+7%"
    cadence: string             # "+4%"
    hr_drift: string            # "-6%"
  weekly_trend: []
  ai_narrative: string
  pb_records: {}
  next_month_goals: [string]
```

### Race Report 需要的数据

```yaml
race_report:
  race_name: string
  race_date: date
  hero_image: string
  result:
    distance: float
    elevation: int
    finish_time: string
  splits:
    first_half: string
    second_half: string
    climbing_section: string
    downhill_section: string
  critical_moment: string       # AI 生成
  race_intelligence:
    fuel_timing: string
    hr_collapse: string
    climbing_efficiency: string
    downhill_control: string
  finish_narrative: string      # AI 生成
  quote: string                 # 可选名言
```

---

## 十二、实施优先级

| 优先级 | 报表 | 原因 |
|--------|------|------|
| **P0** | Morning Report | 传播性最强，极简设计最容易出效果 |
| **P1** | Daily Report | 使用频率最高，核心体验 |
| **P2** | Weekly Report | 分析深度，用户粘性 |
| **P3** | Monthly Report | 仪式感，社交分享 |
| **P4** | Race Report | 特定场景，但最容易出圈 |

---

## 十三、与现有实现的差距

### 现有问题

| 问题 | 现状 | 目标 |
|------|------|------|
| 报表同质化 | 4 种报表长得差不多 | 5 种报表各有独立风格 |
| 信息空泛 | 大量占位符和零值 | 精确的信息设计 |
| 缺乏叙事 | 数据罗列 | AI 驱动的叙事 |
| 无 Race Report | 缺失 | 电影感设计 |
| Recovery/Efficiency | 混在其他模块 | 独立核心模块 |
| AI Insight | 简单模板 | 深度解读 |
| 视觉层次 | 所有报表同一风格 | 按情绪分层 |

### 需要新增的能力

| 能力 | 说明 |
|------|------|
| AI Narrative Generator | 根据数据生成叙事文本 |
| Risk Alert Engine | 检测异常训练模式 |
| Trend Comparison | 7天/30天对比计算 |
| Efficiency Calculator | HR Drift / Running Efficiency |
| Hero Image Manager | 月报/赛事大图管理 |
| 竖版布局 | Morning Report 专用 |
