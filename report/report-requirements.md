# 佳明训练报表 — 需求与设计思路

> 来源：用户参考图分析，2026-05-20
> 最后更新：2026-05-22（Phase 8 架构升级 + Race Report）

---

## 一、报表逻辑体系

核心逻辑：**状态 → 行为 → 结果 → 目标** 闭环

```
身体状态（健康数据）
      ↓
训练行为（跑步/骑行/力量）
      ↓
训练结果（配速/心率/爬升/PB）
      ↓
目标对比（进度/建议/下阶段方向）
```

五种报表是这个闭环在不同时间粒度和场景上的切片：

| 报表 | 时间粒度 | 核心问题 | 风格 |
|------|---------|---------|------|
| Morning Report | 每日晨间 | 今天我的状态适合怎么练？ | Calm（安静高级感），手机竖版 |
| Daily Report | 单次训练 | 这次跑得怎么样？ | Focus（专注），标准海报 |
| Weekly Report | 7天 | 这周训练质量如何？ | Analysis（分析感），标准海报 |
| Monthly Report | 30天 | 这个月我成长了多少？ | 标准海报 |
| Race Report | 单次赛事 | 这场比赛表现如何？ | Epic（电影感），深色背景 |

---

## 二、架构设计（Phase 8 升级后）

```
D:/Garmin/garmin-agent/GarminAgent/scripts/report/
├── __init__.py
├── report_styles.py       # 统一样式：5 套配色/字体/尺寸/布局常量
├── data_aggregator.py     # 数据聚合：从 GarminClient 拉数据 + 按报表需求聚合
├── ai_narrator.py         # AI Narrative：规则引擎 + LLM 降级，统一文案生成
├── risk_detector.py       # 风险检测：HRV趋势/负荷/睡眠/恢复 四维预警
├── chart_renderer.py      # 图表渲染（旧版，保留兼容）
├── mock_data.py           # 模拟数据
│
├── morning_report.py      # Morning Report（手机竖版，Calm 风格）
├── daily_report.py        # Daily Report（标准海报，Focus 风格）
├── weekly_report_v2.py    # Weekly Report v2（标准海报，Analysis 风格）
├── monthly_report.py      # Monthly Report
├── race_report.py         # Race Report（深色背景，Epic 风格）
│
├── weekly_report.py       # [旧版] 周报 v1（保留兼容）
├── post_run_report.py     # [旧版] 跑后报表（保留兼容）
├── morning_call.py        # [旧版] Morning Call（保留兼容）
│
├── run_report.py          # CLI 入口
└── output/                # 生成的图表图片
```

### 架构分层

| 层 | 职责 | 模块 |
|---|------|------|
| 样式层 | 颜色/字体/尺寸/布局常量 | `report_styles.py` |
| 数据层 | API 调用 + 聚合计算 | `data_aggregator.py` |
| 文案层 | AI Narrative 生成（规则引擎 + LLM） | `ai_narrator.py` |
| 风控层 | 训练风险检测与预警 | `risk_detector.py` |
| 渲染层 | matplotlib 图表 + 报表布局 | `*_report.py` |

---

## 三、完整数据模块

### Morning Report（早间日报）— 手机竖版

**① Readiness Score（大数字）**
- 综合准备度评分（0-100）+ 颜色状态（绿/黄/橙/红）
- HRV 今日值 vs 7日均值（箭头趋势）

**② Recovery + Sleep 双列**
- 恢复状态：HRV / 静息心率 / 训练准备度
- 睡眠：总时长 / 深睡占比 / 睡眠评分

**③ AI Insight（引用块）**
- 基于健康数据的晨间建议（规则引擎生成）
- 降级策略：LLM 不可用时用模板文案

**④ Today's Suggestion**
- 今日训练建议：休息 / 轻松跑 / 正常训练 / 高强度
- 建议配速范围 + 时长

---

### Daily Report（单次训练复盘）— 标准海报

**① Header — 训练标题 + 日期/地点**

**② Hero Data — Distance / Duration / Pace / Elevation**
- 四大核心指标大数字展示

**③ Recovery + Efficiency 双模块**
- 恢复指标：HRV 变化、训练负荷
- 效率指标：HR Drift、步频评分、跑步效率

**④ Pace Split Chart**
- 每公里配速柱状图 + 平均配速参考线

**⑤ AI Insight**
- 单次训练分析（配速趋势/心率漂移/步频评价）

**⑥ Trend Comparison**
- 与历史同类型训练对比

---

### Weekly Report（周报）— 标准海报

**① Header — 周报标题 + 日期范围**

**② Weekly Load — 四大数字**
- 总跑量、总时长、训练天数、消耗热量

**③ Recovery Trend + Efficiency Trend（sparkline）**
- 7 天 HRV / 静息心率 / 睡眠趋势
- 跑步效率变化趋势

**④ Daily Distance 图表**
- 7 天柱状图 + 爬升折线

**⑤ AI Coach Summary**
- 教练级周总结（负荷/恢复/效率/风险综合评估）

**⑥ Risk Alert（条件显示）**
- HRV 连续下降 / 周跑量增幅过大 / 睡眠质量差 / 恢复状态下降
- 由 `RiskDetector` 检测，仅在发现风险时显示

**⑦ Training Distribution + vs Last Week**
- 训练类型分布 + 周对比数据

---

### Monthly Report（月报）

