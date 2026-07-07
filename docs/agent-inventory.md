# Garmin Agent 现状梳理

## 架构形式

```
用户提问
  ↓
Planner (LLM) → 决定 mode: tool / code / direct
  ↓
┌─ tool mode → 调用预设工具 → 返回格式化字符串
├─ code mode → LLM 生成 Python → 沙箱执行 → 返回 result 变量
└─ direct mode → LLM 直接回复
  ↓
Synthesizer (LLM) → 基于数据 + SYNTHESIS_PROMPT → 生成带解读的回复
```

**核心设计**：数据获取（Python，确定性）+ 数据解读（LLM，擅长的）

---

## 已注册工具（21个，TOOL_REGISTRY）

### 活动查询
| 工具 | 用途 | 返回 |
|------|------|------|
| get_latest_activity | 最近一次活动 | 格式化字符串 |
| get_activities_by_date | 日期范围内活动统计 | 统计+列表 |
| get_activity_detail | 活动详情（配速/步态/训练效果） | 详细数据 |
| search_activities | 关键词搜索 | 活动列表+ID |
| search_by_training_type | 按训练类型搜索 | 活动列表 |
| get_activities_fordate | 某天的所有活动 | 活动列表 |
| get_week_summary | 最近N周统计 | 统计数据 |

### 圈/分段分析
| 工具 | 用途 | 返回 |
|------|------|------|
| get_activity_splits | 分段配速 | 圈数据 |
| evaluate_lap_quality | 圈质量评分（最佳/最差圈） | 评分+明细 |
| filter_laps_by_pace | 按配速过滤圈 | 符合条件的圈 |
| get_interval_analysis | 间歇训练分析 | 段落+统计 |
| compare_interval_trainings | 间歇训练横向对比 | 趋势表 |

### 训练/能力
| 工具 | 用途 | 返回 |
|------|------|------|
| classify_activity_type | 训练类型分类 | 类型+原因 |
| get_training_capacity | 训练能力（VO2Max+比赛预测+乳酸阈值） | 能力数据 |
| get_training_status | 训练状态 | 状态信息 |
| get_hr_zone_distribution | 心率区间分布(Z1-Z5) | 区间数据 |
| get_activity_hr_zones | 心率区间分布 | 区间数据 |

### 健康/恢复
| 工具 | 用途 | 返回 |
|------|------|------|
| get_daily_health_summary | 今日健康（睡眠+HRV+准备度） | 综合摘要 |
| get_heart_rate_data | 心率数据 | 心率曲线 |
| get_resting_heart_rate | 静息心率 | 数值 |
| get_sleep_data | 睡眠数据 | 睡眠详情 |
| get_hrv_data | HRV数据 | HRV详情 |

---

## 未注册但已定义的工具（12个）

| 工具 | 用途 | 位置 |
|------|------|------|
| get_training_readiness | 训练准备度 | activity_tools.py |
| get_historical_training_readiness | 历史准备度 | activity_tools.py |
| get_body_composition | 身体成分 | activity_tools.py |
| get_user_profile | 用户资料 | activity_tools.py |
| get_respiration_data | 呼吸数据 | activity_tools.py |
| get_spo2_data | 血氧数据 | activity_tools.py |
| get_menstrual_data | 经期数据 | activity_tools.py |
| get_stress_data | 压力数据 | activity_tools.py |
| get_steps_data | 步数数据 | activity_tools.py |
| get_activities_for_date | 某天活动（不同实现） | activity_tools.py |
| get_rhr_history | 静息心率历史 | activity_tools.py |
| get_hrv_history | HRV历史 | activity_tools.py |

---

## Code Mode 可用的 API（通过 client.xxx()）

| API | 用途 |
|-----|------|
| client.get_activities(limit, start) | 最近活动列表 |
| client.get_activities_by_date(start, end, type) | 按日期范围搜索 |
| client.get_activity(activity_id) | 单个活动详情 |
| client.get_activity_splits(activity_id) | 分圈数据 |
| client.get_activity_split_summaries(activity_id) | 分段摘要 |
| client.get_activity_typed_splits(activity_id) | 间歇 ACTIVE/RECOVERY 分段 |
| client.get_activity_hr_in_timezones(activity_id) | 心率区间分布 |
| client.get_activity_details(activity_id) | 逐秒详细数据 |
| client.get_activity_weather(activity_id) | 活动天气 |
| client.get_activity_power_in_timezones(activity_id) | 功率区间 |
| client.get_activity_exercise_sets(activity_id) | 力量训练组数 |
| client.get_activities_fordate(date_str) | 某天的所有活动 |
| client.get_heart_rates(date_str) | 全天心率 |
| client.get_rhr_day(date_str) | 静息心率 |
| client.get_hrv_data(date_str) | HRV数据 |
| client.get_sleep_data(date_str) | 睡眠数据 |
| client.get_training_status(date_str) | 训练状态 |
| client.get_training_readiness(date_str) | 训练准备度 |
| client.get_fitnessage_data() | 健身年龄+VO2Max |
| client.get_race_predictions() | 比赛预测 |
| client.get_endurance_score() | 耐力评分 |
| client.get_hill_score(activity_id) | 爬坡评分 |
| client.get_lactate_threshold() | 乳酸阈值 |
| client.get_latest_activity() | 最近一次活动(dict) |
| client.get_todays_activities() | 今天的活动 |
| client.get_week_activities(weeks) | 最近几周活动 |

---

## 支撑模块

| 模块 | 功能 | 状态 |
|------|------|------|
| classifier.py | 活动分类（8类：race/trail/interval/long_run/lactate_threshold/tempo/easy/mixed） | ✅ 已测试 |
| interval_analyzer.py | 间歇训练分析（提取段落+统计+对比） | ✅ 已测试 |
| coach_evaluator.py | 教练评估数据准备 | ✅ 已测试 |
| activity_query.py | 高级活动查询（ActivitySummary/ActivityRangeSummary） | ✅ 已实现 |
| cache_manager.py | 活动分类缓存 | ✅ 已实现 |
| cache_sync.py | 缓存同步 | ✅ 已实现 |
| formatters.py | 格式化工具（配速/距离/时长/心率/步频/步幅/垂振/触地时间） | ✅ 已实现 |

---

## LLM 人格定义（SYNTHESIS_PROMPT）

- 角色：专业、主动的跑步教练
- 数据来源标注（📡 Garmin / 📦 缓存 / ⚠️ 出错）
- 明细优先原则（有列表就逐条输出，不允许用总结替代）
- 回复风格：主动、专业、精确、有用、数据驱动
- 绝对禁止：编造数据、问用户要 activity_id、删除活动 ID

---

## 当前形式是否跑通

**基本形式已跑通**：
- tool mode → 21个工具可调用
- code mode → 沙箱执行 Python，可调用所有 client API
- direct mode → 闲聊回复
- synthesis → LLM 基于数据生成带解读的回复

**已知问题**：
1. 12个已定义工具未注册（可能有意为之，也可能遗漏）
2. code mode 依赖 LLM 写代码，可靠性取决于 LLM 能力
3. 没有 MCP 封装（目前所有能力都在 Python 代码中）

---

## 待确认

1. 这21个工具的覆盖范围是否完整？需要增加/删除/合并哪些？
2. 12个未注册工具是有意排除还是遗漏？
3. MCP 封装的具体形式是什么？（当前全部是 Python @tool）
4. agent 的 skills 文件（角色定义、能力说明）在哪里？是否需要新建？
5. "把这个形式跑通"具体指什么？当前 main.py 已经可以交互了
