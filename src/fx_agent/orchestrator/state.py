"""LangGraph state definition for the FX analysis pipeline."""

from __future__ import annotations

from typing import Any, TypedDict


class FXState(TypedDict, total=False):
    # ── Input ─────────────────────────────────────────────────────────────────
    pair: str            # e.g. "EURUSD"
    analysis_date: str   # ISO date string

    # ── Analyst outputs ───────────────────────────────────────────────────────
    macro_analysis: dict[str, Any]
    carry_analysis: dict[str, Any]
    technical_analysis: dict[str, Any]
    sentiment_analysis: dict[str, Any]
    news_analysis: dict[str, Any]

    # ── Research debate ───────────────────────────────────────────────────────
    bullish_case: dict[str, Any]
    bearish_case: dict[str, Any]
    debate_rounds: list[dict[str, Any]]
    debate_conclusion: dict[str, Any]

    # ── Trade recommendation ──────────────────────────────────────────────────
    trade_recommendation: dict[str, Any]

    # ── Risk debate ───────────────────────────────────────────────────────────
    risk_aggressive: dict[str, Any]
    risk_neutral: dict[str, Any]
    risk_conservative: dict[str, Any]
    risk_conclusion: dict[str, Any]

    # ── Final decision ────────────────────────────────────────────────────────
    final_decision: dict[str, Any]

    # ── Metadata ──────────────────────────────────────────────────────────────
    errors: list[str]
