"""Carry analyst — interest rate differential and carry trade attractiveness."""

from __future__ import annotations

import asyncio
import json
import logging

from ..infrastructure.llm import LLMCallable
from ..infrastructure.settings import FRED_RATE_SERIES, Settings
from .base import fetch_fred_rate

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an FX carry trade specialist. You evaluate whether a currency
pair offers an attractive carry trade opportunity based on interest rate differentials,
risk sentiment, and current market conditions.

Respond with JSON only (no markdown fences):
{
  "key_points": ["...", "..."],
  "carry_direction": "long_base|long_quote|neutral",
  "annualised_carry_pp": 0.0,
  "risk_adjusted_attractiveness": "high|medium|low",
  "recommended_direction": "buy|sell|hold",
  "confidence": 0.0-1.0,
  "summary": "..."
}"""


async def run_carry_analyst(
    pair: str,
    llm: LLMCallable,
    settings: Settings,
    macro_data: dict | None = None,
) -> dict:
    """Analyse carry trade attractiveness for the pair."""
    base = pair[:3].upper()
    quote = pair[3:].upper()

    # Reuse rates from macro data if available
    base_rate = macro_data.get("base_rate") if macro_data else None
    quote_rate = macro_data.get("quote_rate") if macro_data else None

    if (base_rate is None or quote_rate is None) and settings.fred_api_key:
        base_series = FRED_RATE_SERIES.get(base)
        quote_series = FRED_RATE_SERIES.get(quote)
        base_rate, quote_rate = await asyncio.gather(
            fetch_fred_rate(base_series, settings.fred_api_key) if base_series else _noop(),
            fetch_fred_rate(quote_series, settings.fred_api_key) if quote_series else _noop(),
        )

    rate_diff = None
    if base_rate is not None and quote_rate is not None:
        rate_diff = round(base_rate - quote_rate, 4)

    user_msg = f"""Currency pair: {pair}
{base} overnight rate: {base_rate if base_rate is not None else 'unavailable'} %
{quote} overnight rate: {quote_rate if quote_rate is not None else 'unavailable'} %
Rate differential ({base} minus {quote}): {rate_diff if rate_diff is not None else 'unavailable'} pp

Evaluate whether a carry trade (borrowing low-rate currency, investing in high-rate currency)
is currently attractive. Consider roll costs, FX volatility risk, and global risk sentiment."""

    raw = await llm(SYSTEM_PROMPT, user_msg)
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(text)
    except Exception:
        logger.warning("carry_analyst: failed to parse LLM response")
        result = {
            "key_points": [raw[:500]],
            "carry_direction": "neutral",
            "recommended_direction": "hold",
            "confidence": 0.3,
            "summary": raw[:300],
        }

    result["base_rate"] = base_rate
    result["quote_rate"] = quote_rate
    result["rate_diff_pp"] = rate_diff
    return result


async def _noop():
    return None
