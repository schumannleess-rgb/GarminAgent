# Garmin Training Report — 完整需求文档

> 版本: v1.0
> 日期: 2026-05-20
> 范围: 仅 Presentation Layer（信息架构 + 视觉层次 + 情绪定位）
> 不涉及: API、数据同步、Schema、Analytics Engine、算法实现

---

## 〇、设计哲学

### 核心问题

现有报表存在以下问题：

1. **内容太空泛** — 大量占位符和零值，没有实际分析深度
2. **没有节奏感** — 所有报表从头到尾一个密度，没有松紧变化
3. **数据量太小** — 完全不是原来给的需求版本，做了大量简化
4. **报表同质化** — 4 种报表长得差不多，没有独立风格

### 解决方向

- **高级感 = 少而精**，不是数据堆砌
- **信息设计（Information Design）**，不是继续加字段
- Garmin 最大的问题：**数据太多，但不美**
- 重点是"什么数据放哪里"和"怎么展示高级"

### 三大核心模块

所有报表围绕三个核心模块构建：

| 模块 | 定位 | 包含指标 |
|------|------|---------|
| **AI Insights** | 智能解读，产品价值核心 | AI 生成的叙事文本 |
| **Recovery** | 身体恢复状态 | HRV / RHR / Sleep Score / Sleep Duration / Readiness / Recovery Time / Fatigue / Stress |
| **Efficiency** | 运动效率指标 | Cadence / Stride Length / Vertical Ratio / Ground Contact Time / HR Drift / Running Efficiency |

### 视觉参考

目标风格对标：
- **Apple Health** — 安静的高级感
- **WHOOP** — 数据密度 + 分析深度
- **Oura** — 极简 + 健康聚焦

---

## 一、报表类型总览

| 报表 | 定位 | 风格 | 核心情绪 | 尺寸 | 场景 |
|------|------|------|---------|------|------|
| **Morning Report** | 身体状态卡 | 极简 | Calm | 竖版手机卡 | 每日晨起 |
| **Daily Report** | 单日训练分析 | 数据感 | Focus | 标准海报 | 跑步后 |
| **Weekly Report** | 趋势与恢复 | 分析感 | Analysis | 标准海报 | 每周日 |
| **Monthly Report** | 成长总结 | 仪式感 | Achievement | 长海报 | 每月末 |
| **Race Report** | 高光时刻 | 电影感 | Epic | 长海报 | 比赛后 |

### 关键原则

> "所有报表都长一样"是很多产品最大的问题。

正确做法：每种报表有**独立的情绪定位**，形成产品层次感。

---

## 二、Morning Report（P0 — 最重要）

### 2.1 定位

- **传播性最强**的报表
- 小卡片，竖版，手机截图即分享
- 核心情绪：**Calm**（安静的高级感）
- **不要做成 dashboard**，要像 Apple Health / WHOOP / Oura
- "安静的高级感"

### 2.2 信息结构（从上到下）

#### 区域 1：顶部 — Morning Readiness Score

| 字段 | 类型 | 说明 |
|------|------|------|
| Readiness Score | 大数字，居中 | 0-100 分，视觉重心 |
| Status Text | 文字，居中 | "Ready for Quality Training" 或类似状态描述 |
| Score Level | 颜色编码 | 绿色(优) / 黄色(一般) / 红色(需休息) |

**设计要求**：
- 大数字是整个卡片的视觉锚点
- 状态描述用英文，简洁有力
- 不要加多余装饰

#### 区域 2：中间 — 核心四指标

**左列：Recovery**

| 字段 | 单位 | 说明 |
|------|------|------|
| HRV | ms | 心率变异性，昨夜值 |
| Resting HR | bpm | 静息心率 |
| Recovery Time | h | 恢复时间（小时） |
| Fatigue | 级别 | 疲劳程度（低/中/高） |

**右列：Sleep**

| 字段 | 单位 | 说明 |
|------|------|------|
| Sleep Score | 0-100 | 睡眠评分 |
| Sleep Duration | h:mm | 睡眠时长 |
| Stress | 级别 | 压力水平（可选） |

**设计要求**：
- 左右两列对称布局
- 每个指标一行：标签 + 数值
- 不要用图表，纯文字 + 数字
- 留白充足

#### 区域 3：AI Insight（核心）

| 字段 | 类型 | 说明 |
|------|------|------|
| AI Insight Text | 1 段话 | 智能解读，基于当日数据生成 |

**AI Insight 内容要求**：
- 必须**个性化**，不能是模板文本
- 必须**有行动指导**，不只是描述
- 必须**关联数据**，提到具体指标

