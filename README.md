# Garmin Agent 🏃

> AI 驱动的 Garmin 训练分析助手。基于 Plan & Execute 架构，用自然语言查询训练数据，并能离线生成每日恢复力诊断报告。

---

## 功能总览

Garmin Agent 提供两大能力：

1. **对话式训练查询** — 用自然语言问训练/健康数据，助手返回带解读的回复（活动、分段、体能、恢复等）。
2. **每日恢复力报告** — 离线生成静态 HTML 诊断报告，基于睡眠 / HRV / RHR / 训练准备度输出综合恢复分、28 天趋势与分维度建议，双击即可在浏览器（含 Hermes 等无服务环境）查看。

---

## 功能详解

### 一、对话式训练查询

自然语言交互，三类模式自动路由：

```
你: 最近跑了什么？
助手: 📊 最近一次活动 📡 数据来自 Garmin
      [活动详情 + 建议]

你: 今天状态如何？
助手: 📊 每日健康摘要 📡 数据来自 Garmin
      [睡眠 + HRV + 训练准备度]

你: 本月跑步配速>8的圈数明细
助手: [逐活动 + 逐圈明细表格 + 汇总]
```

**预设工具（21 个）**

| 分类 | 工具 | 示例问题 |
|------|------|----------|
| 🏃 活动查询 | `search_activities`, `get_activity_detail` | "上次跑步" / "活动详情" |
| 🏋️ 训练类型 | `search_by_training_type`, `classify_activity_type` | "间歇跑" / "节奏跑" |
| 📊 分段分析 | `get_activity_splits`, `get_interval_analysis` | "分段数据" / "间歇分析" |
| 💪 能力评估 | `get_training_capacity`, `get_training_status` | "体能水平" / "比赛预测" |
| 😴 健康恢复 | `get_daily_health_summary` | "今天状态" / "睡眠" |

**CLI 模式**

```bash
python scripts/garmin_cli.py latest      # 最近一次活动
python scripts/garmin_cli.py today       # 今天的活动
python scripts/garmin_cli.py week 2      # 最近2周
python scripts/garmin_cli.py health      # 健康数据
python scripts/garmin_cli.py capacity    # 训练能力
```

核心设计：**数据获取用 Python（确定性），数据解读用 LLM（灵活性）** —— Synthesizer 严格基于工具返回的原始数据生成回复，不编造数值。

### 二、每日恢复力报告

除对话查询外，还能**离线生成每日恢复力诊断报告**：基于 Garmin 睡眠 / HRV / RHR / 训练准备度等数据，输出**综合恢复分、28 天趋势、数据缺口与分维度建议**。报告为静态 HTML，双击即可在浏览器（含 Hermes 等无服务环境）离线查看，无需后端服务。

**交付物（5 个 HTML）**

| 文件 | 角色 | 适用场景 |
|------|------|----------|
| `output/html/recovery_standard.html` | 标准版（手工维护的基准，深度诊断） | 最完整解读 |
| `output/html/recovery_data.html` | 数字版（全字段纯数据页） | 取数 / 二次加工 |
| `output/html/recovery_pin_paper.html` | 风格 1：pin & paper | 清爽便签风 |
| `output/html/recovery_zine.html` | 风格 2：zine / Retro | 复古杂志风 |
| `output/html/recovery_swiss.html` | 风格 3：Swiss deck（PPT 风） | 演示 / 汇报 |

所有变体读取同一份权威数据，仅样式与排版不同。

**生成方式**

```bash
# 数据源：.local/data/daily_health.json（不提交）→ output/kpi_today.json（权威，不提交）
GARMIN_OUTPUT_DIR=output python scripts/rebuild_kpi_today.py
python scripts/gen_trend_data_view.py
python scripts/variants/pin_paper/build.py
python scripts/variants/zine/build.py
python scripts/variants/recovery_deck/build.py
node scripts/verify_deliverables.js   # 自检：5 交付物数据是否准确
```

**参考文档**：数据契约 [`docs/KPI_DATA_CONTRACT.md`](docs/KPI_DATA_CONTRACT.md) · 每日产出操作手册 [`docs/DAILY_OUTPUT_RUNBOOK.md`](docs/DAILY_OUTPUT_RUNBOOK.md) · 风格变体注册表 [`scripts/variants/MANIFEST.md`](scripts/variants/MANIFEST.md)

---

## 快速开始

### 1. 克隆代码

```bash
git clone https://github.com/schumannleess-rgb/GarminAgent.git
cd GarminAgent
```

### 2. 安装依赖

```bash
# 推荐：使用 setup.py（自动创建虚拟环境）
python setup.py install

# 或手动安装
python -m venv venv
source venv/bin/activate        # macOS
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

### 3. 配置

```bash
mkdir .local
cp .env.example .local/.env
# 编辑 .local/.env，填入你的 LLM API Key 和 Garmin 账号
```

```bash
# .env 内容

# === LLM API 配置 ===
# 两种命名方式都支持（选一种即可）：
# 方式1：ANTHROPIC_* （适合 StepFun 等 Anthropic 兼容 API）
ANTHROPIC_AUTH_TOKEN=your_api_key_here
ANTHROPIC_BASE_URL=https://api.stepfun.com/step_plan
ANTHROPIC_DEFAULT_FABLE_MODEL=step-3.7-flash
#
# 方式2：ZHIPU_* （智谱 GLM 等）
# ZHIPU_API_KEY=your_api_key_here
# ZHIPU_BASE_URL=https://open.bigmodel.cn/api/anthropic
# ZHIPU_MODEL=glm-4.7

