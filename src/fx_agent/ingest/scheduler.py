"""Session-based scheduler — triggers analysis at London and New York opens."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from ..infrastructure.event_bus import EventBus
from ..infrastructure.models import DataEvent, Urgency
from ..infrastructure.settings import Settings

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


class SessionScheduler:
    """Fires a 'session_open' event at configured London and New York open times (ET)."""

    def __init__(self, bus: EventBus, settings: Settings) -> None:
        self._bus = bus
        self._settings = settings
        self._running = False
        self._fired: set[str] = set()  # "YYYY-MM-DD:session"

    async def run(self) -> None:
        self._running = True
        logger.info("SessionScheduler started")
        while self._running:
            now_et = datetime.now(ET)
            date_str = now_et.strftime("%Y-%m-%d")
            time_str = now_et.strftime("%H:%M")

            for session, open_time in [
                ("london", self._settings.london_open_et),
                ("newyork", self._settings.newyork_open_et),
            ]:
                key = f"{date_str}:{session}"
                if time_str >= open_time and key not in self._fired:
                    self._fired.add(key)
                    await self._fire_session_event(session, date_str)

            # Clean up fired keys from past days
            today = now_et.strftime("%Y-%m-%d")
            self._fired = {k for k in self._fired if k.startswith(today)}

            await asyncio.sleep(30)

    async def _fire_session_event(self, session: str, date_str: str) -> None:
        for pair in self._settings.default_pairs:
            event = DataEvent(
                source="fx_market",
                pair=pair,
                urgency=Urgency.HIGH,
                payload={
                    "event_type": "session_open",
                    "session": session,
                    "date": date_str,
                },
            )
            await self._bus.publish(event)
        logger.info("SessionScheduler: fired %s open for %d pairs", session, len(self._settings.default_pairs))

    def stop(self) -> None:
        self._running = False