**示例**：
- "睡眠恢复良好，HRV 高于基线 9%，今天适合进行节奏跑或爬坡训练。"
- "最近训练负荷较高，建议今天以恢复跑为主。"
- "HRV 连续 3 天下降，建议今天休息或进行极轻量活动。"

**设计要求**：
- 引用块样式：左侧竖线 + 浅色背景
- 字体略小于正文，但清晰可读

#### 区域 4：底部 — Today's Suggestion

| 字段 | 说明 |
|------|------|
| Recommended Training | 训练类型（轻松跑/节奏跑/间歇跑/休息） |
| Suggested Duration | 建议时长（如 "45 min"） |
| Suggested Intensity | 建议强度（如 "Z2" / "Z3-Z4" / "Rest"） |

**设计要求**：
- 三行简洁文字
- 不要加图表或进度条
- 收尾干净

### 2.3 视觉规范

| 维度 | 规范 |
|------|------|
| 背景色 | `#FFFFFF` 纯白（不是米色） |
| 比例 | 竖版 9:16 或 3:4 |
| 留白 | 最重要的设计元素 |
| 字体 | 大号数字 + 小号说明 |
| 颜色 | 只用状态色（绿/黄/红）+ 中性色 |
| 图表 | **无图表**，纯文字 + 数字 |
| 分享 | 手机截图即分享 |

### 2.4 数据点清单

| # | 数据点 | 来源 | 必需 |
|---|--------|------|------|
| 1 | Readiness Score (0-100) | training_readiness API | 是 |
| 2 | Readiness Level (优/一般/需休息) | 计算 | 是 |
| 3 | HRV Last Night (ms) | hrv_data API | 是 |
| 4 | Resting HR (bpm) | rhr_day API | 是 |
| 5 | Sleep Score (0-100) | sleep_data API | 是 |
| 6 | Sleep Duration (h:mm) | sleep_data API | 是 |
| 7 | Recovery Time (h) | 计算 | 是 |
| 8 | Fatigue Level (低/中/高) | 计算 | 是 |
| 9 | Stress Level (可选) | stress API | 否 |
| 10 | AI Insight Text | LLM 生成 | 是 |
| 11 | Training Type Suggestion | 计算 | 是 |
| 12 | Duration Suggestion | 计算 | 是 |
| 13 | Intensity Suggestion | 计算 | 是 |

**总计: 13 个数据点（12 必需 + 1 可选）**

---

## 三、Daily Report（P1）

### 3.1 定位

- 单次训练的深度分析
- 核心情绪：**Focus**（专注）
- 重点不是"统计"，而是**"今天跑得怎么样"**
- **训练表现必须和恢复关联**
- 这是区别于普通 App 的地方

### 3.2 信息结构（从上到下）

#### 区域 1：Header — 训练标题

| 字段 | 说明 |
|------|------|
| Training Title | 训练名称（如 "Evening Mountain Tempo"） |
| Date | 日期 |
| Location | 地点（可选） |
| Weather | 天气（可选） |

**设计要求**：
- 标题大字，副标题小字
- 日期/地点/天气一行排列

#### 区域 2：Hero Data — 四大核心数字

| 字段 | 单位 | 说明 |
|------|------|------|
| Distance | km | 跑步距离 |
| Duration | H:MM:SS | 运动时长 |
| Pace | min/km | 平均配速 |
| Elevation | m | 累计爬升 |

**设计要求**：
- 四个数字**大号显示**，占视觉重心
- 每个数字下方有小号标签
- 横向排列，间距均匀

#### 区域 3：Recovery + Efficiency 双模块（左右布局）

**左列：Recovery 模块**

| 字段 | 单位 | 说明 |
|------|------|------|
| Readiness | 0-100 | 身体准备度 |
| HRV | ms | 心率变异性 |
| Sleep Score | 0-100 | 睡眠评分 |
| Recovery Time | h | 恢复时间 |

**右列：Efficiency 模块（核心高级感）**

| 字段 | 单位 | 说明 |
|------|------|------|
| Cadence | spm | 步频 |
| Stride Length | m | 步幅 |
| Ground Contact Time | ms | 触地时间 |
| Vertical Ratio | % | 垂直比 |
| HR Drift | % | 心率漂移 |

**设计要求**：
- 左右两列**等宽对称**
- Efficiency 模块用**特殊卡片样式**突出（区别于普通 App）
- 每个指标一行：标签 + 数值
- Recovery 和 Efficiency 之间有明确分隔

#### 区域 4：Pace Split Chart

