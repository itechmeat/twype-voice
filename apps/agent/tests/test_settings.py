from __future__ import annotations

import pytest
from pydantic import ValidationError
from settings import AgentSettings


def test_settings_defaults(livekit_required_env: None) -> None:
    settings = AgentSettings()
    assert settings.LOG_LEVEL == "INFO"
    assert settings.STT_LANGUAGE == "multi"
    assert settings.STT_MODEL == "nova-3"
    assert settings.LLM_MODEL == "gemini-flash-lite"
    assert settings.LLM_TEMPERATURE == 0.7
    assert settings.LLM_MAX_TOKENS == 512

    assert settings.TTS_PROVIDER == "inworld"
    assert settings.INWORLD_API_KEY == "inworld_test_key"
    assert settings.TTS_INWORLD_VOICE == "Olivia"
    assert settings.TTS_INWORLD_MODEL == "inworld-tts-1.5-mini"
    assert settings.TTS_SPEAKING_RATE == 1.0
    assert settings.TTS_TEMPERATURE == 1.0
    assert settings.ELEVENLABS_API_KEY is None
    assert settings.TTS_ELEVENLABS_VOICE_ID == "EXAVITQu4vr4xnSDxMaL"
    assert settings.TTS_ELEVENLABS_MODEL == "eleven_flash_v2_5"
    assert settings.VAD_ACTIVATION_THRESHOLD == 0.5
    assert settings.VAD_MIN_SPEECH_DURATION == 0.05
    assert settings.VAD_MIN_SILENCE_DURATION == 0.3

    assert settings.TURN_DETECTION_MODE == "stt"
    assert settings.MIN_ENDPOINTING_DELAY == 0.5
    assert settings.MAX_ENDPOINTING_DELAY == 3.0
    assert settings.PREEMPTIVE_GENERATION is True
    assert settings.NOISE_CANCELLATION_ENABLED is True
    assert settings.FALSE_INTERRUPTION_TIMEOUT == 2.0
    assert settings.MIN_INTERRUPTION_DURATION == 0.5
    assert settings.THINKING_SOUNDS_ENABLED is True
    assert settings.THINKING_SOUNDS_DELAY == 1.5


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

    monkeypatch.setenv("TURN_DETECTION_MODE", "vad")
    monkeypatch.setenv("MIN_ENDPOINTING_DELAY", "0.3")
    monkeypatch.setenv("MAX_ENDPOINTING_DELAY", "5.0")
    monkeypatch.setenv("PREEMPTIVE_GENERATION", "false")
    monkeypatch.setenv("NOISE_CANCELLATION_ENABLED", "false")
    monkeypatch.setenv("FALSE_INTERRUPTION_TIMEOUT", "0")
    monkeypatch.setenv("MIN_INTERRUPTION_DURATION", "0.2")
    monkeypatch.setenv("THINKING_SOUNDS_ENABLED", "false")
    monkeypatch.setenv("THINKING_SOUNDS_DELAY", "2.0")

    monkeypatch.setenv("TTS_PROVIDER", "elevenlabs")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "eleven_test_key")
    monkeypatch.setenv("TTS_ELEVENLABS_VOICE_ID", "voice_123")
    monkeypatch.setenv("TTS_ELEVENLABS_MODEL", "eleven_flash_v2_5")

    settings = AgentSettings()
    assert settings.LOG_LEVEL == "DEBUG"
    assert settings.STT_LANGUAGE == "ru"
    assert settings.STT_MODEL == "nova-3"
    assert settings.VAD_ACTIVATION_THRESHOLD == 0.6
    assert settings.VAD_MIN_SPEECH_DURATION == 0.1
    assert settings.VAD_MIN_SILENCE_DURATION == 0.4

    assert settings.TURN_DETECTION_MODE == "vad"
    assert settings.MIN_ENDPOINTING_DELAY == 0.3
    assert settings.MAX_ENDPOINTING_DELAY == 5.0
    assert settings.PREEMPTIVE_GENERATION is False
    assert settings.NOISE_CANCELLATION_ENABLED is False
    assert settings.FALSE_INTERRUPTION_TIMEOUT == 0.0
    assert settings.MIN_INTERRUPTION_DURATION == 0.2
    assert settings.THINKING_SOUNDS_ENABLED is False
    assert settings.THINKING_SOUNDS_DELAY == 2.0
    assert settings.TTS_PROVIDER == "elevenlabs"
    assert settings.ELEVENLABS_API_KEY == "eleven_test_key"
    assert settings.TTS_ELEVENLABS_VOICE_ID == "voice_123"
    assert settings.TTS_ELEVENLABS_MODEL == "eleven_flash_v2_5"


def test_settings_inworld_tuning_overrides(
    monkeypatch: pytest.MonkeyPatch,
    livekit_required_env: None,
) -> None:
    monkeypatch.setenv("TTS_PROVIDER", "inworld")
    monkeypatch.setenv("TTS_SPEAKING_RATE", "0.8")
    monkeypatch.setenv("TTS_TEMPERATURE", "0.6")

    settings = AgentSettings()
    assert settings.TTS_PROVIDER == "inworld"
    assert settings.TTS_SPEAKING_RATE == 0.8
    assert settings.TTS_TEMPERATURE == 0.6


def test_settings_requires_inworld_api_key_when_inworld(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit")
    monkeypatch.setenv("LIVEKIT_API_KEY", "api-key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "api-secret")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg_test_key")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://twype:twype_secret@localhost:5433/twype_test",
    )
    monkeypatch.setenv("LITELLM_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "litellm_master_key")
    monkeypatch.setenv("TTS_PROVIDER", "inworld")
    monkeypatch.delenv("INWORLD_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        AgentSettings()


def test_settings_missing_required_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LITELLM_URL", raising=False)
    monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)

    with pytest.raises(ValidationError):
        AgentSettings()


def test_settings_rejects_invalid_turn_detection_mode(
    monkeypatch: pytest.MonkeyPatch,
    livekit_required_env: None,
) -> None:
    monkeypatch.setenv("TURN_DETECTION_MODE", "nope")
    with pytest.raises(ValidationError):
        AgentSettings()


def test_settings_rejects_non_positive_thinking_sounds_delay(
    monkeypatch: pytest.MonkeyPatch,
    livekit_required_env: None,
) -> None:
    monkeypatch.setenv("THINKING_SOUNDS_DELAY", "0")
    with pytest.raises(ValidationError):
        AgentSettings()
