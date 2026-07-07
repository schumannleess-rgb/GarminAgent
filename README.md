# Garmin Agent 🏃

> AI 驱动的 Garmin 训练分析助手。基于 Plan & Execute 架构，用自然语言查询训练数据。

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
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key 和 Garmin 账号
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
#
# 获取 API Key:
# - 智谱 GLM: https://open.bigmodel.cn 注册获取
# - StepFun: https://platform.stepfun.com

# === Garmin 账号 ===
# 首次登录需要账号密码，之后 TOKEN 自动保存到 ./tokens/
GARMIN_EMAIL=your_email@example.com
GARMIN_PASSWORD=your_password
```

> ⚠️ **安全提示**：`.env` 已在 `.gitignore` 中排除，不会被提交到 Git。不要把 `.env` 上传到公开仓库。

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

**核心设计原则**：数据获取用 Python（确定性），数据解读用 LLM（灵活性）。

---

## 功能

### 对话式查询

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

### 预设工具（21个）

| 分类 | 工具 | 示例问题 |
|------|------|----------|
| 🏃 活动查询 | `search_activities`, `get_activity_detail` | "上次跑步" / "活动详情" |
| 🏋️ 训练类型 | `search_by_training_type`, `classify_activity_type` | "间歇跑" / "节奏跑" |
| 📊 分段分析 | `get_activity_splits`, `get_interval_analysis` | "分段数据" / "间歇分析" |
| 💪 能力评估 | `get_training_capacity`, `get_training_status` | "体能水平" / "比赛预测" |
| 😴 健康恢复 | `get_daily_health_summary` | "今天状态" / "睡眠" |

### CLI 模式

```bash
python garmin_cli.py latest      # 最近一次活动
python garmin_cli.py today       # 今天的活动
python garmin_cli.py week 2      # 最近2周
python garmin_cli.py health      # 健康数据
python garmin_cli.py capacity    # 训练能力
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
│   └── tools/
│       └── activity_tools.py   # 21个预设工具
├── login/
│   └── garmin_login.py     # Garmin 认证模块
├── scripts/report/         # 报告生成脚本
├── docs/
│   └── agent-inventory.md  # Agent 现状梳理
├── main.py                 # 入口（交互式）
├── garmin_cli.py           # CLI 入口
├── requirements.txt        # 依赖
├── .env.example            # 配置模板
├── Makefile / setup.py     # 构建脚本
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

---

## 更新日志

### 0.4.0
- Plan & Execute 架构（Planner + SandboxExecutor + Synthesizer）
- 21个预设工具 + 代码沙箱执行
- 明细优先输出规范
- 历史对话压缩与 ID 上下文注入

### 0.2.0
- 初始 LangChain Agent 版本
- 基础活动查询 + 健康数据

---

## License

MIT