| 图表类型 | 说明 |
|---------|------|
| 配速拆分图 | 每公里配速柱状图 + 心率折线叠加 |

**图表要求**：
- X 轴：每公里标记（1km, 2km, ...）
- 左 Y 轴：配速（min/km，倒序，最快在上）
- 右 Y 轴：心率（bpm）
- 平均配速虚线参考线
- 最快/最慢公里高亮
- 心率折线用红色

#### 区域 5：AI Insight

| 字段 | 类型 | 说明 |
|------|------|------|
| AI Insight Text | 1-2 段话 | 这次训练的智能解读 |

**AI Insight 内容要求**：
- 分析**配速变化**（前半程 vs 后半程）
- 分析**心率效率**（HR Drift 方向）
- 分析**爬坡表现**（如有）
- 给出**改进建议**

**示例**：
- "后半程心率漂移明显下降，说明有氧效率正在提升。爬坡段配速稳定性较上周提升。"
- "前 3km 配速偏快，导致后半程明显掉速。建议前半程控制在 Z2 区间。"

**设计要求**：
- 引用块样式：左侧竖线 + 浅色背景

#### 区域 6：Trend Comparison

| 对比维度 | 时间范围 | 说明 |
|---------|---------|------|
| Pace | vs Last 7 Days | 配速变化百分比 |
| Efficiency | vs Last 7 Days | 效率变化百分比 |
| Pace | vs Last 30 Days | 配速变化百分比 |
| Efficiency | vs Last 30 Days | 效率变化百分比 |

**设计要求**：
- 左右两列：7天 vs 30天
- 每列 2-3 个指标
- 用箭头 + 百分比（↑ 3% / ↓ 2%）
- 绿色表示进步，红色表示退步

### 3.3 视觉规范

| 维度 | 规范 |
|------|------|
| 背景色 | `#FAF7F2` 米色（延续现有） |
| 比例 | 标准 3:4 或 4:5 |
| Hero Data | 四个数字大号，视觉重心 |
| Efficiency | 特殊卡片样式 |
| AI Insight | 引用块样式 |
| Trend | 箭头 + 百分比 |

### 3.4 数据点清单

| # | 数据点 | 来源 | 必需 |
|---|--------|------|------|
| 1 | Activity Name | activities API | 是 |
| 2 | Date | activities API | 是 |
| 3 | Location | activities API | 否 |
| 4 | Weather | 外部 API | 否 |
| 5 | Distance (km) | activities API | 是 |
| 6 | Duration (H:MM:SS) | activities API | 是 |
| 7 | Pace (min/km) | activities API | 是 |
| 8 | Elevation (m) | activities API | 是 |
| 9 | Readiness Score | training_readiness API | 是 |
| 10 | HRV (ms) | hrv_data API | 是 |
| 11 | Sleep Score | sleep_data API | 是 |
| 12 | Recovery Time (h) | 计算 | 是 |
| 13 | Cadence (spm) | activity detail API | 是 |
| 14 | Stride Length (m) | activity detail API | 是 |
| 15 | Ground Contact Time (ms) | activity detail API | 是 |
| 16 | Vertical Ratio (%) | activity detail API | 是 |
| 17 | HR Drift (%) | 计算（需要算法） | 是 |
| 18 | Splits[] (per-km) | activity splits API | 是 |
| 19 | HR Zones[] | activity HR zones API | 是 |
| 20 | AI Insight Text | LLM 生成 | 是 |
| 21 | vs 7d Pace Change (%) | 计算 | 是 |
| 22 | vs 7d Efficiency Change (%) | 计算 | 是 |
| 23 | vs 30d Pace Change (%) | 计算 | 是 |
| 24 | vs 30d Efficiency Change (%) | 计算 | 是 |

**总计: 24 个数据点（20 必需 + 4 可选）**

---

## 四、Weekly Report（P2）

### 4.1 定位

- 周度趋势分析
- 核心情绪：**Analysis**（分析感）
- 核心是**累积疲劳**和**恢复质量**
- 不要太"海报"，要有**分析深度**

### 4.2 信息结构（从上到下）

#### 区域 1：Header

| 字段 | 说明 |
|------|------|
| Title | "Weekly Training Report" |
| Date Range | "2026-05-18 ~ 2026-05-24" |

#### 区域 2：Weekly Load — 本周总量

| 字段 | 单位 | 说明 |
|------|------|------|
| Total Distance | km | 本周总跑量 |
| Total Duration | H:MM:SS | 本周总时长 |
| Total Elevation | m | 本周累计爬升 |
| Total Calories | kcal | 本周消耗热量 |

