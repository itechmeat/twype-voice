from __future__ import annotations

import pytest
from livekit.plugins import elevenlabs, inworld
from settings import AgentSettings
from tts import build_tts


def test_build_tts_inworld_returns_plugin(livekit_required_env: None) -> None:
    settings = AgentSettings()
    tts = build_tts(settings)
    assert isinstance(tts, inworld.TTS)


def test_build_tts_elevenlabs_returns_plugin(monkeypatch, livekit_required_env: None) -> None:
    monkeypatch.setenv("TTS_PROVIDER", "elevenlabs")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "eleven_test_key")

    settings = AgentSettings()
    tts = build_tts(settings)
    assert isinstance(tts, elevenlabs.TTS)


def test_build_tts_inworld_language_mapping_overrides_settings_voice(
    monkeypatch,
    livekit_required_env: None,
) -> None:
    monkeypatch.setenv("TTS_INWORLD_VOICE", "Ashley")

    settings = AgentSettings()

    import tts as tts_module

    class DummyTTS:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(tts_module.inworld, "TTS", DummyTTS)

    mapped = tts_module.build_tts(settings, language="en")
    assert mapped.kwargs["voice"] == "Olivia"

    unmapped = tts_module.build_tts(settings)
    assert unmapped.kwargs["voice"] == "Ashley"


def test_build_tts_elevenlabs_language_mapping_overrides_settings_voice_id(
    monkeypatch,
    livekit_required_env: None,
) -> None:
    monkeypatch.setenv("TTS_PROVIDER", "elevenlabs")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "eleven_test_key")
    monkeypatch.setenv("TTS_ELEVENLABS_VOICE_ID", "voice_custom")

    settings = AgentSettings()

    import tts as tts_module

    class DummyTTS:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(tts_module.elevenlabs, "TTS", DummyTTS)

    mapped = tts_module.build_tts(settings, language="ru")
    assert mapped.kwargs["voice_id"] == "EXAVITQu4vr4xnSDxMaL"
    assert mapped.kwargs["language"] == "ru"

    unmapped = tts_module.build_tts(settings)
    assert unmapped.kwargs["voice_id"] == "voice_custom"
    assert unmapped.kwargs["language"] == "en"


def test_build_tts_unsupported_provider_raises(livekit_required_env: None) -> None:
    settings = AgentSettings()
    object.__setattr__(settings, "TTS_PROVIDER", "unsupported")

    import tts as tts_module

    with pytest.raises(ValueError, match="Unsupported TTS_PROVIDER"):
        tts_module.build_tts(settings)
