"""Macro analyst — central bank policy and macroeconomic context."""

from __future__ import annotations

import asyncio
import json
import logging

from ..infrastructure.llm import LLMCallable
from ..infrastructure.settings import FRED_RATE_SERIES, Settings
from .base import fetch_fred_rate

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior FX macro analyst specialising in central bank policy,
interest rate dynamics, and macroeconomic fundamentals.

Given the current interest rates for two currencies and recent monetary policy context,
provide a structured analysis of the macro outlook for the currency pair.

Respond with JSON only (no markdown fences):
{
  "key_points": ["...", "..."],
  "base_currency_bias": "hawkish|neutral|dovish",
  "quote_currency_bias": "hawkish|neutral|dovish",
  "macro_direction": "bullish_base|bearish_base|neutral",
  "confidence": 0.0-1.0,
  "summary": "..."
}"""


async def run_macro_analyst(
    pair: str,
    llm: LLMCallable,
    settings: Settings,
) -> dict:
    """Fetch FRED rates and produce a macro analysis for the given pair."""
    base = pair[:3].upper()
    quote = pair[3:].upper()

    base_series = FRED_RATE_SERIES.get(base)
    quote_series = FRED_RATE_SERIES.get(quote)

    base_rate, quote_rate = None, None
    if settings.fred_api_key:
        base_rate, quote_rate = await asyncio.gather(
            fetch_fred_rate(base_series, settings.fred_api_key) if base_series else _noop(),
            fetch_fred_rate(quote_series, settings.fred_api_key) if quote_series else _noop(),
        )

    rate_diff = None
    if base_rate is not None and quote_rate is not None:
        rate_diff = round(base_rate - quote_rate, 4)

    user_msg = f"""Currency pair: {pair}
Base currency ({base}) policy rate: {base_rate if base_rate is not None else 'unavailable'} %
Quote currency ({quote}) policy rate: {quote_rate if quote_rate is not None else 'unavailable'} %
Rate differential ({base} minus {quote}): {rate_diff if rate_diff is not None else 'unavailable'} pp

FRED series used: {base}: {base_series or 'N/A'}, {quote}: {quote_series or 'N/A'}

Analyse the macro outlook for {pair} based on the above data and your knowledge of
current central bank policy stances."""

    raw = await llm(SYSTEM_PROMPT, user_msg)
    try:
        # strip markdown fences if present
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(text)
    except Exception:
        logger.warning("macro_analyst: failed to parse LLM response, using fallback")
        result = {
            "key_points": [raw[:500]],
            "macro_direction": "neutral",
            "confidence": 0.3,
            "summary": raw[:300],
        }

    result["base_rate"] = base_rate
    result["quote_rate"] = quote_rate
    result["rate_diff_pp"] = rate_diff
    return result


async def _noop():
    return None
