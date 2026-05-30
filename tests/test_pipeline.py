"""End-to-end pipeline test using the stub LLM."""

import asyncio
import json
import pytest

from fx_agent.infrastructure.llm import make_stub_llm
from fx_agent.infrastructure.settings import Settings
from fx_agent.orchestrator.graph import run_pipeline


STUB = json.dumps({
    "key_points": ["Stub point"],
    "macro_direction": "neutral",
    "carry_direction": "neutral",
    "trend": "ranging",
    "news_sentiment": "neutral",
    "sentiment_signal": "neutral",
    "bullish_case": "strong dollar fundamentals",
    "bearish_case": "EUR weakness",
    "conclusion_direction": "hold",
    "direction": "hold",
    "final_direction": "hold",
    "recommended_direction": "hold",
    "risk_assessment": "acceptable",
    "position_size_suggestion": "quarter",
    "conviction": "low",
    "position_size": "quarter",
    "stop_loss_pips": 20,
    "take_profit_pips": 40,
    "risk_reward_ratio": 2.0,
    "confidence": 0.5,
    "summary": "Stub summary.",
})


@pytest.fixture
def settings():
    return Settings(
        anthropic_api_key="stub",
        finnhub_api_key=None,
        fred_api_key=None,
    )


def test_full_pipeline(settings):
    stub_factory = make_stub_llm(default=STUB)
    state = asyncio.run(run_pipeline("EURUSD", stub_factory, settings))
    assert state["pair"] == "EURUSD"
    assert "final_decision" in state
    assert "trade_recommendation" in state
    assert "macro_analysis" in state
