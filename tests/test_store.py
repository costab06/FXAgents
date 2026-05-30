"""Tests for the in-memory RunStore."""

import pytest
from fx_agent.server.store import RunStore
from fx_agent.server.models import RunEntry, RunStatus


def make_entry(pair="EURUSD"):
    return RunEntry(run_id="test-" + pair, pair=pair, date="2026-01-01")


def test_create_and_get():
    store = RunStore()
    entry = make_entry()
    store.create(entry)
    assert store.get(entry.run_id) is entry


def test_delete():
    store = RunStore()
    entry = make_entry()
    store.create(entry)
    assert store.delete(entry.run_id) is True
    assert store.get(entry.run_id) is None


def test_delete_missing():
    store = RunStore()
    assert store.delete("nonexistent") is False


def test_all_sorted():
    store = RunStore()
    for pair in ["EURUSD", "GBPUSD", "USDJPY"]:
        store.create(make_entry(pair))
    runs = store.all()
    assert len(runs) == 3
