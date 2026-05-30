"""Shared event model for the FX agent ingest pipeline."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

UTC = timezone.utc


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataEvent(BaseModel):
    """A single data event published to the Redis event bus."""

    event_id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    source: str                          # "fx_market" | "macro" | "news" | "social"
    data_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    pair: str = ""                       # e.g. "EURUSD"
    urgency: Urgency = Urgency.MEDIUM
    payload: dict[str, Any] = Field(default_factory=dict)
