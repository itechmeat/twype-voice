from __future__ import annotations

import sys
from pathlib import Path

import pytest

agent_root = Path(__file__).resolve().parents[1]
src_dir = agent_root / "src"
sys.path.insert(0, str(src_dir))

@pytest.fixture
def livekit_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit")
    monkeypatch.setenv("LIVEKIT_API_KEY", "api-key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "api-secret")
