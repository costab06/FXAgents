"""In-memory store for pipeline run entries."""

from __future__ import annotations

import threading
from typing import Iterator

from .models import RunEntry


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunEntry] = {}
        self._lock = threading.Lock()

    def create(self, entry: RunEntry) -> RunEntry:
        with self._lock:
            self._runs[entry.run_id] = entry
        return entry

    def get(self, run_id: str) -> RunEntry | None:
        return self._runs.get(run_id)

    def update(self, entry: RunEntry) -> None:
        with self._lock:
            self._runs[entry.run_id] = entry

    def delete(self, run_id: str) -> bool:
        with self._lock:
            return self._runs.pop(run_id, None) is not None

    def all(self) -> list[RunEntry]:
        with self._lock:
            return sorted(self._runs.values(), key=lambda e: e.created_at, reverse=True)

    def __iter__(self) -> Iterator[RunEntry]:
        return iter(self.all())
