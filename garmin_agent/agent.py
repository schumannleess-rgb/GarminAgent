"""
Garmin Agent - Plan & Execute Orchestrator

结构性编排器：
- 简单查询 → 直接调用预设工具（快速路径）
- 复杂查询 → LLM 生成 Python 代码在受限沙箱中执行
- 闲聊    → 直接回复

核心流程：
用户输入 → _create_plan() → _execute_plan() → _synthesize_response()
"""

import os
import re
import json
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

from langchain_anthropic import ChatAnthropic
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from pathlib import Path

from .client import GarminClient
from . import formatters
from .orchestrator import Planner, SandboxExecutor, Plan, SYNTHESIS_PROMPT
from .tools.activity_tools import (
    get_latest_activity,
    get_activities_by_date,
    get_activity_detail,
    search_activities,
    search_by_training_type,
    get_week_summary,
    set_client,
    get_activity_splits,
    get_interval_analysis,
    get_daily_health_summary,
    get_training_capacity,
    get_activities_fordate,
    get_heart_rate_data,
    get_resting_heart_rate,
    get_activity_hr_zones,
    classify_activity_type,
    get_sleep_data,
    get_hrv_data,
    get_training_status,
    compare_interval_trainings,
    evaluate_lap_quality,
    get_hr_zone_distribution,
    filter_laps_by_pace,
)

logger = logging.getLogger(__name__)

# Tool registry
TOOL_REGISTRY = {
    "get_latest_activity": get_latest_activity,
    "get_activities_by_date": get_activities_by_date,
    "get_activity_detail": get_activity_detail,
    "search_activities": search_activities,
    "search_by_training_type": search_by_training_type,
    "get_week_summary": get_week_summary,
    "get_activity_splits": get_activity_splits,
    "get_interval_analysis": get_interval_analysis,
    "get_daily_health_summary": get_daily_health_summary,
    "get_training_capacity": get_training_capacity,
    "get_activities_fordate": get_activities_fordate,
    "get_heart_rate_data": get_heart_rate_data,
    "get_resting_heart_rate": get_resting_heart_rate,
    "get_activity_hr_zones": get_activity_hr_zones,
    "classify_activity_type": classify_activity_type,
    "get_sleep_data": get_sleep_data,
    "get_hrv_data": get_hrv_data,
    "get_training_status": get_training_status,
    "compare_interval_trainings": compare_interval_trainings,
    "evaluate_lap_quality": evaluate_lap_quality,
    "get_hr_zone_distribution": get_hr_zone_distribution,
    "filter_laps_by_pace": filter_laps_by_pace,
}