**设计要求**：
- 四个数字横向排列
- 每个数字下方有小号标签
- 视觉上比 Daily 的 Hero Data 略小

#### 区域 3：Recovery Trend + Efficiency Trend（左右布局）

**左列：Recovery Trend**

| 字段 | 说明 |
|------|------|
| HRV Trend | 7天 HRV 变化（趋势方向 + 数值） |
| RHR Trend | 7天静息心率变化 |
| Sleep Trend | 7天睡眠评分变化 |
| Trend Direction | improving / stable / declining |
| 迷你趋势图 | sparkline 风格 |

**右列：Efficiency Trend**

| 字段 | 说明 |
|------|------|
| Pace vs HR | 配速/心率比变化 |
| Cadence Trend | 步频趋势 |
| Running Efficiency | 跑步效率变化 |
| 迷你趋势图 | sparkline 风格 |

**设计要求**：
- 左右两列**等宽对称**
- 每个趋势一行：标签 + 数值 + 方向箭头
- 下方各一个迷你折线图（sparkline）
- 趋势方向用颜色编码（绿=进步，红=退步）

#### 区域 4：Daily Distance Overview

| 图表类型 | 说明 |
|---------|------|
| 7天跑量柱状图 | 每日距离柱状 + 爬升折线叠加 |

**图表要求**：
- X 轴：周一到周日
- 左 Y 轴：距离（km）
- 右 Y 轴：爬升（m）
- 零跑量日用浅灰色
- 最高跑量日高亮

#### 区域 5：AI Coach Summary（核心）

| 字段 | 类型 | 说明 |
|------|------|------|
| AI Coach Text | 1-2 段话 | 教练级总结 + 下周建议 |

**AI Coach 内容要求**：
- 总结**本周训练质量**
- 分析**恢复状态**
- 评估**训练负荷**
- 给出**下周建议**

**示例**：
- "本周整体恢复稳定，但高强度训练占比偏高。建议下周增加 Z2 跑比例以改善恢复质量。"
- "本周跑量较上周增加 15%，但 HRV 下降 8%。建议下周降低强度，优先恢复。"

**设计要求**：
- **特殊样式**突出（区别于其他模块）
- 引用块 + 背景色

#### 区域 6：Risk Alert

| 字段 | 类型 | 说明 |
|------|------|------|
| Risk Alerts | 0-N 条 | 风险预警 |

**风险检测规则**：
- Acute Load 连续 N 天高于推荐范围
- HRV 连续下降
- 睡眠质量持续低于基线
- 训练强度分布异常

**示例**：
- "Acute Load 已连续 5 天高于推荐范围。"
- "HRV 连续 3 天下降，建议减少训练强度。"

**设计要求**：
- 警告色（红色/橙色）背景
- 只在有风险时显示，无风险则隐藏

#### 区域 7：Training Distribution + vs Last Week

**左列：Training Distribution**

| 字段 | 说明 |
|------|------|
| Z1 % | 恢复区间占比 |
| Z2 % | 有氧区间占比 |
| Z3 % | 节奏区间占比 |
| Z4 % | 阈值区间占比 |
| Z5 % | 无氧区间占比 |

**右列：vs Last Week**

| 字段 | 说明 |
|------|------|
| Distance Change | 跑量变化 |
| Load Change | 负荷变化 |
| Recovery Change | 恢复变化 |

**设计要求**：
- 左列用水平条形图或百分比数字
- 右列用箭头 + 百分比

### 4.3 视觉规范

| 维度 | 规范 |
|------|------|
| 背景色 | `#FAF7F2` 米色 |
| 比例 | 标准 3:4 |
| Recovery/Efficiency | 左右对比布局 |
| 趋势 | 迷你折线图（sparkline） |
| AI Coach | 特殊样式突出 |
| Risk Alert | 警告色 |

### 4.4 数据点清单

| # | 数据点 | 来源 | 必需 |
|---|--------|------|------|
| 1 | Week Start Date | 计算 | 是 |
| 2 | Week End Date | 计算 | 是 |
| 3 | Total Distance (km) | activities API | 是 |
| 4 | Total Duration (H:MM:SS) | activities API | 是 |
| 5 | Total Elevation (m) | activities API | 是 |
| 6 | Total Calories (kcal) | activities API | 是 |
| 7 | HRV Daily[7] (ms) | hrv_data API | 是 |
| 8 | RHR Daily[7] (bpm) | rhr_day API | 是 |
| 9 | Sleep Daily[7] (score) | sleep_data API | 是 |
| 10 | Recovery Trend Direction | 计算 | 是 |
| 11 | Pace vs HR Change (%) | 计算 | 是 |
| 12 | Cadence Trend[7] (spm) | activity detail API | 是 |
| 13 | Efficiency Score Change (%) | 计算 | 是 |
| 14 | Daily Breakdown[7] | activities API | 是 |
| 15 | AI Coach Summary Text | LLM 生成 | 是 |
| 16 | Risk Alerts[] (0-N) | 计算 | 是 |
| 17 | Z1-Z5 Distribution (%) | activity HR zones API | 是 |
| 18 | vs Last Week Distance (%) | 计算 | 是 |
| 19 | vs Last Week Load (%) | 计算 | 是 |
| 20 | vs Last Week Recovery (%) | 计算 | 是 |

