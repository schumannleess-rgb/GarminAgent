# 脚本修订计划

> 日期: 2026-05-20
> 基于: REQUIREMENTS.md v1.0
> 范围: 仅 Presentation Layer 脚本修订

---

## 修订总览

### 现有文件清单

| 文件 | 行数 | 状态 | 修订方式 |
|------|------|------|---------|
| `data_aggregator.py` | ~500 | 需增强 | 追加新字段计算方法 |
| `chart_renderer.py` | ~450 | 需增强 | 追加新图表 + 重构配色 |
| `morning_call.py` | ~250 | **重写** | 完全重写为 Morning Report |
| `post_run_report.py` | ~300 | **重写** | 重写为 Daily Report |
| `weekly_report.py` | ~350 | **重构** | 大幅重构信息架构 |
| `monthly_report.py` | ~300 | **重构** | 大幅重构 + 加 Hero/Narrative |
| `run_report.py` | ~160 | 小改 | 加 race 命令 + 更新输出名 |
| `mock_data.py` | ~300 | 小改 | 补充缺失字段 |
| **新建** `race_report.py` | — | **新建** | 全新实现 |
| **新建** `ai_narrator.py` | — | **新建** | AI Narrative 生成器 |
| **新建** `report_styles.py` | — | **新建** | 统一样式常量 |

### 修订优先级

```
Phase 0: 基础层 — 样式常量 + AI Narrator + 数据字段补全
Phase 1: P0   — Morning Report（全新）
Phase 2: P1   — Daily Report（重写）
Phase 3: P2   — Weekly Report（重构）
Phase 4: P3   — Monthly Report（重构）
Phase 5: P4   — Race Report（新建）
Phase 6: 收尾 — run_report.py 更新 + 测试
```

---

## Phase 0: 基础层

### 0.1 新建 `report_styles.py` — 统一样式常量

**目的**：所有报表共享的样式常量，避免硬编码分散

**需要定义的常量**：

```python
# 背景色
COLORS = {
    "morning_bg": "#FFFFFF",      # 纯白
    "daily_bg": "#FAF7F2",        # 米色
    "weekly_bg": "#FAF7F2",       # 米色
    "monthly_bg": "#F5F0EB",      # 浅米色
    "race_bg": "#1A1A1A",         # 深色
    "card_bg": "#FFFFFF",         # 卡片白
    "text_primary": "#2D2D2D",
    "text_secondary": "#888888",
    "text_light": "#BBBBBB",
    "accent": "#E8A87C",
    "accent_dark": "#D4845A",
}

# 状态色
STATUS_COLORS = {
    "good": "#4CAF50",       # 绿色 — 优/进步
    "normal": "#FFC107",     # 黄色 — 一般
    "warning": "#FF9800",    # 橙色 — 注意
    "danger": "#F44336",     # 红色 — 差/退步
}

# HR 区间色
HR_ZONE_COLORS = ["#4FC3F7", "#81C784", "#FFD54F", "#FFB74D", "#E57373"]

# 字体层级
FONTS = {
    "morning": {"title": 28, "subtitle": 16, "hero": 48, "body": 14, "caption": 11},
    "daily": {"title": 24, "subtitle": 14, "hero": 36, "body": 12, "caption": 10},
    "weekly": {"title": 22, "subtitle": 14, "hero": 32, "body": 12, "caption": 10},
    "monthly": {"title": 28, "subtitle": 16, "hero": 36, "body": 12, "caption": 10},
    "race": {"title": 36, "subtitle": 18, "hero": 48, "body": 14, "caption": 11},
}

# 比例
ASPECT_RATIOS = {
    "morning": (9, 16),    # 竖版手机卡
    "daily": (3, 4),       # 标准
    "weekly": (3, 4),      # 标准
    "monthly": (2, 5),     # 长海报
    "race": (2, 5),        # 长海报
}
```

**工作量**：~100 行

---

### 0.2 新建 `ai_narrator.py` — AI Narrative 生成器

