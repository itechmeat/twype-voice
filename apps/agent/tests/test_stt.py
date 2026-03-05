from __future__ import annotations

from typing import Any

from livekit.plugins import deepgram
from settings import AgentSettings
from stt import build_stt


def test_build_stt_config(monkeypatch, livekit_required_env: None) -> None:
    captured: dict[str, Any] = {}

    def fake_stt(**kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(deepgram, "STT", fake_stt)

    settings = AgentSettings()
    build_stt(settings)

    assert captured["api_key"] == settings.DEEPGRAM_API_KEY
    assert captured["model"] == settings.STT_MODEL
    assert captured["language"] == settings.STT_LANGUAGE