**总计: 20 个数据点（全部必需）**

---

## 五、Monthly Report（P3）

### 5.1 定位

- 月度成长叙事
- 核心情绪：**Achievement**（仪式感）
- 重要的是**成长感**，不是统计感
- 需要 **Narrative（叙事感）**

### 5.2 信息结构（从上到下）

#### 区域 1：Opening Hero（大视觉）

| 字段 | 说明 |
|------|------|
| Hero Image | 大图（山脊/长距离/赛事/高光瞬间） |
| Title | "APRIL RECAP" |
| Year | "2026" |

**设计要求**：
- **必须有大图**，全宽显示
- 文字叠加在图片上
- 视觉冲击力最强
- 如果没有图片，用纯色背景 + 大字标题

#### 区域 2：Achievement — 核心成就（先放成就，不是跑量）

| 字段 | 说明 |
|------|------|
| Achievement 1 | 如 "Highest Weekly Load: 127 km" |
| Achievement 2 | 如 "New Climbing PB: 3,290m" |
| Achievement 3 | 如 "Longest Trail Run: 27.94 km" |

**设计要求**：
- **放在 Training Overview 之前**
- 每个成就一行
- 用图标/徽章样式
- 成就要**具体**，有数字

#### 区域 3：Training Overview — 训练总量

| 字段 | 单位 | 说明 |
|------|------|------|
| Total Distance | km | 月度总跑量 |
| Total Duration | H:MM:SS | 月度总时长 |
| Total Elevation | m | 月度累计爬升 |
| Training Days | 天 | 运动天数 |

**设计要求**：
- 四个数字横向排列
- 比 Achievement 区域略小

#### 区域 4：Recovery Summary + Efficiency Growth（左右布局）

**左列：Recovery Summary**

| 字段 | 说明 |
|------|------|
| Avg HRV | 月度平均 HRV |
| Sleep Consistency | 睡眠一致性（%） |
| Recovery Stability | 恢复稳定性（stable/volatile） |

**右列：Efficiency Growth**

| 字段 | 说明 |
|------|------|
| Aerobic Efficiency Change | 有氧效率变化（如 "+7%"） |
| Cadence Stability Change | 步频稳定性变化（如 "+4%"） |
| HR Drift Change | 心率漂移变化（如 "-6%"） |
| 趋势图 | 效率指标月度趋势 |

**设计要求**：
- 左右两列**等宽对称**
- Growth 用**箭头 + 百分比**
- 绿色表示进步，红色表示退步

#### 区域 5：Weekly Trend

| 图表类型 | 说明 |
|---------|------|
| 4周跑量趋势图 | 每周距离柱状 + 爬升折线叠加 |

**图表要求**：
- X 轴：第1周 ~ 第4周
- 左 Y 轴：距离（km）
- 右 Y 轴：爬升（m）

#### 区域 6：AI Monthly Narrative（最重要）

| 字段 | 类型 | 说明 |
|------|------|------|
| AI Narrative Text | 2-3 段话 | 月度成长叙事 |

**AI Narrative 内容要求**：
- 总结**训练稳定性**
- 分析**恢复状态**
- 评估**效率变化**
- 展望**下月方向**
- 用**叙事性语言**，不是数据罗列

**示例**：
- "本月训练稳定性明显提升，长距离耐力增强。恢复状态整体良好，但高强度训练后恢复时间偏长。建议下月在保持跑量的同时，增加恢复训练的比例。"

**设计要求**：
- **特殊样式**，像杂志编辑推荐
- 引用块 + 背景色 + 左侧竖线

#### 区域 7：Personal Best

| 字段 | 说明 |
|------|------|
| 5K PB | 时间 + 日期 |
| 10K PB | 时间 + 日期 |
| Half Marathon PB | 时间 + 日期 |
| Full Marathon PB | 时间 + 日期 |
| Trail PB | 时间 + 日期（如有） |