**目的**：统一管理所有报表的 AI 文本生成

**需要实现的方法**：

| 方法 | 输入 | 输出 | 用于报表 |
|------|------|------|---------|
| `generate_morning_insight()` | health data + baseline | 建议型文本 | Morning |
| `generate_daily_insight()` | activity + splits + efficiency + history | 分析型文本 | Daily |
| `generate_weekly_coach()` | weekly load + recovery + efficiency trends | 教练型文本 | Weekly |
| `generate_monthly_narrative()` | monthly stats + efficiency growth + PB | 叙事型文本 | Monthly |
| `generate_race_commentary()` | race splits + HR zones + intelligence | 评论型文本 | Race |
| `generate_critical_moment()` | race splits + HR data | 关键时刻分析 | Race |

**每个方法的 Prompt 模板**：

```python
MORNING_INSIGHT_PROMPT = """
基于以下身体数据，生成一段简洁的晨间建议（1-2句话）：

HRV: {hrv}ms（基线: {baseline}ms，变化: {change}%）
静息心率: {rhr}bpm
睡眠评分: {sleep_score}/100，时长: {sleep_duration}
准备度: {readiness}/100

要求：
1. 个性化，基于实际数据
2. 给出行动建议（今天适合什么训练）
3. 提到具体指标
4. 简洁，不超过2句话
"""
```

**降级策略**：LLM 不可用时，用规则引擎生成模板文本

**工作量**：~200 行

---

### 0.3 增强 `data_aggregator.py` — 补全缺失字段

**现有方法 → 需要追加的字段**：

#### `get_morning_call_data()` → 重命名为 `get_morning_data()`

| 追加字段 | 说明 | 来源 |
|---------|------|------|
| `hrv_baseline` | 7天 HRV 平均 | 计算 |
| `hrv_change_pct` | HRV 较基线变化% | 计算 |
| `recovery_time` | 恢复时间(小时) | 计算 |
| `fatigue_level` | 疲劳程度 | 计算 |
| `stress_level` | 压力水平 | 可选 |

#### `get_post_run_data()` → 重命名为 `get_daily_data()`

| 追加字段 | 说明 | 来源 |
|---------|------|------|
| `hr_drift` | 心率漂移% | 需要算法 |
| `efficiency_score` | 跑步效率分 | 需要算法 |
| `vs_7d` | 7天对比 | 计算 |
| `vs_30d` | 30天对比 | 计算 |
| `recovery_time` | 恢复时间 | 计算 |

#### `get_weekly_data()` — 追加字段

| 追加字段 | 说明 | 来源 |
|---------|------|------|
| `recovery_trend_direction` | 恢复趋势方向 | 计算 |
| `efficiency_trend` | 效率趋势数据 | 计算 |
| `risk_alerts` | 风险预警列表 | 规则引擎 |
| `vs_last_week_efficiency` | 效率对比 | 计算 |

#### `get_monthly_data()` — 追加字段

| 追加字段 | 说明 | 来源 |
|---------|------|------|
| `achievements` | 3个核心成就 | 计算 |
| `avg_hrv` | 月度平均 HRV | 计算 |
| `sleep_consistency` | 睡眠一致性% | 计算 |
| `recovery_stability` | 恢复稳定性 | 计算 |
| `efficiency_growth` | 效率增长数据 | 计算 |

#### 新增 `get_race_data(activity_id)`

| 字段 | 说明 | 来源 |
|------|------|------|
| `race_name` | 赛事名称 | API |
| `first_half_time` | 前半程时间 | 计算 |
| `second_half_time` | 后半程时间 | 计算 |
| `climbing_section` | 爬升段数据 | 计算 |
| `downhill_section` | 下坡段数据 | 计算 |
| `race_intelligence` | 赛事智能分析 | 计算 |

**工作量**：~300 行追加

---

### 0.4 增强 `chart_renderer.py` — 新图表

