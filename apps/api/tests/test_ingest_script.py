from __future__ import annotations

import importlib
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest


@pytest.fixture
def ingest_module(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delitem(sys.modules, "scripts.ingest", raising=False)
    module = importlib.import_module("scripts.ingest")
    monkeypatch.setitem(sys.modules, "scripts.ingest", module)
    return module


@pytest.mark.asyncio
async def test_run_logs_missing_google_api_key_without_traceback(
    ingest_module,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with caplog.at_level("ERROR"):
        result = await ingest_module._run(Path.cwd())

    assert result == 1
    assert "GOOGLE_API_KEY is not set" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.asyncio
async def test_run_logs_unexpected_runtime_errors_with_traceback(
    ingest_module,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "google_test_key")

    @asynccontextmanager
    async def fake_session_scope():
        yield object()

    async def fake_ingest_directory(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ingest_module, "session_scope", fake_session_scope)
    monkeypatch.setattr(ingest_module, "ingest_directory", fake_ingest_directory)

    with caplog.at_level("ERROR"):
        result = await ingest_module._run(Path.cwd())

    assert result == 1
    assert "Knowledge ingestion failed" in caplog.text
    assert any(record.exc_info is not None for record in caplog.records)
