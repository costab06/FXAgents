"""Pydantic models for the FX agent REST API."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

UTC = timezone.utc


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunEntry(BaseModel):
    run_id: str
    pair: str
    date: str
    status: RunStatus = RunStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    log: list[str] = Field(default_factory=list)


class StartRunRequest(BaseModel):
    pair: str


class RunSummary(BaseModel):
    run_id: str
    pair: str
    date: str
    status: RunStatus
    created_at: datetime
    completed_at: datetime | None = None
    direction: str | None = None
    confidence: float | None = None
