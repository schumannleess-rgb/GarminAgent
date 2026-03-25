"""
Garmin Agent - LangChain Agent Configuration

支持智谱 GLM API (Anthropic 兼容格式)
"""

import os
import logging
import json
from datetime import datetime
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_community.chat_message_histories import ChatMessageHistory, FileChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent

from pathlib import Path

from .client import GarminClient
from .tools.activity_tools import (
    get_latest_activity,
    get_activities_by_date,
    get_activity_detail,
    search_activities,
    search_by_training_type,  # 新增：按训练类型搜索
    get_week_summary,
    set_client,
    # 活动分析工具
    get_activity_splits,
    get_interval_analysis,
    get_hill_score,
    get_activity_split_summaries,
    get_activity_details,
    get_activity_power_zones,
    get_activity_exercise_sets,
    # 日期活动工具
    get_activities_fordate,
    # 合并工具（减少工具数量，提高稳定性）
    get_daily_health_summary,  # 睡眠+HRV+训练准备度
    get_training_capacity,      # 训练状态+健身年龄+耐力+比赛预测+乳酸阈值
    # 心率工具
    get_heart_rate_data,
    get_resting_heart_rate,
    get_activity_hr_zones,
    # 训练分类工具
    classify_activity_type,
)

logger = logging.getLogger(__name__)

# System prompt - 精简版，5个核心工具
SYSTEM_PROMPT = """你是 Garmin 训练助手，一个专业、亲切又活泼的跑步教练！🏃

## ⚠️ 必须遵守

1. **每次回答前必须调用工具** - 你没有任何用户数据，必须先查
2. **禁止编造数字** - 所有数据来自工具返回
3. **先查后说** - 工具返回数据后再分析

## 可用工具（5个）

**search_activities** - 搜索跑步活动
- 触发：用户提到任何活动时

**search_by_training_type** - 按训练类型搜索
- 触发：用户问"间歇跑"、"节奏跑"、"轻松跑"、"长距离"等
- 支持类型：interval(间歇), tempo(节奏), easy(轻松), long_run(长距离), race(比赛)

**get_activity_detail** - 活动详情分析
- 触发：分析具体活动（需先获取activityId）

**get_daily_health_summary** - 每日健康摘要
- 触发：问"今天状态"、"睡眠怎么样"

**get_training_capacity** - 训练能力概览
- 触发：问"体能水平"、"能跑多快"

## 回复格式（严格遵守！）

```
📊 **[标题]**

[1-2句话概括]

📌 关键数据：
• 数据项1：xxx
• 数据项2：xxx

💡 建议：
[专业建议，1-3条]
```

## 回复风格

- 🏃 用教练语气，专业但亲切
- 😊 适当使用 emoji 让回复更生动
- 📏 距离用 km，配速用 分:秒/km
- ✨ 先概括亮点，再分析，最后给建议
"""

# Available tools - 5个核心工具
TOOLS = [
    search_activities,           # 按关键词查询活动
    search_by_training_type,     # 按训练类型搜索（间歇/节奏/轻松/长距离）
    get_activity_detail,         # 活动详情分析
    get_daily_health_summary,    # 每日健康摘要
    get_training_capacity,       # 训练能力概览
]