# === Garmin 账号 ===
# 首次登录需要账号密码，之后 TOKEN 自动保存到 ./tokens/
GARMIN_EMAIL=your_email@example.com
GARMIN_PASSWORD=your_password
```

> ⚠️ **安全提示**：真实 `.env`、token、缓存、日志、同步数据都放在 `.local/` 下，`.local/` 已在 `.gitignore` 中排除，不会提交到公开仓库。

### 本地运行态与公开仓库边界

本项目按三层维护：

```text
public repo       源码、文档、测试、脱敏 fixtures，可公开发布
.local/           本机 Garmin token、真实健康数据、缓存、日志、输出，不提交
private archive   旧备份和历史运行材料，放到仓库外
```

如需迁移旧版根目录运行态，发布前执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/migrate_local_runtime.ps1
powershell -ExecutionPolicy Bypass -File scripts/preflight_release.ps1
```

### 4. 运行

```bash
python main.py
# 或使用 setup.py
python setup.py run
```

---

## 架构

```
用户提问
  ↓
Planner (LLM) → 决定模式: tool / code / direct
  ↓
┌─ tool mode → 调用预设工具（21个，快速路径）
├─ code mode → LLM 生成 Python 代码在沙箱执行（跨活动分析）
└─ direct mode → 闲聊直接回复
  ↓
Synthesizer (LLM) → 基于数据 + 格式规范 → 生成带解读的回复
```

---

## 技术栈

- **LLM**: 智谱 GLM / OpenAI / Anthropic（Anthropic 兼容 API）
- **框架**: LangChain + ChatAnthropic
- **API**: garminconnect（Garmin Connect 数据接口）
- **认证**: 自动 TOKEN 持久化（首次需账号密码）
- **架构**: Plan & Execute 编排器（支持代码沙箱执行）

---

## 目录结构

```
GarminAgent/
├── garmin_agent/
│   ├── agent.py            # Plan & Execute 编排器
│   ├── orchestrator.py     # Planner + SandboxExecutor
│   ├── client.py           # Garmin API 客户端
│   ├── formatters.py       # 数据格式化
│   ├── classifier.py       # 训练类型分类器
│   ├── cache_manager.py    # 活动分类缓存
│   ├── cache_sync.py       # 缓存同步
│   ├── config.py           # 外部路径配置
│   └── tools/
│       └── activity_tools.py   # 21个预设工具
├── login/
│   └── garmin_login.py     # Garmin 认证模块
├── scripts/
│   ├── garmin_cli.py       # CLI 入口
│   ├── sync_data.py        # 数据同步脚本
│   ├── rebuild_kpi_today.py # 每日 KPI 重建（报告流水线入口，自带计算逻辑）
│   ├── gen_trend_data_view.py # 生成数字版交付物 recovery_data.html
│   ├── compute_all_kpis.py # 独立全量 KPI 计算器（参考用，非管线依赖）
│   ├── verify_deliverables.js # 交付物数据自检（5 HTML 准确性）
│   ├── ppt_common.py       # Swiss deck 共享内容层
│   ├── morning_report.py   # 晨间报告
│   ├── variants/           # 报告风格变体
│   │   ├── pin_paper/      # 风格1 生成器 + 测试
│   │   ├── zine/           # 风格2 生成器
│   │   ├── recovery_deck/  # 风格3 (Swiss) 生成器
│   │   ├── archive/        # 已归档变体（morning-card 等）
│   │   └── MANIFEST.md     # 变体注册表
│   └── report/             # 报告生成脚本
├── tests/                  # 单元测试
├── docs/
│   ├── DAILY_OUTPUT_RUNBOOK.md # 每日产出操作手册
│   ├── KPI_DATA_CONTRACT.md    # 报告数据契约
│   └── （其他设计 / 规格文档）
├── main.py                 # 入口（交互式）
├── setup.py                # 构建脚本
├── requirements.txt        # 依赖
├── .env.example            # 配置模板
├── .local/                 # 本地运行态（不提交）
├── Makefile                # 构建快捷命令
└── README.md
```

---

## 常见问题

### LLM 幻觉怎么处理？

Synthesizer 严格基于工具返回的原始数据生成回复，不允许编造数值。Plan & Execute 架构确保所有数据经过沙箱验证。

### 跨平台支持？

Windows 和 macOS 均可运行。使用 `setup.py` 自动检测平台。

### 怎么换 LLM？

修改 `.env` 中的 `ZHIPU_BASE_URL` 和 `ZHIPU_MODEL` 指向其他兼容 API（如 Ollama 本地模型）。

### 报告 HTML 能离线看吗？

能。报告为纯静态 HTML，双击即可在浏览器打开；Hermes 等无服务环境也能直接查看，无需后端。

---

## 更新日志

### 0.4.0
- Plan & Execute 架构（Planner + SandboxExecutor + Synthesizer）
- 21个预设工具 + 代码沙箱执行
- 明细优先输出规范
- 历史对话压缩与 ID 上下文注入
- 每日恢复力报告（5 个静态 HTML 交付物 + 离线查看）

### 0.2.0
- 初始 LangChain Agent 版本
- 基础活动查询 + 健康数据

---

## License

MIT
