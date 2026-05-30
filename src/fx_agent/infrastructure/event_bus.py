"""Redis Streams event bus — publish/consume DataEvents with consumer groups."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import redis.asyncio as aioredis

from .models import DataEvent
from .settings import Settings

logger = logging.getLogger(__name__)


class EventBus:
    """Thin wrapper around Redis Streams for publishing and consuming DataEvents."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(
            self._settings.redis_url,
            decode_responses=True,
        )
        await self._redis.ping()
        logger.info("EventBus connected to %s", self._settings.redis_url)

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()

    # ── Publishing ────────────────────────────────────────────────────────────

    async def publish(self, event: DataEvent) -> str:
        """Append event to the appropriate ingest stream; return the Redis message ID."""
        assert self._redis, "call connect() first"
        stream = self._settings.ingest_prefix + event.source
        payload = {"data": event.model_dump_json()}
        msg_id = await self._redis.xadd(
            stream,
            payload,
            maxlen=self._settings.max_stream_length,
            approximate=True,
        )
        logger.debug("EventBus.publish stream=%s id=%s", stream, msg_id)
        return msg_id

    # ── Consuming ─────────────────────────────────────────────────────────────

    async def ensure_group(self, stream: str, group: str) -> None:
        """Create consumer group (idempotent)."""
        assert self._redis
        try:
            await self._redis.xgroup_create(stream, group, id="0", mkstream=True)
        except aioredis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def consume(
        self,
        stream: str,
        group: str,
        consumer: str,
        *,
        count: int = 10,
        block_ms: int = 2_000,
    ) -> AsyncIterator[tuple[str, DataEvent]]:
        """Yield (msg_id, event) tuples from a consumer-group read."""
        assert self._redis
        await self.ensure_group(stream, group)
        while True:
            results = await self._redis.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: ">"},
                count=count,
                block=block_ms,
            )
            if not results:
                await asyncio.sleep(0)
                continue
            for _stream, messages in results:
                for msg_id, fields in messages:
                    try:
                        event = DataEvent.model_validate_json(fields["data"])
                    except Exception:
                        logger.exception("Failed to parse DataEvent msg_id=%s", msg_id)
                        await self.ack(stream, group, msg_id)
                        continue
                    yield msg_id, event

    async def ack(self, stream: str, group: str, msg_id: str) -> None:
        assert self._redis
        await self._redis.xack(stream, group, msg_id)

    # ── Idempotency ───────────────────────────────────────────────────────────

    async def is_duplicate(self, event_id: str) -> bool:
        """Return True if this event_id was already processed."""
        assert self._redis
        key = f"idempotency:{event_id}"
        result = await self._redis.set(
            key, "1", ex=self._settings.idempotency_ttl_seconds, nx=True
        )
        return result is None  # None means key already existed

    # ── Dead-letter queue ─────────────────────────────────────────────────────

    async def send_to_dlq(self, event: DataEvent, reason: str) -> None:
        assert self._redis
        payload = {"data": event.model_dump_json(), "reason": reason}
        await self._redis.xadd(
            self._settings.dlq_stream,
            payload,
            maxlen=self._settings.max_stream_length,
            approximate=True,
        )
        logger.warning("EventBus.dlq event_id=%s reason=%s", event.event_id, reason)

    # ── Agent streams ─────────────────────────────────────────────────────────

    async def publish_to_agent(self, agent: str, payload: dict) -> str:
        """Publish a dict payload to an agent stream."""
        assert self._redis
        stream = self._settings.agent_prefix + agent
        msg_id = await self._redis.xadd(
            stream,
            {"data": json.dumps(payload)},
            maxlen=self._settings.max_stream_length,
            approximate=True,
        )
        return msg_id

    async def consume_agent(
        self,
        agent: str,
        group: str,
        consumer: str,
        *,
        count: int = 1,
        block_ms: int = 2_000,
    ) -> AsyncIterator[tuple[str, dict]]:
        stream = self._settings.agent_prefix + agent
        assert self._redis
        await self.ensure_group(stream, group)
        while True:
            results = await self._redis.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: ">"},
                count=count,
                block=block_ms,
            )
            if not results:
                await asyncio.sleep(0)
                continue
            for _stream, messages in results:
                for msg_id, fields in messages:
                    try:
                        data = json.loads(fields["data"])
                    except Exception:
                        logger.exception("Failed to parse agent msg_id=%s", msg_id)
                        await self.ack(stream, group, msg_id)
                        continue
                    yield msg_id, data