**① Hero 区** — 月份标题 + 主题一句话

**② 5大核心指标** — 月跑量/运动时间/累计爬升/消耗热量/运动天数

**③ 月度每日总览图** — 每日跑量柱状 + 爬升折线

**④ 高光时刻** — 本月最佳单次活动

**⑤ 训练强度分布** — Z1–Z5 环形图

**⑥ 周跑量趋势** — 4–5 周柱状图

**⑦ 跑步专项进步趋势** — 月内配速/心率趋势

**⑧ 个人最佳 PB** — 5K/10K/半马/全马

**⑨ 健康月度报告** — 月均 HRV/RHR/睡眠 vs 上月

**⑩ 骑行 & 力量月汇总**

**⑪ 月度总结** — 亮点 3–4 条（AI 生成）

**⑫ 下月目标** — 跑量/训练次数/专项目标

---

### Race Report（赛事报表）— 深色背景

**① Hero — 赛事名称 + 核心数据**
- 深色背景 + 金色强调色，电影感冲击力
- 完赛时间 / 距离 / 平均配速 / 平均心率

**② Split Analysis — 前半 vs 后半 + 爬升/下坡**
- 前半程 vs 后半程用时对比
- 爬升段 / 下坡段效率分析

**③ Charts — 配速拆分 + 心率区间**
- 每公里配速柱状图 + 心率叠加
- Z1–Z5 心率区间环形图

**④ Critical Moment — 关键时刻**
- 配速变化最大的公里标注
- 爬坡段 / 冲刺段表现

**⑤ Race Intelligence — 四维分析**
- 爬坡效率 / 心率稳定性 / 配速策略 / 节奏控制

**⑥ Finish Narrative — 完赛叙事 + 名言**
- AI 生成的赛事叙事文本

---

## 四、支撑模块详细设计

### report_styles.py — 统一样式系统

**5 套配色方案：**
| 配色 | 适用报表 | 背景色 | 强调色 |
|------|---------|--------|--------|
| MORNING_COLORS | Morning Report | #FFFFFF 白色 | #E8A87C 暖橙 |
| DAILY_COLORS | Daily Report | #FAF7F2 米色 | #E8A87C 暖橙 |
| WEEKLY_COLORS | Weekly Report | #FAF7F2 米色 | #E8A87C 暖橙 |
| MONTHLY_COLORS | Monthly Report | #F5F0EB 浅米 | #E8A87C 暖橙 |
| RACE_COLORS | Race Report | #1A1A1A 深色 | #FFD700 金色 |

**字体层级：** title / subtitle / hero / body / caption 五级

**布局常量：** 卡片圆角、内边距、模块间距、进度条高度等

**辅助函数：** `readiness_color()` 状态色、`trend_color()` 趋势色

---

### ai_narrator.py — AI Narrative 生成器

**四种叙事风格：**
| 方法 | 用途 | 风格 |
|------|------|------|
| `generate_morning_insight()` | 晨间建议 | 建议型 |
| `generate_daily_insight()` | 单次训练分析 | 分析型 |
| `generate_weekly_coach()` | 周总结 | 教练型 |
| `generate_monthly_narrative()` | 月度成长 | 叙事型 |

**赛事叙事：**
| 方法 | 用途 |
|------|------|
| `generate_race_commentary()` | 赛事评论 |
| `generate_critical_moment()` | 关键时刻分析 |
| `generate_finish_narrative()` | 完赛叙事 |

**降级策略：** LLM 不可用时用规则引擎模板生成文案

---

### risk_detector.py — 风险检测引擎

**四维检测：**
| 检测项 | 阈值 | 触发条件 |
|--------|------|---------|
| HRV 趋势 | 连续下降 3 天 / 较基线降 10% | 训练过度 / 恢复不足 |
| 训练负荷 | 周跑量增幅 > 20% | 增量过大，建议控制 10-15% |
| 睡眠质量 | 评分 < 60 持续 3 天 | 影响恢复质量 |
| 恢复状态 | 趋势持续下降 | 建议安排主动恢复 |

**输出：** 预警列表，仅在 Weekly Report 中条件显示

---

## 五、CLI 入口

```bash
python run_report.py morning               # Morning Report（手机竖版）
python run_report.py daily                  # Daily Report（最新活动）
python run_report.py daily --activity-id ID # Daily Report（指定活动）
python run_report.py weekly                 # Weekly Report（本周）
python run_report.py weekly --weeks-ago 1   # Weekly Report（上周）
python run_report.py monthly                # Monthly Report（本月）
python run_report.py monthly --months-ago 1 # Monthly Report（上月）
python run_report.py race                   # Race Report（最新赛事）
python run_report.py race --activity-id ID  # Race Report（指定赛事）
python run_report.py all                    # 生成全部 5 种报表
```

默认使用 mock 数据，加 `--no-mock` 使用真实 Garmin 数据。

---

## 六、待定决策

| 问题 | 选项 | 当前状态 |
|------|------|---------|
| AI 文字部分怎么处理？ | 规则引擎 / LLM 动态生成 | ✅ 规则引擎 + LLM 降级 |
| 图表风格 | 配色方案 | ✅ 5 套配色，每种报表独立 |
| 数据来源 | mock / 真实 API | ✅ 双模式支持 |
| 报表数量 | 4 种 / 5 种 | ✅ 5 种（新增 Race Report） |
