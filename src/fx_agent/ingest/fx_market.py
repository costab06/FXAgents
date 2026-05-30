"""FX market data ingestor — OHLCV snapshots via yfinance."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import yfinance as yf

from ..infrastructure.event_bus import EventBus
from ..infrastructure.models import DataEvent, Urgency
from ..infrastructure.settings import Settings
from .base import BaseIngestor

logger = logging.getLogger(__name__)

UTC = timezone.utc


def _yf_ticker(pair: str) -> str:
    """Convert 'EURUSD' → 'EURUSD=X' for yfinance."""
    if pair.endswith("=X"):
        return pair
    return pair + "=X"


class FXMarketIngestor(BaseIngestor):
    """Polls yfinance for FX OHLCV data for each configured pair."""

    def __init__(self, bus: EventBus, settings: Settings, poll_interval: int = 300) -> None:
        super().__init__(bus, settings)
        self._poll_interval = poll_interval

    @property
    def source(self) -> str:
        return "fx_market"

    @property
    def poll_interval_seconds(self) -> int:
        return self._poll_interval

    async def fetch(self) -> list[DataEvent]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_sync)

    def _fetch_sync(self) -> list[DataEvent]:
        events: list[DataEvent] = []
        for pair in self._settings.default_pairs:
            try:
                ticker = _yf_ticker(pair)
                hist = yf.Ticker(ticker).history(period="5d", interval="1h")
                if hist.empty:
                    logger.warning("FXMarketIngestor: no data for %s", pair)
                    continue
                latest = hist.iloc[-1]
                payload = {
                    "open": float(latest["Open"]),
                    "high": float(latest["High"]),
                    "low": float(latest["Low"]),
                    "close": float(latest["Close"]),
                    "volume": float(latest.get("Volume", 0)),
                    "timestamp": str(hist.index[-1]),
                    "period": "1h",
                    "bars_available": len(hist),
                }
                events.append(
                    DataEvent(
                        source="fx_market",
                        pair=pair,
                        urgency=Urgency.MEDIUM,
                        payload=payload,
                    )
                )
                logger.debug("FXMarketIngestor: fetched %s close=%.5f", pair, payload["close"])
            except Exception:
                logger.exception("FXMarketIngestor: error fetching %s", pair)
        return events


async def fetch_fx_ohlcv(pair: str, period: str = "60d", interval: str = "1d") -> dict:
    """Fetch OHLCV history for a pair; returns dict with lists for each column."""
    loop = asyncio.get_event_loop()

    def _sync() -> dict:
        ticker = _yf_ticker(pair)
        hist = yf.Ticker(ticker).history(period=period, interval=interval)
        if hist.empty:
            return {}
        return {
            "dates": [str(d) for d in hist.index],
            "open": hist["Open"].tolist(),
            "high": hist["High"].tolist(),
            "low": hist["Low"].tolist(),
            "close": hist["Close"].tolist(),
            "volume": hist.get("Volume", hist["Close"] * 0).tolist(),
        }

    return await loop.run_in_executor(None, _sync)
