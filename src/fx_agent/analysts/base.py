"""Shared utilities for FX analysts."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# Expanded search terms per currency code so filtering doesn't match on
# three-letter substrings like "eur" appearing in "Europe" or "entrepreneur".
_CURRENCY_TERMS: dict[str, list[str]] = {
    "EUR": ["euro ", "euros", " eur ", "ecb", "european central bank", "eurozone", "lagarde"],
    "USD": ["dollar", " usd ", "federal reserve", " fed ", "fomc", "powell"],
    "GBP": ["sterling", " gbp ", "pound", "bank of england", " boe ", "bailey"],
    "JPY": [" yen", " jpy ", "bank of japan", " boj ", "ueda"],
    "CHF": ["franc", " chf ", "snb", "swiss national bank"],
    "AUD": ["aussie", " aud ", "reserve bank of australia", " rba "],
    "CAD": ["loonie", " cad ", "bank of canada"],
    "NZD": ["kiwi", " nzd ", "rbnz", "reserve bank of new zealand"],
    "SEK": ["krona", " sek ", "riksbank"],
    "NOK": ["krone", " nok ", "norges bank"],
}


def _matches_pair(article: dict, base: str, quote: str) -> bool:
    text = (
        (article.get("headline") or "") + " " + (article.get("summary") or "")
    ).lower()
    base_terms = _CURRENCY_TERMS.get(base.upper(), [base.lower()])
    quote_terms = _CURRENCY_TERMS.get(quote.upper(), [quote.lower()])
    return any(t in text for t in base_terms) or any(t in text for t in quote_terms)


async def fetch_finnhub_fx_news(pair: str, api_key: str, days: int = 7) -> list[dict]:
    """Fetch forex news from Finnhub for a currency pair."""
    if not api_key:
        return []

    base = pair[:3]
    quote = pair[3:]

    def _sync() -> list[dict]:
        import finnhub
        client = finnhub.Client(api_key=api_key)
        try:
            articles = client.general_news(category="forex") or []
            relevant = [a for a in articles if _matches_pair(a, base, quote)]
            return [
                {
                    "title": a.get("headline", ""),
                    "publisher": a.get("source", ""),
                    "summary": a.get("summary", ""),
                    "datetime": a.get("datetime", ""),
                }
                for a in relevant[:15]
            ]
        except Exception:
            logger.exception("fetch_finnhub_fx_news failed pair=%s", pair)
            return []

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync)


async def fetch_finnhub_forex_candles(
    pair: str, api_key: str, resolution: str = "D", count: int = 90
) -> dict:
    """Fetch OHLCV candles via Finnhub forex endpoint."""
    if not api_key:
        return {}

    def _sync() -> dict:
        import time
        import finnhub
        client = finnhub.Client(api_key=api_key)
        # Finnhub symbol: "OANDA:EUR_USD"
        base = pair[:3]
        quote = pair[3:]
        symbol = f"OANDA:{base}_{quote}"
        to_ts = int(time.time())
        # resolution D = daily, count days back
        seconds_back = count * 24 * 3600
        from_ts = to_ts - seconds_back
        try:
            candles = client.forex_candles(symbol, resolution, from_ts, to_ts)
            if candles.get("s") != "ok":
                return {}
            return {
                "timestamps": candles.get("t", []),
                "open": candles.get("o", []),
                "high": candles.get("h", []),
                "low": candles.get("l", []),
                "close": candles.get("c", []),
                "volume": candles.get("v", []),
            }
        except Exception:
            logger.exception("fetch_finnhub_forex_candles failed pair=%s", pair)
            return {}

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync)


async def fetch_fred_rate(series_id: str, api_key: str) -> float | None:
    """Fetch the latest value for a FRED series."""
    if not api_key or not series_id:
        return None

    def _sync() -> float | None:
        try:
            from fredapi import Fred
            fred = Fred(api_key=api_key)
            series = fred.get_series(series_id)
            if series is None or series.empty:
                return None
            return float(series.dropna().iloc[-1])
        except Exception:
            logger.exception("fetch_fred_rate series=%s failed", series_id)
            return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync)


def compute_sma(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return sum(trs[-period:]) / period


def pips_from_price(price_diff: float, pair: str) -> float:
    """Convert a price difference to pips based on the pair."""
    # JPY pairs: 1 pip = 0.01; others: 1 pip = 0.0001
    if "JPY" in pair:
        return round(price_diff / 0.01, 1)
    return round(price_diff / 0.0001, 1)
