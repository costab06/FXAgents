"""Router — forward DataEvents from ingest streams to the orchestrator agent stream."""

from __future__ import annotations

import asyncio
import logging

from .event_bus import EventBus
from .models import DataEvent
from .settings import Settings

logger = logging.getLogger(__name__)


class Router:
    """Reads all ingest streams and forwards events to configured agent streams."""

    def __init__(self, bus: EventBus, settings: Settings) -> None:
        self._bus = bus
        self._settings = settings
        self._running = False

    async def run(self) -> None:
        self._running = True
        tasks = [
            asyncio.create_task(self._consume_source(source), name=f"router:{source}")
            for source in self._settings.routing
        ]
        logger.info("Router started for sources: %s", list(self._settings.routing))
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for t in tasks:
                t.cancel()
            raise

    async def _consume_source(self, source: str) -> None:
        stream = self._settings.ingest_prefix + source
        group = "router"
        consumer = f"router-{source}"
        async for msg_id, event in self._bus.consume(stream, group, consumer):
            if not self._running:
                break
            if await self._bus.is_duplicate(event.event_id):
                logger.debug("Router: duplicate event_id=%s, skipping", event.event_id)
                await self._bus.ack(stream, group, msg_id)
                continue
            targets = self._settings.routing.get(source, [])
            for agent in targets:
                await self._bus.publish_to_agent(
                    agent,
                    {"event": event.model_dump(mode="json")},
                )
                logger.debug(
                    "Router routed event_id=%s source=%s -> agent=%s",
                    event.event_id, source, agent,
                )
            await self._bus.ack(stream, group, msg_id)

    def stop(self) -> None:
        self._running = False
