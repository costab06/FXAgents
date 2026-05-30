"""Technical analyst — OHLCV indicators for FX pairs."""

from __future__ import annotations

import json
import logging

from ..infrastructure.llm import LLMCallable
from ..infrastructure.settings import Settings
from ..ingest.fx_market import fetch_fx_ohlcv
from .base import compute_atr, compute_rsi, compute_sma, pips_from_price

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a professional FX technical analyst with expertise in
price action, momentum indicators, and support/resistance levels.

Given OHLCV data and computed technical indicators for a currency pair, provide
a structured technical analysis.

Respond with JSON only (no markdown fences):
{
  "key_points": ["...", "..."],
  "trend": "uptrend|downtrend|ranging",
  "momentum": "bullish|bearish|neutral",
  "key_support": 0.0,
  "key_resistance": 0.0,
  "recommended_direction": "buy|sell|hold",
  "entry_price": 0.0,
  "stop_loss_pips": 0,
  "take_profit_pips": 0,
  "confidence": 0.0-1.0,
  "summary": "..."
}"""


async def run_technical_analyst(
    pair: str,
    llm: LLMCallable,
    settings: Settings,
) -> dict:
    """Fetch OHLCV data, compute indicators, and run technical analysis."""
    ohlcv = await fetch_fx_ohlcv(pair, period="90d", interval="1d")

    if not ohlcv or len(ohlcv.get("close", [])) < 20:
        logger.warning("technical_analyst: insufficient data for %s", pair)
        user_msg = f"""Currency pair: {pair}
OHLCV data: unavailable (insufficient history).

Provide a technical analysis based on general market knowledge for {pair}."""
    else:
        closes = ohlcv["close"]
        highs = ohlcv["high"]
        lows = ohlcv["low"]

        sma20 = compute_sma(closes, 20)
        sma50 = compute_sma(closes, 50)
        rsi14 = compute_rsi(closes, 14)
        atr14 = compute_atr(highs, lows, closes, 14)

        current = closes[-1]
        high_20 = max(highs[-20:])
        low_20 = min(lows[-20:])

        atr_pips = pips_from_price(atr14, pair) if atr14 else None

        user_msg = f"""Currency pair: {pair}
Current price: {current:.5f}
20-day high: {high_20:.5f}
20-day low: {low_20:.5f}
SMA-20: {sma20:.5f if sma20 else 'N/A'}
SMA-50: {sma50:.5f if sma50 else 'N/A'}
RSI-14: {rsi14:.1f if rsi14 else 'N/A'}
ATR-14: {atr_pips:.1f} pips (price: {atr14:.5f}) if atr14 else 'N/A'
Bars analysed: {len(closes)} daily candles

Recent closes (last 10): {[f'{c:.5f}' for c in closes[-10:]]}

Provide a full technical analysis for {pair}."""

    raw = await llm(SYSTEM_PROMPT, user_msg)
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(text)
    except Exception:
        logger.warning("technical_analyst: failed to parse LLM response")
        result = {
            "key_points": [raw[:500]],
            "trend": "ranging",
            "recommended_direction": "hold",
            "confidence": 0.3,
            "summary": raw[:300],
        }

    return result
