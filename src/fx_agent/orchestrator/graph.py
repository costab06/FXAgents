"""LangGraph pipeline graph for the FX analysis pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from typing import Any

from langgraph.graph import END, StateGraph

from ..analysts.carry import run_carry_analyst
from ..analysts.macro import run_macro_analyst
from ..analysts.news import run_news_analyst
from ..analysts.sentiment import run_sentiment_analyst
from ..analysts.technical import run_technical_analyst
from ..infrastructure.llm import LLMFactory
from ..infrastructure.settings import Settings
from .debate import (
    run_bearish_researcher,
    run_bullish_researcher,
    run_debate_facilitator,
    run_risk_analyst,
    run_risk_facilitator,
)
from .state import FXState

logger = logging.getLogger(__name__)

TRADER_SYSTEM = """You are a professional FX trader. Given research debate conclusions
and analyst data, make a concrete trade recommendation for the currency pair.

Respond with JSON only (no markdown fences):
{
  "key_points": ["...", "..."],
  "direction": "buy|sell|hold",
  "entry_price": 0.0,
  "stop_loss_pips": 0,
  "take_profit_pips": 0,
  "position_size_suggestion": "full|half|quarter",
  "time_horizon": "intraday|swing|position",
  "rationale": "...",
  "confidence": 0.0-1.0,
  "summary": "..."
}"""

FUND_MANAGER_SYSTEM = """You are the fund manager for an FX trading desk. Given the complete
analysis pipeline output — macro, carry, technical, sentiment, news, research debate,
trade recommendation, and risk analysis — make the final investment decision.

