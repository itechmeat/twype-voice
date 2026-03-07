from __future__ import annotations

import uuid
from datetime import datetime

import agent as agent_module
import pytest
from settings import AgentSettings

AGENT_KWARGS = {
    "instructions": "System",
    "mode_voice_guidance": "Voice guidance",
    "mode_text_guidance": "Text guidance",
}


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
async def test_tts_node_text_mode_falls_back_to_chat_response_without_text_part() -> None:
    published_messages: list[str] = []
    agent = agent_module.TwypeAgent(**AGENT_KWARGS)
    agent.mode_context.switch_to("text")

    async def fake_publish(message: str) -> None:
        published_messages.append(message)

    agent.set_chat_response_publisher(fake_publish)

    result = await agent.tts_node(_text_chunks(), None)

    assert result is None
    assert published_messages == ["Hello"]
    assert agent.last_dual_layer_result is not None
    assert agent.last_dual_layer_result.voice_text == "Hello"


@pytest.mark.asyncio
async def test_tts_node_text_mode_publishes_structured_response_when_present() -> None:
    published_results: list[object] = []
    agent = agent_module.TwypeAgent(**AGENT_KWARGS)
    agent.mode_context.switch_to("text")
    agent._last_rag_chunks = [
        agent_module.RagChunk(
            chunk_id=uuid.uuid4(),
            content="Fact",
            source_type="article",
            title="Source",
            author=None,
            section=None,
            page_range=None,
            score=0.5,
        )
    ]

    async def fake_publish(result) -> None:
        published_results.append(result)

    async def _dual_layer():
        yield "---VOICE---\nShort answer.\n---TEXT---\n- Detail [1]"

    agent.set_structured_response_publisher(fake_publish)

    result = await agent.tts_node(_dual_layer(), None)

    assert result is None
    assert len(published_results) == 1
    published_result = published_results[0]
    assert published_result.text_items[0].text == "Detail"
    assert len(published_result.text_items[0].chunk_ids) == 1


@pytest.mark.asyncio
async def test_tts_node_uses_base_tts_when_text_mode_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_audio_stream():
        yield "frame-1"

    def fake_tts_node(self, text, model_settings):
        captured["self"] = self
        captured["model_settings"] = model_settings

        async def _collect():
            captured["tokens"] = [chunk async for chunk in text]
            async for frame in fake_audio_stream():
                yield frame

        return _collect()

    monkeypatch.setattr(agent_module.Agent, "tts_node", fake_tts_node)

    agent = agent_module.TwypeAgent(**AGENT_KWARGS)
    stream = await agent.tts_node(_text_chunks(), "settings")
    frames = [frame async for frame in stream]

    assert frames == ["frame-1"]
    assert captured["self"] is agent
    assert captured["model_settings"] == "settings"
    assert captured["tokens"] == ["Hel", "lo"]


@pytest.mark.asyncio
async def test_tts_node_voice_mode_routes_only_voice_part_to_base_tts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    published_results: list[object] = []
    source_chunk_id = uuid.uuid4()

    async def fake_audio_stream():
        yield "frame-1"

    def fake_tts_node(self, text, model_settings):
        captured["model_settings"] = model_settings

        async def _collect():
            captured["tokens"] = [chunk async for chunk in text]
            async for frame in fake_audio_stream():
                yield frame

        return _collect()

    monkeypatch.setattr(agent_module.Agent, "tts_node", fake_tts_node)

    agent = agent_module.TwypeAgent(**AGENT_KWARGS)
    agent._last_rag_chunks = [
        agent_module.RagChunk(
            chunk_id=source_chunk_id,
            content="Fact",
            source_type="article",
            title="Source",
            author=None,
            section=None,
            page_range=None,
            score=0.5,
        )
    ]

    async def fake_publish(result) -> None:
        published_results.append(result)

    async def _dual_layer():
        yield "---VOICE---\nShort "
        yield "answer.\n---TEXT---\n- Detail [1]"

    agent.set_structured_response_publisher(fake_publish)

    stream = await agent.tts_node(_dual_layer(), "settings")
    frames = [frame async for frame in stream]

    assert frames == ["frame-1"]
    assert captured["tokens"] == ["Short ", "answer."]
    assert captured["model_settings"] == "settings"
    assert agent.last_dual_layer_result is not None
    assert len(published_results) == 1
    assert published_results[0].all_chunk_ids == [source_chunk_id]


@pytest.mark.asyncio
async def test_tts_node_voice_mode_skips_tts_when_voice_part_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    published_results: list[object] = []
    tts_called = False
    source_chunk_id = uuid.uuid4()

    def fake_tts_node(self, text, model_settings):
        nonlocal tts_called
        _ = (self, text, model_settings)
        tts_called = True
        return None

    monkeypatch.setattr(agent_module.Agent, "tts_node", fake_tts_node)

    agent = agent_module.TwypeAgent(**AGENT_KWARGS)
    agent._last_rag_chunks = [
        agent_module.RagChunk(
            chunk_id=source_chunk_id,
            content="Fact",
            source_type="article",
            title="Source",
            author=None,
            section=None,
            page_range=None,
            score=0.5,
        )
    ]

    async def fake_publish(result) -> None:
        published_results.append(result)

    async def _text_only_response():
        yield "---TEXT---\n- Detail [1]"

    agent.set_structured_response_publisher(fake_publish)

    result = await agent.tts_node(_text_only_response(), "settings")

    assert result is None
    assert tts_called is False
    assert agent.last_dual_layer_result is not None
    assert len(published_results) == 1
    assert published_results[0].all_chunk_ids == [source_chunk_id]
