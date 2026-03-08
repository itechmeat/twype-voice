from __future__ import annotations

import sys
from pathlib import Path

import pytest

from testsupport import default_test_database_url

agent_root = Path(__file__).resolve().parents[1]
src_dir = agent_root / "src"
sys.path.insert(0, str(src_dir))


@pytest.fixture
def livekit_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit")
    monkeypatch.setenv("LIVEKIT_API_KEY", "api-key-for-tests")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "api-secret-for-tests-with-32-bytes")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg_test_key")
    monkeypatch.setenv("DATABASE_URL", default_test_database_url(scope="agent"))
    monkeypatch.setenv("GOOGLE_API_KEY", "google_test_key")

    monkeypatch.setenv("LITELLM_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "litellm_master_key")

    monkeypatch.setenv("INWORLD_API_KEY", "inworld_test_key")
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