Respond with JSON only (no markdown fences):
{
  "key_points": ["...", "..."],
  "final_direction": "buy|sell|hold",
  "conviction": "high|medium|low",
  "position_size": "full|half|quarter|none",
  "entry_price": 0.0,
  "stop_loss_pips": 0,
  "take_profit_pips": 0,
  "risk_reward_ratio": 0.0,
  "time_horizon": "intraday|swing|position",
  "key_risks": ["...", "..."],
  "monitoring_triggers": ["...", "..."],
  "confidence": 0.0-1.0,
  "summary": "..."
}"""


def build_graph(llm_factory: LLMFactory, settings: Settings, checkpointer=None) -> StateGraph:
    """Build and compile the FX analysis LangGraph pipeline."""

    def _llm(agent_id: str):
        return llm_factory(settings.model_for(agent_id))

    # ── Node functions ─────────────────────────────────────────────────────────

    async def macro_analyst_node(state: FXState) -> dict:
        try:
            result = await run_macro_analyst(state["pair"], _llm("macro-analyst"), settings)
            return {"macro_analysis": result}
        except Exception as e:
            logger.exception("macro_analyst_node failed")
            return {"macro_analysis": {}, "errors": state.get("errors", []) + [str(e)]}

    async def carry_analyst_node(state: FXState) -> dict:
        try:
            result = await run_carry_analyst(
                state["pair"], _llm("carry-analyst"), settings,
                macro_data=state.get("macro_analysis"),
            )
            return {"carry_analysis": result}
        except Exception as e:
            logger.exception("carry_analyst_node failed")
            return {"carry_analysis": {}, "errors": state.get("errors", []) + [str(e)]}

    async def technical_analyst_node(state: FXState) -> dict:
        try:
            result = await run_technical_analyst(state["pair"], _llm("technical-analyst"), settings)
            return {"technical_analysis": result}
        except Exception as e:
            logger.exception("technical_analyst_node failed")
            return {"technical_analysis": {}, "errors": state.get("errors", []) + [str(e)]}

    async def sentiment_analyst_node(state: FXState) -> dict:
        try:
            result = await run_sentiment_analyst(state["pair"], _llm("sentiment-analyst"), settings)
            return {"sentiment_analysis": result}
        except Exception as e:
            logger.exception("sentiment_analyst_node failed")
            return {"sentiment_analysis": {}, "errors": state.get("errors", []) + [str(e)]}

    async def news_analyst_node(state: FXState) -> dict:
        try:
            result = await run_news_analyst(state["pair"], _llm("news-analyst"), settings)
            return {"news_analysis": result}
        except Exception as e:
            logger.exception("news_analyst_node failed")
            return {"news_analysis": {}, "errors": state.get("errors", []) + [str(e)]}

    async def research_debate_node(state: FXState) -> dict:
        try:
            bull, bear = await asyncio.gather(
                run_bullish_researcher(state, _llm("bullish-researcher")),
                run_bearish_researcher(state, _llm("bearish-researcher")),
            )
            conclusion = await run_debate_facilitator(
                {**state, "bullish_case": bull, "bearish_case": bear},
                _llm("debate-facilitator"),
                rounds=settings.debate_rounds,
            )
            return {
                "bullish_case": bull,
                "bearish_case": bear,
                "debate_conclusion": conclusion,
            }
        except Exception as e:
            logger.exception("research_debate_node failed")
            return {"errors": state.get("errors", []) + [str(e)]}

    async def trader_node(state: FXState) -> dict:
        try:
            pair = state["pair"]
            debate = state.get("debate_conclusion", {})
            llm = _llm("trader")
            user_msg = (
                f"Currency pair: {pair}\n\n"
                f"Debate conclusion:\n{json.dumps(debate, indent=2)}\n\n"
                f"Macro: {state.get('macro_analysis', {}).get('summary', '')}\n"
                f"Technical: {state.get('technical_analysis', {}).get('summary', '')}\n"
                f"Carry: {state.get('carry_analysis', {}).get('summary', '')}\n"
                f"Sentiment: {state.get('sentiment_analysis', {}).get('summary', '')}\n"
                f"News: {state.get('news_analysis', {}).get('summary', '')}\n\n"
                f"Make a trade recommendation for {pair}."
            )
            raw = await llm(TRADER_SYSTEM, user_msg)
            result = _parse_json(raw, "trader")
            return {"trade_recommendation": result}
        except Exception as e:
            logger.exception("trader_node failed")
            return {"errors": state.get("errors", []) + [str(e)]}

    async def risk_debate_node(state: FXState) -> dict:
        try:
            agg, neu, con = await asyncio.gather(
                run_risk_analyst("aggressive", state, _llm("risk-aggressive")),
                run_risk_analyst("neutral", state, _llm("risk-neutral")),
                run_risk_analyst("conservative", state, _llm("risk-conservative")),
            )
            conclusion = await run_risk_facilitator(
                {**state, "risk_aggressive": agg, "risk_neutral": neu, "risk_conservative": con},
                _llm("risk-facilitator"),
            )
            return {
                "risk_aggressive": agg,
                "risk_neutral": neu,
                "risk_conservative": con,
                "risk_conclusion": conclusion,
            }
        except Exception as e:
            logger.exception("risk_debate_node failed")
            return {"errors": state.get("errors", []) + [str(e)]}

    async def fund_manager_node(state: FXState) -> dict:
        try:
            pair = state["pair"]
            llm = _llm("fund-manager")
            user_msg = (
                f"Currency pair: {pair}\n\n"
                f"Trade recommendation:\n{json.dumps(state.get('trade_recommendation', {}), indent=2)}\n\n"
                f"Risk conclusion:\n{json.dumps(state.get('risk_conclusion', {}), indent=2)}\n\n"
                f"Macro summary: {state.get('macro_analysis', {}).get('summary', '')}\n"
                f"Technical summary: {state.get('technical_analysis', {}).get('summary', '')}\n"
                f"Debate conclusion: {state.get('debate_conclusion', {}).get('summary', '')}\n\n"
                f"Make the final investment decision for {pair}."
            )
            raw = await llm(FUND_MANAGER_SYSTEM, user_msg)
            result = _parse_json(raw, "fund_manager")
            return {"final_decision": result}
        except Exception as e:
            logger.exception("fund_manager_node failed")
            return {"errors": state.get("errors", []) + [str(e)]}

    # ── Parallel analyst fan-out node ──────────────────────────────────────────

    async def analysts_fanout_node(state: FXState) -> dict:
        """Run all 5 analysts in parallel."""
        results = await asyncio.gather(
            macro_analyst_node(state),
            carry_analyst_node(state),
            technical_analyst_node(state),
            sentiment_analyst_node(state),
            news_analyst_node(state),
            return_exceptions=True,
        )
        merged: dict[str, Any] = {}
        for r in results:
            if isinstance(r, dict):
                merged.update(r)
        return merged

    # ── Build graph ────────────────────────────────────────────────────────────

    workflow = StateGraph(FXState)

    workflow.add_node("analysts", analysts_fanout_node)
    workflow.add_node("research_debate", research_debate_node)
    workflow.add_node("trader", trader_node)
    workflow.add_node("risk_debate", risk_debate_node)
    workflow.add_node("fund_manager", fund_manager_node)

    workflow.set_entry_point("analysts")
    workflow.add_edge("analysts", "research_debate")
    workflow.add_edge("research_debate", "trader")
    workflow.add_edge("trader", "risk_debate")
    workflow.add_edge("risk_debate", "fund_manager")
    workflow.add_edge("fund_manager", END)

    return workflow.compile(checkpointer=checkpointer)


def _parse_json(raw: str, agent: str) -> dict:
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except Exception:
        logger.warning("%s: failed to parse JSON", agent)
        return {"key_points": [raw[:500]], "confidence": 0.3, "summary": raw[:300]}


async def run_pipeline(
    pair: str,
    llm_factory: LLMFactory,
    settings: Settings,
    checkpointer=None,
) -> FXState:
    """Run the full pipeline for a pair and return the final state."""
    graph = build_graph(llm_factory, settings, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": f"{pair}-{date.today().isoformat()}"}}
    initial: FXState = {
        "pair": pair,
        "analysis_date": date.today().isoformat(),
        "errors": [],
    }
    final_state = await graph.ainvoke(initial, config)
    return final_state
