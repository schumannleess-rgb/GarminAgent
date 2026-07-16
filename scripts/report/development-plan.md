# 佳明训练报表 — 开发计划

> 创建时间：2026-05-20
> 最后更新：2026-05-22（Phase 8 架构升级 + Race Report）
> 状态：Phase 1-8 全部完成

---

## 一、需求复述

用 Garmin Agent 已有的 API 能力，生成 5 种训练报表（Morning/Daily/Weekly/Monthly/Race），核心逻辑是「状态 → 行为 → 结果 → 目标」闭环。

**数据来源**：GarminClient 的活动 API + 健康 API，已有完整实现。
**输出形式**：matplotlib 生成静态图片，可发送到飞书。
**开发策略**：先 mock 数据跑通 UI，再对接真实 API。

---

## 二、架构设计

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
├── run_report.py          # CLI 入口（支持 6 种命令）
└── output/                # 生成的图表图片
```

### 架构分层（Phase 8 升级）

| 层 | 职责 | 模块 |
|---|------|------|
| 样式层 | 颜色/字体/尺寸/布局常量 | `report_styles.py` |
| 数据层 | API 调用 + 聚合计算 | `data_aggregator.py` |
| 文案层 | AI Narrative 生成（规则引擎 + LLM） | `ai_narrator.py` |
| 风控层 | 训练风险检测与预警 | `risk_detector.py` |
| 渲染层 | matplotlib 图表 + 报表布局 | `*_report.py` |

---

## 三、数据映射（需求 → API）

| 报表模块 | 数据字段 | API 来源 | CLI 命令 |
|---------|---------|---------|---------|
| 活动概览 | distance, duration, avgSpeed, avgHR, calories, elevationGain | get_activities | week/latest |
| 配速拆分 | lapDTOs[].averageSpeed, averageHR | get_activity_splits | splits |
| 心率区间 | zoneNumber, secsInZone | get_activity_hr_in_timezones | detail |
| 跑步动态 | avgStrideLength, avgGroundContactTime, avgVerticalOscillation, averageRunningCadence | activities 表字段 | detail |
| 海拔剖面 | lapDTOs[].elevationGain, elevationLoss | get_activity_splits | splits |
| HRV | hrvSummary.lastNightAvg | get_hrv_data | hrv |
| 睡眠 | sleepScores.overall.value, sleepTimeSeconds, deepSleepSeconds | get_sleep_data | sleep |
| 训练状态 | trainingStatusDTO | get_training_status | status |
| 训练准备度 | trainingReadinessValue, trainingReadinessLevel | get_training_readiness | health |
| 活动分类 | type, reason | classifier.py | classify |
| VO2Max | vO2MaxValue | get_training_status | status |
| 比赛预测 | 5K/10K/半马/全马 | get_race_predictions | capacity |

---

## 四、开发阶段

### Phase 1：数据聚合 + mock 数据 ✅
- [x] 创建 scripts/report/ 目录结构
- [x] mock_data.py：基于真实样例值生成模拟数据
- [x] data_aggregator.py：从 GarminClient 拉数据 + 聚合计算
- [x] 测试：mock 数据验证聚合逻辑

### Phase 2：图表渲染 ✅
- [x] chart_renderer.py：配速柱状图、心率区间环形图、周跑量趋势图、健康趋势、训练类型环形图、月度趋势
- [x] 配色方案：米色系（参考图风格）
- [x] 测试：6 张图表全部生成成功

### Phase 3：周报模板（第一个原型）✅
- [x] weekly_report.py：8 个模块完整实现（标题、概览卡片、每日跑量、训练类型、心率区间、健康趋势、高光+对比+进度）
- [x] run_report.py CLI 入口（支持 weekly/post/morning/monthly/all）
- [x] 端到端测试：mock 数据 → 图表 → 完整周报图片（weekly_report.png 345KB）

### Phase 4：对接真实数据 ✅
- [x] 替换 mock 为 GarminClient 真实调用（_get_week_health 用 get_hrv_data/get_sleep_data/get_rhr_day/get_training_readiness）
- [x] 修复 _calc_hr_zones_week 真实模式硬编码 mock 的 bug
- [x] 修复 _calc_daily_breakdown 天数计算 bug（上周数据算出 10 天而非 7 天）
- [x] 真实数据端到端测试通过（上周周报：12.6km / 3天 / 心率区间 Z1:12% Z2:29% Z3:59%）
- [x] 健康趋势图数据提取路径修复（HRV: hrvSummary.lastNightAvg, RHR: allMetrics.metricsMap, sleep: dailySleepDTO.sleepScores）

### Phase 5：跑后报表 ✅
- [x] post_run_report.py：8 个模块（概览、配速、心率区间、跑步指标、健康对比、历史对比、目标进度）
- [x] 端到端测试通过（mock + 真实数据）

### Phase 6：Morning Call ✅
- [x] morning_call.py：5 个模块（身体状态评分、7日健康趋势、训练建议、训练负荷、目标提醒）
- [x] 修复 training_readiness 列表格式兼容问题
- [x] 端到端测试通过（mock + 真实数据）

### Phase 7：月报 ✅
- [x] monthly_report.py：12 个模块（Hero、5大指标、每日跑量、高光、强度分布、周趋势、PB、健康月度、总结、下月目标）
- [x] 修复 render_weekly_distance_chart 支持 31 天数据
- [x] 端到端测试通过（mock + 真实数据）

### Phase 8：架构升级 + Race Report ✅
- [x] report_styles.py：统一样式系统（5 套配色方案、字体层级、尺寸定义、布局常量、辅助函数）
- [x] ai_narrator.py：AI Narrative 生成器（4 种叙事风格 + 3 种赛事叙事 + 规则引擎降级）
- [x] risk_detector.py：风险检测引擎（HRV趋势/负荷/睡眠/恢复 四维检测）
- [x] morning_report.py：Morning Report 重制（手机竖版 1080x1920，Calm 风格，Readiness Score 大数字）
- [x] daily_report.py：Daily Report 重制（标准海报，Focus 风格，训练复盘）
- [x] weekly_report_v2.py：Weekly Report v2（标准海报，Analysis 风格，含 Risk Alert）
- [x] race_report.py：Race Report（深色背景 Epic 风格，Split Analysis + Critical Moment + Race Intelligence + Finish Narrative）
- [x] run_report.py 升级：支持 6 种命令（morning/daily/weekly/monthly/race/all）
- [x] 端到端测试通过（mock 数据，5 种报表全部生成成功）

---

## 五、测试策略

每个 Phase 完成后：
1. 生成 `report/test_reports/` 下的测试报告 JSON
2. 生成图片到 `scripts/report/output/` 目录
3. 终端打印可读摘要

---

## 六、报表对比（旧版 → 新版）

| 报表 | 旧版文件 | 新版文件 | 主要变化 |
|------|---------|---------|---------|
| Morning | `morning_call.py` | `morning_report.py` | 手机竖版、Calm 风格、Readiness Score 大数字 |
| Daily | `post_run_report.py` | `daily_report.py` | 重命名、Focus 风格、AI Insight 模块 |
| Weekly | `weekly_report.py` | `weekly_report_v2.py` | Analysis 风格、Risk Alert、Recovery/Efficiency sparkline |
| Monthly | `monthly_report.py` | `monthly_report.py` | 无变化 |
| Race | — | `race_report.py` | 全新，深色背景 Epic 风格 |

---

## 七、参考资料

| 文件 | 用途 |
|------|------|
| `D:\Garmin\garmin-fitness-v3\docs\api` | API 字段文档 + DB 映射 |
| `D:\Garmin\garmin-agent\suggestion\健康数据.txt` | 健康数据真实样例值（mock 数据参考） |
| `D:\Garmin\garmin-agent\suggestion\API方法.txt` | API 方法速查 |
| `garmin_agent/formatters.py` | 格式化函数复用 |
| `garmin_agent/classifier.py` | 活动分类逻辑复用 |
