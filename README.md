# Garmin Agent

基于 LangChain 的 Garmin 训练助手。

---

## 开发方法论

本项目遵循**以终为始**的开发流程：

```
┌─────────────────────────────────────────────────────────┐
│                    开发循环                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. 【目标文档】写清楚要做什么、为什么做                 │
│         ↓                                               │
│  2. 【测试设计】根据目标设计测试用例                     │
│       - 测试是目标的验证方式                             │
│       - 先确定预期结果，再写代码                         │
│         ↓                                               │
│  3. 【架构设计】简略描述实现方案                         │
│         ↓                                               │
│  4. 【开发实现】编码 + 单元测试                          │
│         ↓                                               │
│  5. 【集成测试】验证整体功能                             │
│         ↓                                               │
│  6. 【文档更新】同步更新本文档                           │
│         ↓                                               │
│  7. 进入下一个循环                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**文档分两类：**
- **目标文档**：稳定，不随实现变化（要解决什么问题）
- **实现文档**：迭代，记录当前方案（怎么解决的）

---

## 当前状态

### 已完成节点

| 节点 | 状态 | 说明 |
|------|------|------|
| 基础设施测试 | ✅ | Log 存储、Memory 存储 |
| Garmin 连接 | ✅ | TOKEN 认证正常 |
| LLM 连接 | ✅ | 智谱 GLM-4.7 (Anthropic 端点) |
| Tool 定义 | ✅ | 4 个活动查询工具 |
| Agent 初始化 | ✅ | LangChain Agent 正常 |
| 端到端测试 | ✅ | 单轮对话正常 |
| 多轮对话 | ✅ | Memory 上下文保持正常 |
| 步态数据 | ✅ | 活动详情查询正常 |

### 技术栈

- **LLM**: 智谱 GLM-4.7 (Anthropic 兼容端点)
- **Agent**: LangChain + ChatAnthropic
- **API**: garminconnect
- **Memory**: ChatMessageHistory (支持多轮对话)

---

## 下一步任务

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P0 | 完善测试用例（多轮对话、边界情况） | 待开始 |
| P1 | 添加训练负荷工具 (TSS/TRIMP) | 待开始 |
| P1 | 添加有氧效率工具 (AEI) | 待开始 |
| P2 | 支持本地 LLM (Ollama) | 待开始 |

---

## 快速开始

### 安装

```bash
cd D:\Garmin\garmin-agent
pip install -r requirements.txt
```

### 配置

编辑 `.env` 文件：

```
ZHIPU_API_KEY=your_api_key
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/anthropic
ZHIPU_MODEL=glm-5
```

### 运行

```bash
python main.py
```

### 测试

```bash
# 基础设施测试
python test_infra.py

# 业务功能测试
python test_business.py

# 对话测试
python test_chat.py
```

---

## 项目结构

```
garmin-agent/
├── .env                    # 配置文件
├── tokens/                 # Garmin TOKEN (独立存储)
├── garmin_agent/
│   ├── agent.py            # LangChain Agent
│   ├── client.py           # Garmin API 客户端
│   ├── formatters.py       # 数据格式化
│   └── tools/
│       └── activity_tools.py
├── main.py                 # 入口
├── test_infra.py           # 基础设施测试
├── test_business.py        # 业务功能测试
├── test_chat.py            # 对话测试
└── README.md               # 本文件
```

---

## 可用工具

| 工具 | 功能 | 示例问题 |
|------|------|----------|
| `get_latest_activity` | 获取最近活动 | "最近跑了什么？" |
| `get_activities_by_date` | 按日期查询 | "3月跑了多少？" |
| `get_week_summary` | 周统计 | "这周跑量多少？" |
| `get_activity_detail` | 活动详情 | "步态数据" |

---

## 相关文档

| 文档 | 说明 |
|------|------|
| `training_analytics_design.md` | 训练分析设计 |
| `AGENT_DESIGN_NOTES.md` | Agent 设计笔记 |
| `docs/api_fields_reference.md` | API 字段参考 |

---

## 更新日志

### 2026-03-24 (续)
- 修复 ChatAnthropic 输出格式与 Memory 不兼容问题
- 修复 get_activity_detail 数据解析 (从 summaryDTO 读取)
- 添加步态数据格式化函数 (format_gct, format_vo, format_stride)
- 多轮对话测试通过
- 步态数据查询测试通过
- 更新默认模型为 GLM-4.7

### 2026-03-24
- 完成基础设施测试
- 完成业务功能测试
- 修复 ChatAnthropic 兼容性问题
- 端到端对话测试通过
