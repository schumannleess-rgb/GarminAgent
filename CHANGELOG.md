# Changelog

All notable changes to the GarminAgent orchestrator and memory management.

## [Unreleased] - 2026-05-16

### 架构重构：三层动态编排器

**目标**：解决刚性两阶段流水线（意图识别 → 固定工具执行 → 格式化回复）无法处理复杂查询的问题。

**变更文件**：
- `garmin_agent/orchestrator.py` — 新增
- `garmin_agent/agent.py` — 核心流程重写

**新架构流程**：
```
用户输入 → _create_plan() → _execute_plan() → _synthesize_response()
```

**三种执行模式**：
| 模式 | 场景 | 执行方式 |
|------|------|----------|
| `tool` | 简单查询（单次 API 即可回答） | 直接调用预设工具，保留快速路径 |
| `code` | 复杂查询（需多步组合、筛选、聚合） | LLM 生成 Python 代码，在受限沙箱中执行 |
| `direct` | 闲聊/无关 | 直接回复，不调用任何工具 |

**`code` 模式的核心能力**：
- LLM 可任意组合 `client.xxx()` 基础 API（搜索活动 → 获取分圈 → 条件筛选 → 字段提取 → 聚合计算）
- 无需为每种复杂查询硬编码"超级工具"（如 `filter_laps_by_pace`）
- 沙箱预注入 `client`、`formatters`、安全标准库（`json`、`datetime`、`re`、`math`、`collections`、`statistics`）
- 严格限制 builtins（无 `open`/`eval`/`__import__`），超时控制（30s），错误隔离

---

### Prompt 改进

**`SYNTHESIS_PROMPT`（结果解读）**
- 新增核心原则：**明细优先，总结其次**
- 新增数据明细输出规范：按活动分组展示 → 圈数明细表格 → 末尾汇总
- 新增绝对禁止项：**绝对禁止用总结替代明细**
- 明确区分两种输出格式：
  - 多条明细记录 → 分组表格 + 汇总
  - 单个活动/健康摘要 → 关键数据 bullet

**`PLAN_PROMPT`（计划生成）**
- 新增**需求扩展原则**：用户查询往往只说核心条件，Planner 要主动扩展，让 `result` 包含完整上下文（活动全貌 + 目标圈明细 + 其他圈汇总 + 全局汇总）
- 示例代码更新：从只收集慢圈改为生成包含 `activity_overview`、`target_laps`、`other_laps_summary`、`global_summary` 的丰富数据结构

---

### 性能与输出

- `format_llm.max_tokens`：2048 → 4096，防止多活动明细数据被截断
- `_synthesize_response` 的 HumanMessage 新增 4 条强制输出要求（必须按活动逐一展示明细、先概况再逐圈再汇总等）

---

### 记忆管理改进

**变更文件**：`garmin_agent/agent.py`、`garmin_agent/orchestrator.py`

#### 1. Planner 历史上下文增强

**`orchestrator.py` — `Planner.create_plan`**
- 历史条数：`history[-4:]` → `history[-6:]`（多看 2 轮）
- 截断长度：500 字 → 700 字
- 新增 ID 保护：截断前先用正则提取 `[ID:xxxxx]`，截断后把 ID 拼回末尾，确保上下文引用不丢失

#### 2. 活动 ID 上下文注入

**`agent.py` — `_create_plan`**
- 新增：调用 `_extract_ids_from_history` 提取历史中的活动 ID
- 新增：把 ID 列表拼成上下文提示注入 `user_message`，Planner 能直接引用具体 `activity_id`
- 修复：`_extract_ids_from_history` 在新架构中原来是死代码，现在被真正激活

**注入格式示例**：
```
用户问：刚才那几个活动的步频数据

[上下文提示：本次对话中已出现的活动ID: 592865580, 591779441，
如果用户说「刚才」「这些」「上面」等指代词，优先引用这些ID]
```

#### 3. 历史压缩从截断升级为 LLM 摘要

**`agent.py` — `_compress_history`**
- **旧逻辑**：超过 20 条 → 直接丢弃最早的，只保留最近 20 条原文
- **新逻辑**：超过 20 条 → 早期消息（除最近 10 条外）传给 LLM 生成摘要 → 存为 `[📋 早期对话摘要]` 消息 → 保留最近 10 条原文
- **结果**：`1 条摘要 + 10 条原文` 替代 `20 条原文`，长期对话早期信息不丢失
- **降级保护**：摘要生成失败时自动回退到原来的截断逻辑
- **摘要 Prompt 要求保留**：所有活动 ID、用户关注指标、关键结论和建议

---

### 工具层与 API 层

- **无变更**：`garmin_agent/tools/activity_tools.py`、`garmin_agent/client.py` 完全保留，未做修改
- **向后兼容**：`GarminAgent.chat()`、`connect()`、`clear_memory()` 接口签名不变

---

### 修复的 Bug

- `activity_tools.py` — `filter_laps_by_pace`：修复 `_infer_date` 未导入导致的 `NameError`（新增 `_infer_date_for_tools` 函数）
- `agent.py` — `_infer_date`：新增对"本月"的自然语言支持

---

### 待验证

- [ ] 沙箱超时在实际长查询场景中的表现（当前上限 30s）
- [ ] LLM 摘要压缩在多轮对话后的信息保真度
- [ ] `code` 模式在 Windows 下的 ThreadPoolExecutor 超时行为（后台线程不会被真正杀死）
