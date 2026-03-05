from __future__ import annotations

from types import SimpleNamespace

import main as main_module
import pytest
from settings import AgentSettings


def test_prewarm_initializes_noise_cancellation_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    livekit_required_env: None,
) -> None:
    settings = AgentSettings()
    monkeypatch.setattr(main_module, "_settings", settings)

    monkeypatch.setattr(main_module, "build_vad", lambda _settings: "vad")
    monkeypatch.setattr(main_module, "build_stt", lambda _settings: "stt")
    monkeypatch.setattr(main_module, "build_llm", lambda _settings: "llm")
    monkeypatch.setattr(main_module, "build_tts", lambda _settings, language=None: "tts")
    monkeypatch.setattr(main_module, "build_engine", lambda _settings: "engine")
    monkeypatch.setattr(main_module, "build_sessionmaker", lambda _engine: "sessionmaker")
    monkeypatch.setattr(main_module, "configure_transcript_store", lambda _sm: None)

    import livekit.plugins.noise_cancellation as nc

    calls: dict[str, int] = {"load": 0, "bvc": 0}

    def fake_load() -> None:
        calls["load"] += 1

    def fake_bvc() -> str:
        calls["bvc"] += 1
        return "bvc-options"

    monkeypatch.setattr(nc, "load", fake_load)
    monkeypatch.setattr(nc, "BVC", fake_bvc)

    proc = SimpleNamespace(userdata={})
    main_module.prewarm(proc)  # type: ignore[arg-type]

    assert calls["load"] == 1
    assert calls["bvc"] == 1
    assert proc.userdata["noise_cancellation"] == "bvc-options"


def test_prewarm_skips_noise_cancellation_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
    livekit_required_env: None,
) -> None:
    monkeypatch.setenv("NOISE_CANCELLATION_ENABLED", "false")
    settings = AgentSettings()
    monkeypatch.setattr(main_module, "_settings", settings)

    monkeypatch.setattr(main_module, "build_vad", lambda _settings: "vad")
    monkeypatch.setattr(main_module, "build_stt", lambda _settings: "stt")
    monkeypatch.setattr(main_module, "build_llm", lambda _settings: "llm")
    monkeypatch.setattr(main_module, "build_tts", lambda _settings, language=None: "tts")
    monkeypatch.setattr(main_module, "build_engine", lambda _settings: "engine")
    monkeypatch.setattr(main_module, "build_sessionmaker", lambda _engine: "sessionmaker")
    monkeypatch.setattr(main_module, "configure_transcript_store", lambda _sm: None)

    import livekit.plugins.noise_cancellation as nc

    def fail_load() -> None:
        raise AssertionError("noise_cancellation.load() should not be called")

    def fail_bvc() -> str:
        raise AssertionError("noise_cancellation.BVC() should not be called")

    monkeypatch.setattr(nc, "load", fail_load)
    monkeypatch.setattr(nc, "BVC", fail_bvc)

    proc = SimpleNamespace(userdata={})
    main_module.prewarm(proc)  # type: ignore[arg-type]

    assert "noise_cancellation" not in proc.userdata