| 新图表 | 方法名 | 用于报表 | 说明 |
|--------|--------|---------|------|
| Recovery Sparkline | `render_recovery_sparkline()` | Weekly | 7天 HRV/RHR/Sleep 迷你趋势 |
| Efficiency Sparkline | `render_efficiency_sparkline()` | Weekly | 效率指标迷你趋势 |
| HR Drift Chart | `render_hr_drift_chart()` | Daily | 心率漂移可视化 |
| Race Pace Gradient | `render_race_pace_gradient()` | Race | 渐变色配速图 |

**重构**：
- 将 `Colors` 类迁移到 `report_styles.py`
- 所有图表方法支持新的样式常量

**工作量**：~200 行追加 + 重构

---

## Phase 1: P0 — Morning Report（重写）

### 重写 `morning_call.py` → `morning_report.py`

**现有结构**（3行2列，有图表）→ **新结构**（竖版极简，无图表）

#### 新布局

```
┌─────────────────────────┐  Row 0: Morning Readiness Score
│      Readiness Score    │  (大数字居中 + 状态描述)
├─────────────────────────┤  Row 1: Recovery + Sleep 双列
│  Recovery  │   Sleep    │  (纯文字 + 数字)
├─────────────────────────┤  Row 2: AI Insight
│    AI Insight Block     │  (引用块样式)
├─────────────────────────┤  Row 3: Today's Suggestion
│  Today's Suggestion     │  (3行简洁文字)
└─────────────────────────┘
```

#### 删除的模块

- 健康趋势图表（7天 HRV/RHR/Sleep 图）
- 周训练负荷
- 本周目标提醒

#### 新增的模块

- Readiness Score 大数字
- Recovery 模块（HRV/RHR/Recovery Time/Fatigue）
- Sleep 模块（Score/Duration）
- Today's Suggestion（训练类型/时长/强度）

#### 视觉变化

- 背景色：`#FAF7F2` → `#FFFFFF` 纯白
- 比例：16:18 → 9:16 竖版
- 图表：删除所有图表
- 字体：加大 Readiness Score

**工作量**：~250 行（重写）

---

## Phase 2: P1 — Daily Report（重写）

### 重写 `post_run_report.py` → `daily_report.py`

**现有结构**（4行2列，8个跑步指标平铺）→ **新结构**（Recovery + Efficiency 双模块）

#### 新布局

```
┌─────────────────────────────────────┐  Row 0: Header
│  Training Title + Date/Location     │
├─────────────────────────────────────┤  Row 1: Hero Data
│  Distance │ Duration │ Pace │ Elev  │  (四大数字)
├──────────────────┬──────────────────┤  Row 2: Recovery + Efficiency
│  Recovery        │  Efficiency      │  (双模块对称)
├──────────────────┴──────────────────┤
│  ┌─────────────────────────────┐    │  Row 3: Pace Split Chart
│  │  Pace Split Chart           │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤
│  ┌─────────────────────────────┐    │  Row 4: AI Insight
│  │  AI Insight                 │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤  Row 5: Trend Comparison
│  vs 7d │ vs 30d                     │
└─────────────────────────────────────┘
```

#### 删除的模块

- 8个跑步指标平铺（步频/步幅/触地时间等）
- 身体状态文本
- 历史对比占位符
- 目标进度条

#### 新增的模块

- **Recovery 模块**（Readiness/HRV/Sleep/Recovery Time）
- **Efficiency 模块**（Cadence/Stride/GCT/Vertical Ratio/HR Drift）
- **Trend Comparison**（vs 7d / vs 30d）

**工作量**：~300 行（重写）

---

## Phase 3: P2 — Weekly Report（重构）

### 重构 `weekly_report.py`

**现有结构**（4行2列，数据海报）→ **新结构**（分析感，趋势优先）

#### 新布局

