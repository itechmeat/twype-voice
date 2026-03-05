from __future__ import annotations

from datetime import datetime

import agent as agent_module
import pytest
from settings import AgentSettings


@pytest.mark.usefixtures("livekit_required_env")
def test_build_session_passes_pipeline_settings(
    monkeypatch: pytest.MonkeyPatch,
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


@pytest.mark.usefixtures("livekit_required_env")
def test_build_session_disables_false_interruption_timeout_when_zero(
    monkeypatch: pytest.MonkeyPatch,
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


def test_mode_context_initial_state() -> None:
    context = agent_module.ModeContext()

    assert context.current_mode == "voice"
    assert context.previous_mode == "voice"
    assert isinstance(context.switched_at, datetime)


def test_mode_context_switches_to_text() -> None:
    context = agent_module.ModeContext()
    initial_timestamp = context.switched_at

    context.switch_to("text")

    assert context.current_mode == "text"
    assert context.previous_mode == "voice"
    assert context.switched_at >= initial_timestamp


def test_mode_context_switches_back_to_voice() -> None:
    context = agent_module.ModeContext(current_mode="text", previous_mode="voice")

    context.switch_to("voice")

    assert context.current_mode == "voice"
    assert context.previous_mode == "text"


def test_mode_context_same_mode_is_noop() -> None:
    context = agent_module.ModeContext()
    initial_timestamp = context.switched_at

    context.switch_to("voice")

    assert context.current_mode == "voice"
    assert context.previous_mode == "voice"
    assert context.switched_at == initial_timestamp


async def _text_chunks() -> object:
    for chunk in ("Hel", "lo"):
        yield chunk


@pytest.mark.asyncio
async def test_tts_node_skips_tts_and_publishes_chunks_in_text_mode() -> None:
    published_chunks: list[str] = []
    agent = agent_module.TwypeAgent()
    agent.mode_context.switch_to("text")

    async def fake_publish(chunk: str) -> None:
        published_chunks.append(chunk)

    agent.set_chat_response_publisher(fake_publish)

    result = await agent.tts_node(_text_chunks(), None)

    assert result is None
    assert published_chunks == ["Hel", "lo"]


@pytest.mark.asyncio
async def test_tts_node_uses_base_tts_when_text_mode_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_audio_stream():
        yield "frame-1"

    def fake_tts_node(self, text, model_settings):
        captured["self"] = self
        captured["text"] = text
        captured["model_settings"] = model_settings
        return fake_audio_stream()

    monkeypatch.setattr(agent_module.Agent, "tts_node", fake_tts_node)

    agent = agent_module.TwypeAgent()
    stream = await agent.tts_node(_text_chunks(), "settings")
    frames = [frame async for frame in stream]

    assert frames == ["frame-1"]
    assert captured["self"] is agent
    assert captured["model_settings"] == "settings"