def _infer_date(text: str, today: date = None) -> str:
    """把自然语言日期转成 YYYY-MM-DD。推不出来就返回今天。"""
    if today is None:
        today = date.today()

    text = text.strip()

    # 直接是 YYYY-MM-DD
    if re.match(r'\d{4}-\d{2}-\d{2}', text):
        return text

    # X月X日 / X月X号
    m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]', text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = today.year
        try:
            d = date(year, month, day)
            if d > today:
                d = date(year - 1, month, day)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # X天前 / 前天 / 昨天
    if "前天" in text:
        return (today - timedelta(days=2)).strftime("%Y-%m-%d")
    if "昨天" in text:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    if "今天" in text:
        return today.strftime("%Y-%m-%d")
    m = re.search(r'(\d+)\s*天前', text)
    if m:
        return (today - timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")

    # 上周 / 本周
    if "上周" in text:
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        return f"{last_monday.strftime('%Y-%m-%d')},{last_sunday.strftime('%Y-%m-%d')}"
    if "本周" in text or "这周" in text:
        monday = today - timedelta(days=today.weekday())
        return f"{monday.strftime('%Y-%m-%d')},{today.strftime('%Y-%m-%d')}"

    # 上个月
    if "上月" in text or "上个月" in text:
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return f"{last_month_start.strftime('%Y-%m-%d')},{last_month_end.strftime('%Y-%m-%d')}"

    # 本月 / 这个月
    if "本月" in text or "这个月" in text:
        first_this_month = today.replace(day=1)
        return f"{first_this_month.strftime('%Y-%m-%d')},{today.strftime('%Y-%m-%d')}"

    return today.strftime("%Y-%m-%d")


def _infer_date_range(text: str, today: date = None) -> tuple:
    """返回 (start_date, end_date) 字符串元组。"""
    if today is None:
        today = date.today()

    result = _infer_date(text, today)

    # 如果返回的是范围（包含逗号）
    if "," in result:
        parts = result.split(",")
        return parts[0], parts[1]

    return result, result


# Legacy prompts (kept for reference, not used in new flow)
FORMAT_PROMPT = """你是 Garmin 训练助手，一个专业、主动的跑步教练。

## 数据来源标注（必须遵守！）

在回复开头标注数据来源：
- 如果数据来自 Garmin 真实 API → 在标题后加 "📡 数据来自 Garmin"
- 如果数据是模拟/缓存 → 加 "📦 数据来自缓存"

## 回复风格

- 🔥 **主动**：直接给结论和建议，不要问用户"你想了解什么"
- 🏃 **专业**：用教练语气，专业但亲切
- 📏 **精确**：距离 km，配速 分:秒/km，心率 bpm
- 💡 **有用**：每次回复必须包含具体的下一步建议

## 回复格式

📊 **[标题]** 📡 数据来自 Garmin

[1-2句话直接给结论]

📌 关键数据：
• 数据项：数值
• 数据项：数值

💡 建议：
[1-3条具体可执行的建议，比如"建议明天做一次轻松跑恢复"而不是"可以考虑适当休息"]

🔥 你可以试试：
[主动推荐1-2个相关的后续查询，比如"想看分段配速？直接说'分段数据'" ]

## 绝对禁止
- 不要问用户"你想了解什么"、"需要我帮你查什么"
- 不要问用户要 activity_id，自己去查
- 不要编造数据，只用工具返回的真实数据
- 不要说"如果您有其他问题"之类的客套话
- **不要删除活动 ID**：工具返回的 [ID:xxxxx] 必须保留在回复中，用户需要它来查看详细数据
"""


class GarminAgent:
    """Garmin Training Assistant Agent (Plan & Execute Orchestrator)"""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        garmin_email: str = None,
        garmin_password: str = None,
    ):
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        self.base_url = base_url or os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/anthropic")
        self.model = model or os.getenv("ZHIPU_MODEL", "glm-4.7")

        if not self.api_key:
            raise ValueError("需要 API Key。请设置 ZHIPU_API_KEY 环境变量。")

        self.client = GarminClient(email=garmin_email, password=garmin_password)

        self._memory_dir = Path(__file__).parent.parent / "memory"
        self._memory_dir.mkdir(exist_ok=True)
        self._logs_dir = Path(__file__).parent.parent / "logs"
        self._logs_dir.mkdir(exist_ok=True)

        # 计划生成用低温（确定性决策）
        self.llm = ChatAnthropic(
            model=self.model, temperature=0.2,
            api_key=self.api_key, base_url=self.base_url, max_tokens=2048,
        )
        # 回复格式化用高温（创造性表达），token 上限提高以支持多活动明细输出
        self.format_llm = ChatAnthropic(
            model=self.model, temperature=0.7,
            api_key=self.api_key, base_url=self.base_url, max_tokens=4096,
        )

        # 编排器组件
        self.planner = Planner(self.llm)
        self.sandbox = None  # 在 connect() 后初始化，需要 client

        self._connected = False

    def get_welcome_message(self) -> str:
        return """嘿！我是你的 Garmin 训练教练 🏃

我能帮你做这些：

  🏃 训练记录    "最近跑了什么" / "这周跑量" / "昨天的活动"
  📊 活动分析    "上次跑步的配速" / "分段数据" / "心率区间"
  🏋️ 训练类型    "找间歇跑" / "节奏跑" / "长距离跑"
  💪 体能评估    "体能水平" / "比赛预测" / "乳酸阈值"
  😴 健康状态    "今天状态" / "睡眠怎么样" / "静息心率"

直接说就行，不用记命令！"""

    def connect(self) -> bool:
        try:
            if not self.client.connect():
                return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

        set_client(self.client)
        self.sandbox = SandboxExecutor(self.client, formatters)
        self._connected = True
        logger.info("Agent initialized (plan & execute orchestrator)")
        return True

    def _get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        session_file = self._memory_dir / f"{session_id}.json"
        return FileChatMessageHistory(str(session_file))

    # ==========================================
    # Core Orchestration: Plan → Execute → Synthesize
    # ==========================================

    def _create_plan(self, user_message: str, history_messages: list = None) -> Plan:
        """Step 1: Generate execution plan, enriched with recent activity IDs from history."""
        recent_ids = self._extract_ids_from_history(history_messages)
        enriched_message = user_message
        if recent_ids:
            # 注入上下文，让 Planner 知道对话中出现过哪些活动 ID
            enriched_message = (
                f"{user_message}\n\n"
                f"[上下文提示：本次对话中已出现的活动ID: {', '.join(recent_ids)}，"
                f"如果用户说「刚才」「这些」「上面」等指代词，优先引用这些ID]"
            )
            logger.info(f"Enriched message with {len(recent_ids)} recent IDs: {recent_ids}")
        return self.planner.create_plan(enriched_message, history_messages)

    def _execute_plan(self, plan: Plan) -> Dict[str, Any]:
        """Step 2: Execute the plan (tool call or code execution)."""
        if plan.mode == "direct":
            return {"type": "direct", "content": plan.reply or "嘿！直接问我关于跑步的问题就行 🏃"}

        if plan.mode == "tool":
            params = self._resolve_dates(plan.params or {})
            tool_name = plan.tool_name or "get_latest_activity"
            result = self._execute_tool(tool_name, params)
            return {
                "type": "tool",
                "tool_name": tool_name,
                "content": result,
            }

        if plan.mode == "code":
            if self.sandbox is None:
                return {
                    "type": "code",
                    "stdout": "",
                    "result": None,
                    "error": "沙箱未初始化，请先调用 connect()",
                    "code": plan.code,
                }
            exec_result = self.sandbox.execute(plan.code, timeout=30)
            return {
                "type": "code",
                "stdout": exec_result["stdout"],
                "result": exec_result["result"],
                "error": exec_result["error"],
                "code": plan.code,
            }

        # Unknown mode fallback
        return {"type": "error", "content": f"Unknown plan mode: {plan.mode}"}

    def _synthesize_response(self, user_message: str, execution_result: Dict[str, Any]) -> str:
        """Step 3: Generate final natural language response from execution results."""
        # Build the context for the format LLM
        if execution_result.get("type") == "direct":
            return execution_result["content"]

        if execution_result.get("type") == "error":
            return f"抱歉，执行出错了: {execution_result.get('content', '未知错误')}"

        # Build result description
        result_parts = []

        if execution_result.get("type") == "tool":
            result_parts.append(f"【工具: {execution_result.get('tool_name')}】")
            result_parts.append(str(execution_result.get("content", "")))

        elif execution_result.get("type") == "code":
            if execution_result.get("error"):
                result_parts.append(f"⚠️ 代码执行出错:\n{execution_result['error']}")
            if execution_result.get("stdout"):
                result_parts.append(f"📤 输出:\n{execution_result['stdout']}")
            if execution_result.get("result") is not None:
                try:
                    result_json = json.dumps(execution_result["result"], ensure_ascii=False, indent=2, default=str)
                    result_parts.append(f"📦 结果 (JSON):\n{result_json}")
                except Exception:
                    result_parts.append(f"📦 结果:\n{str(execution_result['result'])}")
            if not result_parts:
                result_parts.append("代码执行完成，但没有输出和结果。")

        tool_result = "\n\n".join(result_parts)

        messages = [
            SystemMessage(content=SYNTHESIS_PROMPT),
            HumanMessage(content=f"""用户问：{user_message}

执行结果：
{tool_result}

⚠️ 重要输出要求：
- 必须输出每一个活动的明细，不能只给总结
- 每个活动的每一个符合条件的圈数必须单独列出（圈号、配速、心率、步频、步幅、垂直振幅）
- 不符合条件的圈也要给出概况汇总
- 最后再做整体汇总
- 数据量大时用表格格式
- 绝对禁止用「共有X个慢圈，平均配速Y」代替逐圈列表

生成回复："""),
        ]
        try:
            response = self.format_llm.invoke(messages)
            content = response.content
            if isinstance(content, list):
                texts = [item.get("text", "") if isinstance(item, dict) else str(item) for item in content]
                content = "".join(texts)
            return content
        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            return tool_result

    # ==========================================
    # Legacy helpers (kept for tool-mode and internal use)
    # ==========================================

    def _resolve_dates(self, params: Dict) -> Dict:
        """把自然语言日期转成 YYYY-MM-DD"""
        today = date.today()
        for key in ["start_date", "end_date", "date_str"]:
            if key in params and isinstance(params[key], str):
                val = params[key]
                if not re.match(r'\d{4}-\d{2}-\d{2}', val):
                    if key in ("start_date", "end_date"):
                        start, end = _infer_date_range(val, today)
                        params["start_date"] = start
                        params["end_date"] = end
                    else:
                        params[key] = _infer_date(val, today)
        return params

    def _execute_tool(self, tool_name: str, params: Dict) -> str:
        if tool_name not in TOOL_REGISTRY:
            return f"未知工具: {tool_name}"

        tool = TOOL_REGISTRY[tool_name]
        try:
            for key in ["limit", "weeks"]:
                if key in params and isinstance(params[key], str):
                    try:
                        params[key] = int(params[key])
                    except ValueError:
                        pass

            if "activity_id" in params and isinstance(params["activity_id"], str) and "," in str(params["activity_id"]):
                ids = [x.strip() for x in str(params["activity_id"]).split(",") if x.strip()]
                results = []
                for aid in ids:
                    try:
                        r = tool.invoke({"activity_id": int(aid)})
                        results.append(r)
                    except Exception as e:
                        results.append(f"活动 {aid}: {e}")
                return "\n\n---\n\n".join(results)

            if "activity_id" in params and isinstance(params["activity_id"], str):
                try:
                    params["activity_id"] = int(params["activity_id"])
                except ValueError:
                    pass

            result = tool.invoke(params) if params else tool.invoke({})
            logger.info(f"Tool {tool_name}: {len(str(result))} chars")
            return str(result)
        except Exception as e:
            logger.error(f"Tool {tool_name} error: {e}")
            return f"工具调用失败: {e}"

    def _extract_ids_from_history(self, history_messages: list = None) -> List[str]:
        """从对话历史中提取所有活动 ID"""
        if not history_messages:
            return []
        ids = []
        for msg in history_messages[-6:]:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            ids.extend(re.findall(r'\[ID:(\d+)\]', content))
            ids.extend(re.findall(r'ID:\s*(\d{6,})', content))
        seen = set()
        unique = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                unique.append(i)
        return unique

    def _fallback_intent(self, user_message: str, history_messages: list = None) -> Dict[str, Any]:
        """Legacy fallback for intent parsing."""
        msg = user_message.lower()

        if any(kw in msg for kw in ["这些", "刚才", "上面的", "全部", "都"]):
            ids = self._extract_ids_from_history(history_messages)
            if ids:
                return {"tool": "get_activity_detail", "params": {"activity_id": ",".join(ids)}}

        type_map = {
            "间歇": "interval", "interval": "interval",
            "节奏": "tempo", "tempo": "tempo",
            "轻松": "easy", "easy": "easy",
            "长距离": "long_run", "长跑": "long_run", "lsd": "long_run",
            "比赛": "race", "race": "race",
            "乳酸阈值": "lactate_threshold",
            "越野": "trail",
        }

        for kw, tt in type_map.items():
            if kw in msg:
                params = {"training_type": tt}
                m = re.search(r'(\d+)\s*(?:次|个)', msg)
                if m:
                    params["limit"] = int(m.group(1))
                return {"tool": "search_by_training_type", "params": params}

        if any(kw in msg for kw in ["状态", "睡眠", "hrv", "恢复"]):
            return {"tool": "get_daily_health_summary", "params": {}}
        if any(kw in msg for kw in ["体能", "vo2", "耐力", "能跑", "比赛预测"]):
            return {"tool": "get_training_capacity", "params": {}}
        if any(kw in msg for kw in ["这周", "本周", "周跑量"]):
            return {"tool": "get_week_summary", "params": {"weeks": 1}}
        if "心率" in msg:
            return {"tool": "get_heart_rate_data", "params": {}}
        if "静息" in msg:
            return {"tool": "get_resting_heart_rate", "params": {}}

        return {"tool": "get_latest_activity", "params": {}}

    def _archive_chat(self, user_msg: str, assistant_msg: str, session_id: str, tool_name: str, tool_result: str):
        try:
            log_file = self._logs_dir / f"chat_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
            entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": session_id,
                "user": user_msg,
                "assistant": assistant_msg,
                "tool": tool_name,
                "tool_result_preview": tool_result[:500] if tool_result else "",
            }
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Archive failed: {e}")

    def _compress_history(self, session_id: str, max_messages: int = 20, keep_recent: int = 10):
        """当历史超过 max_messages 条时，用 LLM 把早期消息压缩成摘要，保留最近 keep_recent 条原文。"""
        try:
            history = self._get_session_history(session_id)
            msgs = history.messages
            if len(msgs) <= max_messages:
                return  # 未超限，不处理

            # 需要压缩的旧消息（除最近 keep_recent 条以外）
            old_msgs = msgs[:-keep_recent]
            recent_msgs = msgs[-keep_recent:]

            # 把旧消息格式化成文本，让 LLM 做摘要
            old_text_parts = []
            for m in old_msgs:
                role = "用户" if isinstance(m, HumanMessage) else "助手"
                content = m.content if isinstance(m.content, str) else str(m.content)
                old_text_parts.append(f"[{role}]: {content[:300]}")  # 每条只取前300字
            old_text = "\n\n".join(old_text_parts)

            summary_prompt = [
                SystemMessage(content=(
                    "你是对话摘要助手。请把以下 Garmin 训练助手的对话历史压缩成一段简洁的摘要。\n"
                    "摘要必须保留：\n"
                    "1. 用户查询过哪些活动（活动ID、日期、类型）\n"
                    "2. 用户关注的指标（配速、心率、步频等）\n"
                    "3. 助手给出的关键结论或建议\n"
                    "4. 所有出现过的活动 ID（格式 [ID:xxxxx]），一个都不能丢\n"
                    "摘要控制在200字以内，用中文输出。"
                )),
                HumanMessage(content=f"请压缩以下对话历史：\n\n{old_text}"),
            ]

            try:
                summary_response = self.llm.invoke(summary_prompt)
                summary_content = summary_response.content
                if isinstance(summary_content, list):
                    summary_content = "".join(
                        item.get("text", "") for item in summary_content if isinstance(item, dict)
                    )
                summary_msg = AIMessage(
                    content=f"[📋 早期对话摘要]\n{summary_content}"
                )
                logger.info(f"History compressed: {len(old_msgs)} msgs → 1 summary")
            except Exception as e:
                logger.warning(f"Summary generation failed, falling back to truncation: {e}")
                # 摘要生成失败时降级为保留最近消息
                history.clear()
                for m in recent_msgs:
                    history.add_message(m)
                return

            # 用「摘要 + 最近N条」替换全部历史
            history.clear()
            history.add_message(summary_msg)
            for m in recent_msgs:
                history.add_message(m)

        except Exception as e:
            logger.warning(f"Compress failed: {e}")

    # ==========================================
    # Main Chat Entry
    # ==========================================

    def chat(self, message: str, session_id: str = "default") -> str:
        if not self._connected:
            raise RuntimeError("Agent not initialized. Call connect() first.")

        try:
            # 1. 获取对话历史
            history = self._get_session_history(session_id)

            # 2. 生成执行计划
            plan = self._create_plan(message, history.messages)
            logger.info(f"Plan: mode={plan.mode}, tool={plan.tool_name}, reasoning={plan.reasoning[:80]}")

            # 3. 执行计划
            execution_result = self._execute_plan(plan)

            # 4. 生成回复
            response = self._synthesize_response(message, execution_result)

            # 5. 存档
            history.add_message(HumanMessage(content=message))
            history.add_message(AIMessage(content=response))
            tool_name = plan.tool_name or ("code" if plan.mode == "code" else plan.mode)
            tool_result = json.dumps(execution_result, ensure_ascii=False, default=str)[:500]
            self._archive_chat(message, response, session_id, tool_name, tool_result)
            self._compress_history(session_id)

            return response

        except Exception as e:
            logger.error(f"Chat error: {e}")
            return f"抱歉，出错了: {e}"

    def clear_memory(self, session_id: str = "default"):
        session_file = self._memory_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Cleared memory: {session_id}")
