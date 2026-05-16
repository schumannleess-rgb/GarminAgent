"""Layer 3: End-to-end smoke test — requires real Garmin token and LLM API.

Run manually: pytest tests/test_agent_smoke.py -v
"""

import os
import sys
from pathlib import Path

import pytest

# Skip if no LLM API key
pytestmark = pytest.mark.skipif(
    not os.getenv("ZHIPU_API_KEY"),
    reason="No LLM API key configured (ZHIPU_API_KEY)",
)


@pytest.fixture(scope="module")
def agent():
    """Create and connect a real agent."""
    # Load .env
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    from garmin_agent.agent import GarminAgent

    a = GarminAgent()
    assert a.connect(), "Failed to connect to Garmin"
    return a


class TestAgentInit:
    """Test agent initialization with real APIs."""

    def test_agent_creates(self):
        from dotenv import load_dotenv
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)

        from garmin_agent.agent import GarminAgent
        a = GarminAgent()
        assert a.llm is not None
        assert a.client is not None

    def test_agent_connects(self, agent):
        assert agent.is_authenticated is not None or agent._agent_with_history is not None


class TestAgentChat:
    """Test single-turn chat with real agent."""

    def test_recent_activity(self, agent):
        response = agent.chat("最近跑了什么")
        assert response
        assert len(response) > 10
        # Should contain some activity-related content
        assert any(kw in response for kw in ["km", "跑步", "活动", "距离", "训练", "没有"])

    def test_health_summary(self, agent):
        response = agent.chat("今天状态如何")
        assert response
        assert len(response) > 10

    def test_training_capacity(self, agent):
        response = agent.chat("我的体能水平怎么样")
        assert response
        assert len(response) > 10