**设计要求**：
- 用**奖牌/徽章**样式（金银铜色圆形）
- 每个 PB 一行
- 显示时间和日期

#### 区域 8：Next Month Goal

| 字段 | 说明 |
|------|------|
| Goal 1 | 如 "月跑量 450-500 km" |
| Goal 2 | 如 "加强速度与阈值训练" |
| Goal 3 | 如 "提升高距离耐力" |

**设计要求**：
- 3-4 行文字
- 简洁有力
- 收尾干净

### 5.3 视觉规范

| 维度 | 规范 |
|------|------|
| 背景色 | `#F5F0EB` 浅米色（略深，仪式感） |
| 比例 | 长海报 2:5 或 1:3 |
| Hero | **必须有大图** |
| Achievement | 放在 Training Overview **之前** |
| AI Narrative | 杂志编辑推荐样式 |
| PB Records | 奖牌/徽章样式 |

### 5.4 数据点清单

| # | 数据点 | 来源 | 必需 |
|---|--------|------|------|
| 1 | Month Label | 计算 | 是 |
| 2 | Hero Image Path | 图片管理 | 否 |
| 3 | Achievement 1 Text | 计算 | 是 |
| 4 | Achievement 2 Text | 计算 | 是 |
| 5 | Achievement 3 Text | 计算 | 是 |
| 6 | Total Distance (km) | activities API | 是 |
| 7 | Total Duration (H:MM:SS) | activities API | 是 |
| 8 | Total Elevation (m) | activities API | 是 |
| 9 | Training Days | activities API | 是 |
| 10 | Avg HRV (ms) | hrv_data API | 是 |
| 11 | Sleep Consistency (%) | sleep_data API | 是 |
| 12 | Recovery Stability | 计算 | 是 |
| 13 | Aerobic Efficiency Change (%) | 计算 | 是 |
| 14 | Cadence Stability Change (%) | 计算 | 是 |
| 15 | HR Drift Change (%) | 计算 | 是 |
| 16 | Weekly Trend[4] | activities API | 是 |
| 17 | AI Narrative Text | LLM 生成 | 是 |
| 18 | PB 5K (time + date) | activities API | 是 |
| 19 | PB 10K (time + date) | activities API | 是 |
| 20 | PB Half (time + date) | activities API | 是 |
| 21 | PB Full (time + date) | activities API | 是 |
| 22 | PB Trail (time + date) | activities API | 否 |
| 23 | Next Month Goal 1 | 用户输入 | 是 |
| 24 | Next Month Goal 2 | 用户输入 | 是 |
| 25 | Next Month Goal 3 | 用户输入 | 是 |

**总计: 25 个数据点（24 必需 + 1 可选）**

---

## 六、Race Report（P4）

### 6.1 定位

- 赛事高光复盘
- 核心情绪：**Epic**（电影感）
- 最容易在社交媒体传播
- 需要**叙事弧线**
- **最容易出圈**

### 6.2 信息结构（从上到下）

#### 区域 1：Hero — 赛事照片 + 核心数据

| 字段 | 说明 |
|------|------|
| Race Photo | 赛事照片（全宽） |
| Race Name | 赛事名称 |
| Distance | 距离 |
| Elevation | 爬升 |
| Finish Time | 完赛时间 |

**设计要求**：
- **必须有赛事照片**
- 文字叠加在图片上
- 视觉冲击力最强
- 整体风格像**运动品牌广告**

#### 区域 2：Split Analysis

| 字段 | 说明 |
|------|------|
| First Half | 前半程时间 |
| Second Half | 后半程时间 |
| Climbing Section | 爬升段数据 |
| Downhill Section | 下坡段数据 |

**设计要求**：
- 横向排列：前半 vs 后半
- 爬升段 vs 下坡段

#### 区域 3：Charts — 配速 + 心率

| 图表类型 | 说明 |
|---------|------|
| Pace Split Chart | 配速拆分图 |
| HR Zone Donut | 心率区间分布 |

**设计要求**：
- 左右并排
- 配速图用**渐变色**表示强度

#### 区域 4：Critical Moment

| 字段 | 类型 | 说明 |
|------|------|------|
| Critical Moment Text | 1 段话 | AI 生成的关键时刻分析 |

**示例**：
- "32km 后出现明显配速下降，但爬坡段表现依旧稳定。"

**设计要求**：
- 引用块样式
- 突出显示

#### 区域 5：Race Intelligence