```
┌─────────────────────────────────────┐  Row 0: Header
│  Weekly Training Report + Date      │
├─────────────────────────────────────┤  Row 1: Weekly Load
│  Distance │ Time │ Elev │ Calories  │
├──────────────────┬──────────────────┤  Row 2: Recovery + Efficiency Trends
│  Recovery Trend  │  Efficiency      │  (sparkline 图)
│  [sparkline]     │  Trend [sparkline]│
├──────────────────┴──────────────────┤
│  ┌─────────────────────────────┐    │  Row 3: Daily Distance
│  │  7天跑量柱状图              │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤
│  ┌─────────────────────────────┐    │  Row 4: AI Coach Summary
│  │  AI Coach Summary           │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤  Row 5: Risk Alert (条件显示)
│  Risk Alert                         │
├─────────────────────────────────────┤  Row 6: Training Distribution
│  Z1-Z5 │ vs Last Week              │
└─────────────────────────────────────┘
```

#### 删除的模块

- 训练类型甜甜圈
- 心率区间甜甜圈（移到 Daily）
- 本周高光文本
- 目标进度条

#### 新增的模块

- **Recovery Trend**（HRV/RHR/Sleep sparkline）
- **Efficiency Trend**（Pace/HR/Cadence sparkline）
- **AI Coach Summary**（教练级建议）
- **Risk Alert**（条件显示）
- **vs Last Week**（效率对比）

**工作量**：~350 行（重构）

---

## Phase 4: P3 — Monthly Report（重构）

### 重构 `monthly_report.py`

**现有结构**（6行2列，数据海报）→ **新结构**（仪式感，叙事优先）

#### 新布局

```
┌─────────────────────────────────────┐  Row 0: Opening Hero (全宽大图)
│  [Hero Image + APRIL RECAP]         │
├─────────────────────────────────────┤  Row 1: Achievement
│  Achievement 1 │ 2 │ 3              │  (先放成就)
├─────────────────────────────────────┤  Row 2: Training Overview
│  Distance │ Time │ Elev │ Days      │
├──────────────────┬──────────────────┤  Row 3: Recovery + Efficiency
│  Recovery Summary│  Efficiency      │
│                  │  Growth          │
├──────────────────┴──────────────────┤
│  ┌─────────────────────────────┐    │  Row 4: Weekly Trend
│  │  4周跑量趋势图              │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤
│  ┌─────────────────────────────┐    │  Row 5: AI Monthly Narrative
│  │  AI Monthly Narrative       │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤  Row 6: Personal Best
│  PB Records (奖牌样式)              │
├─────────────────────────────────────┤  Row 7: Next Month Goal
│  Goals                              │
└─────────────────────────────────────┘
```

#### 删除的模块

- 每日跑量柱状图（31天太密，视觉噪音）
- 心率区间甜甜圈
- 健康月度占位符

#### 新增的模块

- **Opening Hero**（大图 + 叠加文字）
- **Achievement**（核心成就，先于 Training Overview）
- **Recovery Summary**（Avg HRV/Sleep Consistency/Stability）
- **Efficiency Growth**（Aerobic/Cadence/HR Drift 变化）
- **AI Monthly Narrative**（叙事型文本）
- **Personal Best**（奖牌/徽章样式）
- **Next Month Goal**

**工作量**：~350 行（重构）

---

## Phase 5: P4 — Race Report（新建）

### 新建 `race_report.py`

#### 布局

```
┌─────────────────────────────────────┐  Row 0: Hero (全宽大图)
│  [Race Photo + Name + Result]       │
├─────────────────────────────────────┤  Row 1: Split Analysis
│  前半 │ 后半 │ 爬升段 │ 下坡段     │
├──────────────────┬──────────────────┤  Row 2: Charts
│  Pace Split      │  HR Zone Donut   │
├──────────────────┴──────────────────┤
│  ┌─────────────────────────────┐    │  Row 3: Critical Moment
│  │  Critical Moment            │    │
│  └─────────────────────────────┘    │
├─────────────────────────────────────┤  Row 4: Race Intelligence
│  Fuel │ HR │ Climbing │ Downhill   │
├─────────────────────────────────────┤
│  ┌─────────────────────────────┐    │  Row 5: Finish Narrative
│  │  Finish Narrative + Quote   │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

#### 视觉特殊要求

- 深色背景 `#1A1A1A`
- 白色/浅色文字
- Hero 大图
- 配速图渐变色
- Finish Narrative 杂志引用样式

