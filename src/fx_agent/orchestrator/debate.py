"""Research and risk debate nodes for the FX pipeline."""

from __future__ import annotations

import json
import logging
from typing import Any

from ..infrastructure.llm import LLMCallable

logger = logging.getLogger(__name__)

# ── Research debate ────────────────────────────────────────────────────────────

BULLISH_SYSTEM = """You are a bullish FX researcher. Your job is to construct the strongest
possible case for buying the base currency (going long) in the given currency pair.
Use all available analyst data to build your argument.

Respond with JSON only (no markdown fences):
{
  "key_points": ["...", "..."],
  "strongest_argument": "...",
  "supporting_data": ["...", "..."],
  "price_target": 0.0,
  "confidence": 0.0-1.0
}"""

BEARISH_SYSTEM = """You are a bearish FX researcher. Your job is to construct the strongest
possible case for selling the base currency (going short) in the given currency pair.
Use all available analyst data to build your argument.

Respond with JSON only (no markdown fences):
{
  "key_points": ["...", "..."],
  "strongest_argument": "...",
  "supporting_data": ["...", "..."],
  "price_target": 0.0,
  "confidence": 0.0-1.0
}"""

DEBATE_FACILITATOR_SYSTEM = """You are an FX debate facilitator. Given the bullish and bearish
cases for a currency pair, along with any prior debate rounds, synthesise the arguments
and provide a conclusion.

Respond with JSON only (no markdown fences):
{
  "key_points": ["...", "..."],
  "bull_strongest_points": ["...", "..."],
  "bear_strongest_points": ["...", "..."],
  "conclusion_direction": "buy|sell|hold",
  "conviction": "high|medium|low",
  "confidence": 0.0-1.0,
  "summary": "..."
}"""


def _analyst_summary(state: dict) -> str:
    parts = []
    for key in ["macro_analysis", "carry_analysis", "technical_analysis", "sentiment_analysis", "news_analysis"]:
        data = state.get(key)
        if data:
            name = key.replace("_analysis", "").replace("_", " ").title()
            summary = data.get("summary", "")
            direction = data.get("recommended_direction", data.get("macro_direction", ""))
            conf = data.get("confidence", "")
            parts.append(f"{name}: direction={direction}, confidence={conf}. {summary[:200]}")
    return "\n".join(parts) if parts else "No analyst data available."


async def run_bullish_researcher(state: dict, llm: LLMCallable) -> dict:
    pair = state.get("pair", "UNKNOWN")
    user_msg = f"Currency pair: {pair}\n\nAnalyst data:\n{_analyst_summary(state)}\n\nBuild the bullish case."
    raw = await llm(BULLISH_SYSTEM, user_msg)
    return _parse(raw, "bullish_researcher")


async def run_bearish_researcher(state: dict, llm: LLMCallable) -> dict:
    pair = state.get("pair", "UNKNOWN")
    user_msg = f"Currency pair: {pair}\n\nAnalyst data:\n{_analyst_summary(state)}\n\nBuild the bearish case."
    raw = await llm(BEARISH_SYSTEM, user_msg)
    return _parse(raw, "bearish_researcher")


async def run_debate_facilitator(
    state: dict,
    llm: LLMCallable,
    rounds: int = 2,
) -> dict:
    pair = state.get("pair", "UNKNOWN")
    bull = state.get("bullish_case", {})
    bear = state.get("bearish_case", {})

    user_msg = (
        f"Currency pair: {pair}\n\n"
        f"BULLISH CASE:\n{json.dumps(bull, indent=2)}\n\n"
        f"BEARISH CASE:\n{json.dumps(bear, indent=2)}\n\n"
        f"Synthesise and conclude after {rounds} debate rounds."
    )
    raw = await llm(DEBATE_FACILITATOR_SYSTEM, user_msg)
    return _parse(raw, "debate_facilitator")


# ── Risk debate ────────────────────────────────────────────────────────────────

RISK_SYSTEM = """You are an FX risk analyst with a {stance} risk stance.
Given a trade recommendation for a currency pair, evaluate the risk from your perspective.

Respond with JSON only (no markdown fences):
{
  "key_points": ["...", "..."],
  "risk_assessment": "acceptable|marginal|unacceptable",
  "position_size_suggestion": "full|half|quarter|none",
  "max_risk_pips": 0,
  "stop_loss_pips": 0,
  "take_profit_pips": 0,
  "risk_reward_ratio": 0.0,
  "confidence": 0.0-1.0,
  "summary": "..."
}"""

RISK_FACILITATOR_SYSTEM = """You are an FX risk facilitator. Given three risk assessments
(aggressive, neutral, conservative), synthesise them into a final risk-adjusted recommendation.

Respond with JSON only (no markdown fences):
{
  "key_points": ["...", "..."],
  "final_direction": "buy|sell|hold",
  "position_size": "full|half|quarter|none",
  "stop_loss_pips": 0,
  "take_profit_pips": 0,
  "risk_reward_ratio": 0.0,
  "max_drawdown_pips": 0,
  "confidence": 0.0-1.0,
  "summary": "..."
}"""


async def run_risk_analyst(stance: str, state: dict, llm: LLMCallable) -> dict:
    pair = state.get("pair", "UNKNOWN")
    trade = state.get("trade_recommendation", {})
    system = RISK_SYSTEM.format(stance=stance)
    user_msg = (
        f"Currency pair: {pair}\n\n"
        f"Trade recommendation:\n{json.dumps(trade, indent=2)}\n\n"
        f"Evaluate risk with a {stance} stance."
    )
    raw = await llm(system, user_msg)
    return _parse(raw, f"risk_{stance}")


async def run_risk_facilitator(state: dict, llm: LLMCallable) -> dict:
    pair = state.get("pair", "UNKNOWN")
    agg = state.get("risk_aggressive", {})
    neu = state.get("risk_neutral", {})
    con = state.get("risk_conservative", {})
    user_msg = (
        f"Currency pair: {pair}\n\n"
        f"Aggressive risk:\n{json.dumps(agg, indent=2)}\n\n"
        f"Neutral risk:\n{json.dumps(neu, indent=2)}\n\n"
        f"Conservative risk:\n{json.dumps(con, indent=2)}\n\n"
        "Synthesise into a final risk-adjusted recommendation."
    )
    raw = await llm(RISK_FACILITATOR_SYSTEM, user_msg)
    return _parse(raw, "risk_facilitator")


def _parse(raw: str, agent: str) -> dict:
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except Exception:
        logger.warning("%s: failed to parse LLM response", agent)
        return {
            "key_points": [raw[:500]],
            "confidence": 0.3,
            "summary": raw[:300],
        }