class GarminAgent:
    """Garmin Training Assistant Agent"""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        garmin_email: str = None,
        garmin_password: str = None,
    ):
        """Initialize the agent

        Args:
            api_key: API key (默认从 ZHIPU_API_KEY 环境变量读取)
            base_url: API base URL (默认从 ZHIPU_BASE_URL 环境变量读取)
            model: LLM model (默认从 ZHIPU_MODEL 环境变量读取)
            garmin_email: Garmin email
            garmin_password: Garmin password
        """
        # 智谱 GLM 配置
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        self.base_url = base_url or os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/anthropic")
        self.model = model or os.getenv("ZHIPU_MODEL", "glm-4.7")

        if not self.api_key:
            raise ValueError("需要 API Key。请设置 ZHIPU_API_KEY 环境变量。")

        # Setup Garmin client
        self.client = GarminClient(
            email=garmin_email,
            password=garmin_password
        )

        # Memory storage directory (persistent)
        self._memory_dir = Path(__file__).parent.parent / "memory"
        self._memory_dir.mkdir(exist_ok=True)

        # Chat logs directory (persistent archive)
        self._logs_dir = Path(__file__).parent.parent / "logs"
        self._logs_dir.mkdir(exist_ok=True)

        # Create LLM (使用智谱 API，Anthropic 兼容格式)
        self.llm = ChatAnthropic(
            model=self.model,
            temperature=0.7,
            api_key=self.api_key,
            base_url=self.base_url,
        )

        # Create prompt
        # 注意：chat_history 由 RunnableWithMessageHistory 自动注入
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),  # 历史对话（自动管理）
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),  # Agent 思考过程
        ])

        # Agent components (initialized after connect)
        self._agent = None
        self._agent_executor = None
        self._agent_with_history = None

    def get_welcome_message(self) -> str:
        """获取欢迎消息和功能菜单"""
        return """🏃 欢迎使用 Garmin 训练助手！

请选择您想了解的内容（输入数字或直接提问）：

1️⃣  活动查询 - 查找跑步记录（如"上次跑步"、"这周跑量"）
2️⃣  活动详情 - 分析某次训练的详细数据
3️⃣  每日健康 - 睡眠、HRV、训练准备度
4️⃣  训练能力 - 体能状态、比赛预测、乳酸阈值
5️⃣  训练类型 - 按类型查找（如"间歇跑"、"节奏跑"、"长距离跑")

💡 也可以直接问问题，例如：
   • "最近跑得怎么样"
   • "今天状态如何"
   • "我的体能水平"
   • "最近5次间歇跑"
"""

    def connect(self) -> bool:
        """Connect to Garmin

        Returns:
            True if successful
        """
        try:
            if not self.client.connect():
                logger.error("Failed to connect to Garmin")
                return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

        # Set client for tools
        set_client(self.client)

        # Create agent
        self._agent = create_tool_calling_agent(self.llm, TOOLS, self.prompt)
        self._agent_executor = AgentExecutor(
            agent=self._agent,
            tools=TOOLS,
            verbose=False,  # 关闭终端输出
            handle_parsing_errors=True,
            return_intermediate_steps=True  # 返回中间步骤用于存档
        )

        # Output converter: fix ChatAnthropic list content format for Memory compatibility
        # AND validate tool calls to prevent hallucination
        def convert_output(response: dict) -> dict:
            """Convert AIMessage content from list to string for Memory compatibility
            AND validate that tools were called (prevent hallucination)"""
            output = response.get("output")
            steps = response.get("intermediate_steps", [])

            # Check if any tools were called
            if not steps:
                # No tools called - this is likely a hallucination!
                # Return a warning message instead
                response["output"] = "⚠️ 我需要先查询数据才能回答。请稍等...\n\n（系统检测：未调用数据查询工具）"
                response["_no_tool_call"] = True
                logger.warning("Agent returned response without calling any tools - potential hallucination blocked")
                return response

            if isinstance(output, list):
                # Extract text from list format [{"text": "...", "type": "text"}]
                texts = []
                for item in output:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item.get("text", ""))
                response["output"] = "".join(texts)
            return response

        # Wrap agent_executor with output converter
        agent_with_converter = self._agent_executor | RunnableLambda(convert_output)

        # Wrap with message history
        self._agent_with_history = RunnableWithMessageHistory(
            agent_with_converter,
            self._get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

        logger.info("Agent initialized successfully")
        return True

    def _get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """Get or create session history (persistent file storage)"""
        session_file = self._memory_dir / f"{session_id}.json"
        return FileChatMessageHistory(str(session_file))

    def _compress_history(self, session_id: str = "default", max_messages: int = 20):
        """Compress chat history by keeping only recent messages

        Args:
            session_id: Session ID
            max_messages: Maximum number of messages to keep (default 20, ~10 turns)
        """
        try:
            history = self._get_session_history(session_id)
            messages = history.messages

            if len(messages) > max_messages:
                # Keep only the most recent messages
                kept_messages = messages[-max_messages:]

                # Clear and rebuild history
                history.clear()
                for msg in kept_messages:
                    history.add_message(msg)

                logger.info(f"Compressed history from {len(messages)} to {max_messages} messages")
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to compress history: {e}")
            return False

    def _archive_chat(self, user_msg: str, assistant_msg: str, session_id: str = "default", steps: list = None):
        """Archive chat to log file (for debugging and review)

        Args:
            user_msg: User message
            assistant_msg: Assistant response
            session_id: Session ID
            steps: Agent intermediate steps (tool calls)
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Format intermediate steps for readability
            formatted_steps = []
            if steps:
                for step in steps:
                    action, observation = step
                    formatted_steps.append({
                        "tool": action.tool,
                        "input": action.tool_input,
                        "output": observation[:500] + "..." if len(str(observation)) > 500 else observation
                    })

            log_entry = {
                "timestamp": timestamp,
                "session_id": session_id,
                "user": user_msg,
                "assistant": assistant_msg,
                "steps": formatted_steps  # 处理过程信息
            }

            # Daily log file
            log_file = self._logs_dir / f"chat_{datetime.now().strftime('%Y-%m-%d')}.jsonl"

            # Append as JSONL (one JSON per line)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            logger.debug(f"Archived chat to {log_file}")
        except Exception as e:
            logger.warning(f"Failed to archive chat: {e}")

    def chat(self, message: str, session_id: str = "default") -> str:
        """Send a message to the agent

        Args:
            message: User message
            session_id: Session ID for memory

        Returns:
            Agent response
        """
        if self._agent_with_history is None:
            raise RuntimeError("Agent not initialized. Call connect() first.")

        try:
            # Use the pre-configured agent_with_history (includes convert_output validation)
            response = self._agent_with_history.invoke(
                {"input": message},
                config={"configurable": {"session_id": session_id}}
            )
            output = response.get("output", "")

            # Get intermediate_steps for logging (may not be present after RunnableWithMessageHistory)
            steps = response.get("intermediate_steps") or []

            # Check if response was blocked due to no tool calls
            if response.get("_no_tool_call"):
                logger.warning(f"Response blocked - no tool calls for: {message[:50]}...")
                self._archive_chat(message, output, session_id, [])
                return output

            # Handle encoding issues
            if isinstance(output, str):
                output = output.encode("utf-8", errors="replace").decode("utf-8")

            # Archive chat for debugging/review
            self._archive_chat(message, output, session_id, steps)

            # Compress history if too long (keep last 20 messages = ~10 turns)
            self._compress_history(session_id, max_messages=20)

            return output
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"抱歉，处理消息时出错: {str(e)}"

    def _update_history(self, session_id: str, user_msg: str, assistant_msg: str):
        """Update message history manually"""
        from langchain_core.messages import HumanMessage, AIMessage
        history = self._get_session_history(session_id)
        history.add_message(HumanMessage(content=user_msg))
        history.add_message(AIMessage(content=assistant_msg))

    def clear_memory(self, session_id: str = "default"):
        """Clear conversation memory for a session"""
        session_file = self._memory_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Cleared memory for session: {session_id}")
