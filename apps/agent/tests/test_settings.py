from __future__ import annotations

import pytest
from pydantic import ValidationError
from settings import AgentSettings


def test_settings_defaults(livekit_required_env: None) -> None:
    settings = AgentSettings()
    assert settings.LOG_LEVEL == "INFO"
    assert settings.STT_LANGUAGE == "multi"
    assert settings.STT_MODEL == "nova-3"
    assert settings.VAD_ACTIVATION_THRESHOLD == 0.5
    assert settings.VAD_MIN_SPEECH_DURATION == 0.05
    assert settings.VAD_MIN_SILENCE_DURATION == 0.3


def test_settings_env_overrides(
    monkeypatch: pytest.MonkeyPatch,
    livekit_required_env: None,
) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("STT_LANGUAGE", "ru")
    monkeypatch.setenv("STT_MODEL", "nova-3")
    monkeypatch.setenv("VAD_ACTIVATION_THRESHOLD", "0.6")
    monkeypatch.setenv("VAD_MIN_SPEECH_DURATION", "0.1")
    monkeypatch.setenv("VAD_MIN_SILENCE_DURATION", "0.4")

    settings = AgentSettings()
    assert settings.LOG_LEVEL == "DEBUG"
    assert settings.STT_LANGUAGE == "ru"
    assert settings.STT_MODEL == "nova-3"
    assert settings.VAD_ACTIVATION_THRESHOLD == 0.6
    assert settings.VAD_MIN_SPEECH_DURATION == 0.1
    assert settings.VAD_MIN_SILENCE_DURATION == 0.4


def test_settings_missing_required_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        AgentSettings()
