from __future__ import annotations

import agent as agent_module
import pytest
from settings import AgentSettings


def test_build_session_passes_pipeline_settings(
    monkeypatch: pytest.MonkeyPatch,
    livekit_required_env: None,
) -> None:
    captured: dict[str, object] = {}

    class FakeAgentSession:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(agent_module, "AgentSession", FakeAgentSession)

    settings = AgentSettings()
    session = agent_module.build_session(
        settings,
        vad="vad_obj",
        stt="stt_obj",
        llm="llm_obj",
        tts="tts_obj",
    )

    assert isinstance(session, FakeAgentSession)

    assert captured["vad"] == "vad_obj"
    assert captured["stt"] == "stt_obj"
    assert captured["llm"] == "llm_obj"
    assert captured["tts"] == "tts_obj"

    assert captured["turn_detection"] == "stt"
    assert captured["min_endpointing_delay"] == 0.5
    assert captured["max_endpointing_delay"] == 3.0
    assert captured["preemptive_generation"] is True

    assert captured["false_interruption_timeout"] == 2.0
    assert captured["resume_false_interruption"] is True
    assert captured["min_interruption_duration"] == 0.5


def test_build_session_disables_false_interruption_timeout_when_zero(
    monkeypatch: pytest.MonkeyPatch,
    livekit_required_env: None,
) -> None:
    captured: dict[str, object] = {}

    class FakeAgentSession:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(agent_module, "AgentSession", FakeAgentSession)
    monkeypatch.setenv("FALSE_INTERRUPTION_TIMEOUT", "0")

    settings = AgentSettings()
    session = agent_module.build_session(settings)

    assert isinstance(session, FakeAgentSession)
    assert captured["false_interruption_timeout"] is None
