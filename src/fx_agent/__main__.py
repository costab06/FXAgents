"""Entry point: python -m fx_agent [mode]

Modes:
  server      (default) — FastAPI REST server
  router      — event bus router
  ingest      — FX market data ingestor + session scheduler
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _run_server() -> None:
    import uvicorn
    from .infrastructure.settings import Settings
    settings = Settings()

    key = settings.anthropic_api_key
    if key:
        logger.info("ANTHROPIC_API_KEY loaded: %s...%s (len=%d)", key[:12], key[-4:], len(key))
    else:
        logger.warning("ANTHROPIC_API_KEY not set — LLM calls will fail")

    uvicorn.run(
        "fx_agent.server.app:app",
        host=settings.server_host,
        port=settings.server_port,
        log_level="info",
    )


async def _run_router() -> None:
    from .infrastructure.event_bus import EventBus
    from .infrastructure.router import Router
    from .infrastructure.settings import Settings

    settings = Settings()
    bus = EventBus(settings)
    await bus.connect()
    router = Router(bus, settings)
    try:
        await router.run()
    finally:
        await bus.close()


async def _run_ingest() -> None:
    from .infrastructure.event_bus import EventBus
    from .infrastructure.settings import Settings
    from .ingest.fx_market import FXMarketIngestor
    from .ingest.scheduler import SessionScheduler

    settings = Settings()
    bus = EventBus(settings)
    await bus.connect()

    ingestor = FXMarketIngestor(bus, settings)
    scheduler = SessionScheduler(bus, settings)

    try:
        await asyncio.gather(ingestor.run(), scheduler.run())
    finally:
        await bus.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="fx_agent")
    parser.add_argument(
        "mode",
        nargs="?",
        default="server",
        choices=["server", "router", "ingest"],
    )
    args = parser.parse_args()

    if args.mode == "server":
        _run_server()
    elif args.mode == "router":
        asyncio.run(_run_router())
    elif args.mode == "ingest":
        asyncio.run(_run_ingest())
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
