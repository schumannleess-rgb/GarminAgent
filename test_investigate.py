"""
Test script for investigating PLAN_RAW / PLAN_JSON behavior across S1-S8.
Captures logger.warning output for [PLAN_HISTORY], [PLAN_RAW], [PLAN_JSON].
"""
import sys
import os
import re
import json
import logging
import time

# Windows encoding fix
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Load .env before anything else
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up a custom handler to capture log records
class LogCapture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def get_plan_records(self):
        """Return records containing [PLAN_HISTORY], [PLAN_RAW], or [PLAN_JSON]."""
        results = []
        for r in self.records:
            msg = r.getMessage()
            if any(tag in msg for tag in ['[PLAN_HISTORY]', '[PLAN_RAW]', '[PLAN_JSON]']):
                results.append(msg)
        return results

    def clear(self):
        self.records.clear()


def run_test():
    from garmin_agent.agent import GarminAgent

    # Install log capture on the orchestrator logger
    orchestrator_logger = logging.getLogger('garmin_agent.orchestrator')
    orchestrator_logger.setLevel(logging.WARNING)
    log_capture = LogCapture()
    orchestrator_logger.addHandler(log_capture)

    # Also capture the agent logger
    agent_logger = logging.getLogger('garmin_agent.agent')
    agent_logger.setLevel(logging.WARNING)
    agent_logger.addHandler(log_capture)

    print("=" * 70)
    print("GarminAgent Investigate Test - S1 through S8")
    print("=" * 70)

    agent = GarminAgent()
    agent.connect()
    print("[OK] Connected to Garmin\n")

    session_id = "test_investigate"
    agent.clear_memory(session_id=session_id)
    print("[OK] Memory cleared for session:", session_id)

    steps = [
        ("S1", "clear_memory", True),  # True = special command (clear)
        ("S2", "最近跑了什么", False),
        ("S3", "看下这个月跑步或者徒步配速>8：00的圈数的具体信息，心率、配速、步频、步幅、垂直振幅", False),
        ("S4", "看下这个月跑步或者徒步配速>8：00的圈数的具体信息，心率、配速、步频、步幅、垂直振幅", False),  # Exact repeat
        ("S5", "最近三次跑步或者徒步的记录", False),
        ("S6", "我这边都有记录，你怎么没有呢，徒步也算的", False),
        ("S7", "看下这个月跑步或者徒步配速>8：00的圈数的具体信息，心率、配速、步频、步幅、垂直振幅", False),  # Repeat after S6
        ("S8", "要找到我的不常发生的低速度，需要找到本月跑步或者徒步配速<8：00圈的具体信息", False),
    ]

    all_results = []

    for step_id, message, is_clear in steps:
        print(f"\n{'=' * 70}")
        print(f"{step_id} | Sending: {message[:60]}{'...' if len(message) > 60 else ''}")
        print(f"{'=' * 70}")

        log_capture.clear()

        if is_clear:
            # S1: clear memory
            agent.clear_memory(session_id=session_id)
            print(f"[S1] Memory cleared.")
            all_results.append({
                "step": step_id,
                "message": message,
                "response_preview": "(memory cleared)",
                "plan_records": [],
            })
            continue

        try:
            start = time.time()
            response = agent.chat(message, session_id=session_id)
            elapsed = time.time() - start
            print(f"[{step_id}] Response ({elapsed:.1f}s): {str(response)[:200]}")
        except Exception as e:
            print(f"[{step_id}] ERROR: {e}")
            response = f"ERROR: {e}"

        plan_records = log_capture.get_plan_records()
        print(f"[{step_id}] Plan log records ({len(plan_records)}):")
        for rec in plan_records:
            print(f"  {rec}")

        # Parse key fields
        result_entry = {
            "step": step_id,
            "message": message,
            "response_preview": str(response)[:300],
            "plan_records": plan_records,
            "plan_raw_len": None,
            "plan_raw_type": None,
            "plan_raw_preview": None,
            "plan_json_len": None,
            "plan_json_preview": None,
            "plan_history_count": None,
        }

        for rec in plan_records:
            if '[PLAN_RAW]' in rec:
                m = re.search(r'len=(\d+)\s+type=(\w+)\s+preview=(.*)', rec)
                if m:
                    result_entry["plan_raw_len"] = int(m.group(1))
                    result_entry["plan_raw_type"] = m.group(2)
                    result_entry["plan_raw_preview"] = m.group(3)
            elif '[PLAN_JSON]' in rec:
                m = re.search(r'extracted len=(\d+)\s+preview=(.*)', rec)
                if m:
                    result_entry["plan_json_len"] = int(m.group(1))
                    result_entry["plan_json_preview"] = m.group(2)
            elif '[PLAN_HISTORY]' in rec:
                m = re.search(r'injecting (\d+) msgs', rec)
                if m:
                    result_entry["plan_history_count"] = int(m.group(1))

        all_results.append(result_entry)

    # ============ SUMMARY ============
    print("\n\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for r in all_results:
        step = r["step"]
        print(f"\n--- {step} ---")
        print(f"  Message: {r['message'][:60]}")
        if r.get("plan_raw_len") is not None:
            print(f"  [PLAN_RAW]  len={r['plan_raw_len']} type={r['plan_raw_type']} preview={r['plan_raw_preview'][:100] if r['plan_raw_preview'] else ''}")
        if r.get("plan_json_len") is not None:
            print(f"  [PLAN_JSON] len={r['plan_json_len']} preview={r['plan_json_preview'][:100] if r['plan_json_preview'] else ''}")
        if r.get("plan_history_count") is not None:
            print(f"  [PLAN_HISTORY] injecting {r['plan_history_count']} msgs")
        if r.get("plan_raw_len") is None and not r.get("plan_records"):
            print(f"  (no plan records - may be tool/direct mode or error)")

    # Save to JSON
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "test_investigate_result.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[OK] Results saved to {output_path}")


if __name__ == "__main__":
    # Suppress noisy INFO logs from other modules
    logging.basicConfig(level=logging.WARNING, format="%(name)s %(levelname)s: %(message)s")
    run_test()