| 字段 | 说明 |
|------|------|
| Fuel Timing | 补给策略（如 "每 45min 补给一次"） |
| HR Collapse | 心率崩塌情况 |
| Climbing Efficiency | 爬坡效率（如 "128m/km"） |
| Downhill Control | 下坡控制（如 "配速稳定"） |

**设计要求**：
- 四个维度，2x2 布局
- 每个维度一行

#### 区域 6：Finish Narrative

| 字段 | 类型 | 说明 |
|------|------|------|
| Narrative Text | 1-2 段话 | AI 生成的赛事叙事 |
| Quote | 可选名言 | 收尾名言 |

**示例**：
- "这是一次节奏控制非常成熟的比赛。尽管后半程出现疲劳，但爬坡段表现依旧稳定。"
- 名言："不是终点有多远，而是自己能走多远。"

**设计要求**：
- **杂志引用**样式
- 可加名言收尾
- 叙事弧线完整

### 6.3 视觉规范

| 维度 | 规范 |
|------|------|
| 背景色 | `#1A1A1A` 深色（电影感、冲击力） |
| 比例 | 长海报 2:5 |
| Hero | **必须有赛事照片** |
| 风格 | **运动品牌广告** |
| 配速图 | **渐变色**表示强度 |
| Finish Narrative | **杂志引用**样式 |
| 文字颜色 | 白色/浅色（深色背景） |

### 6.4 数据点清单

| # | 数据点 | 来源 | 必需 |
|---|--------|------|------|
| 1 | Race Name | activities API | 是 |
| 2 | Race Date | activities API | 是 |
| 3 | Race Photo Path | 图片管理 | 否 |
| 4 | Distance (km) | activities API | 是 |
| 5 | Elevation (m) | activities API | 是 |
| 6 | Finish Time (H:MM:SS) | activities API | 是 |
| 7 | First Half Time | 计算 | 是 |
| 8 | Second Half Time | 计算 | 是 |
| 9 | Climbing Section Data | 计算 | 是 |
| 10 | Downhill Section Data | 计算 | 是 |
| 11 | Splits[] (per-km) | activity splits API | 是 |
| 12 | HR Zones[] | activity HR zones API | 是 |
| 13 | Critical Moment Text | LLM 生成 | 是 |
| 14 | Fuel Timing | 计算 | 是 |
| 15 | HR Collapse | 计算 | 是 |
| 16 | Climbing Efficiency | 计算 | 是 |
| 17 | Downhill Control | 计算 | 是 |
| 18 | Finish Narrative Text | LLM 生成 | 是 |
| 19 | Quote | 用户输入 | 否 |

**总计: 19 个数据点（17 必需 + 2 可选）**

---

## 七、信息密度对比

| 报表 | 数据点 | 图表 | 文字段落 | 密度 | 情绪 |
|------|--------|------|---------|------|------|
| Morning | 13 | 0 | 2-3 | ★☆☆☆☆ 极简 | Calm |
| Daily | 24 | 1 | 3-4 | ★★★☆☆ 适中 | Focus |
| Weekly | 20 | 3-4 | 2-3 | ★★★★☆ 较高 | Analysis |
| Monthly | 25 | 2-3 | 3-4 | ★★★★☆ 较高 | Achievement |
| Race | 19 | 2 | 3-4 | ★★☆☆☆ 精炼 | Epic |

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

## 八、三大核心模块分布矩阵

### Recovery 模块在各报表中的呈现

| 报表 | Recovery 呈现方式 | 指标数量 |
|------|------------------|---------|
| Morning | **主角** — Readiness Score + HRV/RHR/Sleep 全量 | 7-8 个 |
| Daily | **配角** — 小模块，4 个指标 | 4 个 |
| Weekly | **趋势** — 7 天 HRV/RHR/Sleep 趋势图 | 3 趋势 + 图表 |
| Monthly | **总结** — 月度平均 + 一致性 | 3 个 |
| Race | **缺席** — 赛事报表不需要恢复数据 | 0 个 |

### Efficiency 模块在各报表中的呈现

| 报表 | Efficiency 呈现方式 | 指标数量 |
|------|-------------------|---------|
| Morning | **缺席** — 晨报不需要效率数据 | 0 个 |
| Daily | **核心** — Cadence/Stride/GCT/VO/HR Drift 全量 | 5 个 |
| Weekly | **趋势** — 效率指标周度变化 | 3 趋势 + 图表 |
| Monthly | **成长** — 效率指标月度增长百分比 | 3 个 |
| Race | **深度** — Climbing Efficiency/Downhill Control | 2 个 |

### AI Insights 模块在各报表中的呈现

