"""Abstract base class for all ingest workers."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from ..infrastructure.event_bus import EventBus
from ..infrastructure.models import DataEvent
from ..infrastructure.settings import Settings

logger = logging.getLogger(__name__)


class BaseIngestor(ABC):
    """Periodically fetch data and publish DataEvents to the event bus."""

    def __init__(self, bus: EventBus, settings: Settings) -> None:
        self._bus = bus
        self._settings = settings
        self._running = False

    @property
    @abstractmethod
    def source(self) -> str:
        """Stream source name (e.g. 'fx_market')."""

    @property
    @abstractmethod
    def poll_interval_seconds(self) -> int:
        """How often to fetch data."""

    @abstractmethod
    async def fetch(self) -> list[DataEvent]:
        """Fetch data and return a list of DataEvents to publish."""

    async def run(self) -> None:
        self._running = True
        logger.info("%s ingestor started (interval=%ds)", self.source, self.poll_interval_seconds)
        while self._running:
            try:
                events = await self.fetch()
                for event in events:
                    await self._bus.publish(event)
                logger.debug("%s ingestor published %d events", self.source, len(events))
            except Exception:
                logger.exception("%s ingestor fetch failed", self.source)
            await asyncio.sleep(self.poll_interval_seconds)

    def stop(self) -> None:
        self._running = False
