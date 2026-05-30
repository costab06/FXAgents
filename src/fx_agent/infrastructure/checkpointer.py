"""LangGraph checkpoint persistence via PostgreSQL."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from .settings import Settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def make_checkpointer(settings: Settings) -> AsyncIterator[AsyncPostgresSaver]:
    """Async context manager that yields a ready-to-use AsyncPostgresSaver."""
    pool = AsyncConnectionPool(
        conninfo=settings.postgres_dsn,
        max_size=settings.postgres_pool_max_size,
        open=False,
    )
    await pool.open()
    try:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        logger.info("Checkpointer ready (postgres)")
        yield checkpointer
    finally:
        await pool.close()