**工作量**：~300 行（新建）

---

## Phase 6: 收尾

### 6.1 更新 `run_report.py`

| 变更 | 说明 |
|------|------|
| `post` → `daily` | 重命名命令 |
| `morning` → 保持 | 但内部调用新类 |
| 新增 `race` 命令 | `python run_report.py race [--activity-id ID]` |
| 更新 `all` | 包含所有 5 种报表 |
| 更新输出文件名 | `morning_report.png`, `daily_report.png` 等 |

### 6.2 更新 `mock_data.py`

追加以下字段的 mock 数据：

| 字段 | 说明 |
|------|------|
| `hrv_baseline` | 7天 HRV 平均 |
| `recovery_time` | 恢复时间 |
| `fatigue_level` | 疲劳程度 |
| `hr_drift` | 心率漂移 |
| `vs_7d`, `vs_30d` | 历史对比 |
| `risk_alerts` | 风险预警 |
| `achievements` | 月度成就 |
| `race_intelligence` | 赛事智能 |

### 6.3 测试验证

每个 Phase 完成后，用 `python run_report.py {type} --no-mock` 验证：

| Phase | 验证命令 | 预期输出 |
|-------|---------|---------|
| Phase 1 | `python run_report.py morning --no-mock` | `output/morning_report.png` |
| Phase 2 | `python run_report.py daily --no-mock` | `output/daily_report.png` |
| Phase 3 | `python run_report.py weekly --no-mock` | `output/weekly_report.png` |
| Phase 4 | `python run_report.py monthly --no-mock` | `output/monthly_report.png` |
| Phase 5 | `python run_report.py race --no-mock` | `output/race_report.png` |
| Phase 6 | `python run_report.py all --no-mock` | 5 张报表全部生成 |

---

## 工作量估算

| Phase | 文件 | 行数 | 难度 |
|-------|------|------|------|
| Phase 0 | report_styles.py | ~100 | 低 |
| Phase 0 | ai_narrator.py | ~200 | 中 |
| Phase 0 | data_aggregator.py 追加 | ~300 | 中 |
| Phase 0 | chart_renderer.py 追加 | ~200 | 中 |
| Phase 1 | morning_report.py（重写） | ~250 | 低 |
| Phase 2 | daily_report.py（重写） | ~300 | 中 |
| Phase 3 | weekly_report.py（重构） | ~350 | 中 |
| Phase 4 | monthly_report.py（重构） | ~350 | 中 |
| Phase 5 | race_report.py（新建） | ~300 | 高 |
| Phase 6 | run_report.py + mock_data.py | ~100 | 低 |
| **总计** | | **~2,450** | |

---

## 依赖关系

```
Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5 ──→ Phase 6
   │            │            │            │            │            │
   └─ 基础层    └─ P0        └─ P1        └─ P2        └─ P3        └─ P4
     必须先完成   可独立       可独立       可独立       可独立       可独立
```

**关键依赖**：
- Phase 0 必须先完成（所有 Phase 依赖样式常量和数据字段）
- Phase 1-5 可以并行开发（互相独立）
- Phase 6 最后收尾

---

## 风险点

| 风险 | 影响 | 缓解 |
|------|------|------|
| HR Drift 算法缺失 | Daily/Efficiency 模块无法计算 | Phase 0 先实现简化版（前后半程 HR 差） |
| AI Narrator LLM 调用失败 | AI Insight 为空 | 降级到规则引擎模板 |
| 深色背景 Race Report 渲染 | 文字可读性 | 测试多组配色 |
| 竖版 Morning Report 比例 | matplotlib 布局 | 用 GridSpec 精确控制 |
| Hero Image 管理 | 月报/赛事大图来源 | Phase 0 定义接口，具体实现后补 |
