"""Tests for FX analysts using the stub LLM."""

import asyncio
import json
import pytest

from fx_agent.infrastructure.llm import make_stub_llm
from fx_agent.infrastructure.settings import Settings
from fx_agent.analysts.macro import run_macro_analyst
from fx_agent.analysts.carry import run_carry_analyst
from fx_agent.analysts.technical import run_technical_analyst
from fx_agent.analysts.news import run_news_analyst
from fx_agent.analysts.sentiment import run_sentiment_analyst


STUB_RESPONSE = json.dumps({
    "key_points": ["Test point 1", "Test point 2"],
    "macro_direction": "neutral",
    "carry_direction": "neutral",
    "trend": "ranging",
    "news_sentiment": "neutral",
    "sentiment_signal": "neutral",
    "recommended_direction": "hold",
    "confidence": 0.5,
    "summary": "Stub summary for testing.",
})


@pytest.fixture
def settings():
    return Settings(
        anthropic_api_key="stub",
        finnhub_api_key=None,
        fred_api_key=None,
    )


@pytest.fixture
def stub_llm():
    factory = make_stub_llm(default=STUB_RESPONSE)
    return factory("claude-sonnet-4-6")


def test_macro_analyst(settings, stub_llm):
    result = asyncio.run(run_macro_analyst("EURUSD", stub_llm, settings))
    assert "key_points" in result
    assert "summary" in result


def test_carry_analyst(settings, stub_llm):
    result = asyncio.run(run_carry_analyst("EURUSD", stub_llm, settings))
    assert "key_points" in result
    assert "summary" in result


def test_news_analyst(settings, stub_llm):
    result = asyncio.run(run_news_analyst("EURUSD", stub_llm, settings))
    assert "key_points" in result
    assert "summary" in result


def test_sentiment_analyst(settings, stub_llm):
    result = asyncio.run(run_sentiment_analyst("EURUSD", stub_llm, settings))
    assert "key_points" in result
    assert "summary" in result