| 报表 | AI Insight 呈现方式 | 文本长度 |
|------|-------------------|---------|
| Morning | **建议型** — 今天适合什么训练 | 1 段话 |
| Daily | **分析型** — 这次训练表现如何 | 1-2 段话 |
| Weekly | **教练型** — 本周总结 + 下周建议 | 1-2 段话 |
| Monthly | **叙事型** — 本月成长故事 | 2-3 段话 |
| Race | **评论型** — 赛事关键时刻解读 | 1-2 段话 + 名言 |

---

## 九、视觉差异化规范

### 背景色矩阵

| 报表 | 背景色 | HEX | 说明 |
|------|--------|-----|------|
| Morning | 纯白 | `#FFFFFF` | 安静、干净 |
| Daily | 米色 | `#FAF7F2` | 延续现有风格 |
| Weekly | 米色 | `#FAF7F2` | 延续现有风格 |
| Monthly | 浅米色 | `#F5F0EB` | 略深，仪式感 |
| Race | 深色 | `#1A1A1A` | 电影感、冲击力 |

### 字体层级矩阵

| 元素 | Morning | Daily | Weekly | Monthly | Race |
|------|---------|-------|--------|---------|------|
| 主标题 | 28pt | 24pt | 22pt | 28pt | 36pt |
| 副标题 | 16pt | 14pt | 14pt | 16pt | 18pt |
| 大数字 | 48pt | 36pt | 32pt | 36pt | 48pt |
| 正文 | 14pt | 12pt | 12pt | 12pt | 14pt |
| 说明文字 | 11pt | 10pt | 10pt | 10pt | 11pt |

### 特殊样式矩阵

| 样式 | 用于 | 效果 |
|------|------|------|
| 引用块 | AI Insight | 左侧竖线 + 浅色背景 |
| 状态色 | Recovery/Ready | 绿/黄/红 |
| 箭头 | Trend Comparison | ↑↓ + 百分比 |
| 进度条 | Goal Progress | 圆角矩形 + 渐变 |
| 警告块 | Risk Alert | 红色/橙色背景 |
| 奖牌 | PB Records | 金银铜色圆形 |
| 大图 | Monthly Hero / Race Hero | 全宽图片 + 叠加文字 |
| 渐变色 | Race Pace Chart | 强度渐变 |
| 杂志引用 | Finish Narrative | 特殊排版 |

---

## 十、AI Narrative 生成规范

### 10.1 各报表 AI Narrative 的输入数据

| 报表 | 输入数据 | 输出 |
|------|---------|------|
| Morning | HRV/RHR/Sleep/Readiness + 历史基线 | 建议型文本 |
| Daily | Activity splits/HR zones/Efficiency + 历史对比 | 分析型文本 |
| Weekly | Weekly load/Recovery trend/Efficiency trend | 教练型文本 |
| Monthly | Monthly stats/Efficiency growth/PB records | 叙事型文本 |
| Race | Race splits/HR zones/Intelligence | 评论型文本 |

### 10.2 AI Narrative 质量要求

- **个性化**：必须基于实际数据，不能是模板
- **有行动指导**：不只是描述，要给出建议
- **关联数据**：提到具体指标和数字
- **叙事性**：用故事性语言，不是数据罗列
- **简洁**：不超过 3 句话（Morning/Daily/Race）或 5 句话（Weekly/Monthly）

---

## 十一、数据需求汇总

### 所有报表的数据点总计

| 报表 | 必需 | 可选 | 总计 |
|------|------|------|------|
| Morning | 12 | 1 | 13 |
| Daily | 20 | 4 | 24 |
| Weekly | 20 | 0 | 20 |
| Monthly | 24 | 1 | 25 |
| Race | 17 | 2 | 19 |
| **总计** | **93** | **8** | **101** |

### 新增数据点（现有实现中不存在）

| 数据点 | 所需报表 | 说明 |
|--------|---------|------|
| HR Drift (%) | Daily, Monthly | 心率漂移，需要算法计算 |
| Running Efficiency | Weekly, Monthly | 跑步效率，需要算法计算 |
| Recovery Time (h) | Morning, Daily | 恢复时间，需要算法计算 |
| Fatigue Level | Morning | 疲劳程度，需要算法计算 |
| Sleep Consistency (%) | Monthly | 睡眠一致性，需要算法计算 |
| Recovery Stability | Monthly | 恢复稳定性，需要算法计算 |
| vs 7d/30d Comparison | Daily | 历史对比，需要数据聚合 |
| Risk Alerts[] | Weekly | 风险检测，需要规则引擎 |
| AI Narrative Text | All | AI 生成，需要 LLM 调用 |
