from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import main as main_module
import pytest
from livekit.agents import llm
from prompts import PromptBundle
from settings import AgentSettings


class FakeRoom:
    def __init__(self) -> None:
        self.name = "room-123"
        self.handlers: dict[str, object] = {}
        self.local_participant = SimpleNamespace(identity="agent-1")

    def on(self, _event_name: str):
        def decorator(handler):
            self.handlers[_event_name] = handler
            return handler

        return decorator


class FakeContext:
    def __init__(self) -> None:
        self.room = FakeRoom()
        self.proc = SimpleNamespace(
            userdata={
                "db_sessionmaker": object(),
                "vad": "vad",
                "stt": "stt",
                "llm": "llm",
                "tts": "tts",
                "noise_cancellation": None,
            }
        )
        self.connected_with = None

    async def connect(self, *, auto_subscribe) -> None:
        self.connected_with = auto_subscribe

    async def wait_for_participant(self):
        return SimpleNamespace(identity="user-1", name="User 1")


class FakeSession:
    def __init__(self) -> None:
        self.started_with: dict[str, object] | None = None
        self.handlers: dict[str, object] = {}
        self.generate_reply_calls: list[dict[str, object]] = []
        self.current_speech = None

    def on(self, _event_name: str):
        def decorator(handler):
            self.handlers[_event_name] = handler
            return handler

        return decorator

    async def start(self, **kwargs: object) -> None:
        self.started_with = kwargs

    def generate_reply(self, **kwargs: object):
        self.generate_reply_calls.append(kwargs)
        return self.current_speech


class FakeSpeechHandle:
    def __init__(
        self,
        *,
        modality: str,
        on_await: object | None = None,
    ) -> None:
        self.input_details = SimpleNamespace(modality=modality)
        self._on_await = on_await

    def __await__(self):
        async def _wait():
            if self._on_await is not None:
                result = self._on_await()
                if asyncio.iscoroutine(result):
                    await result
            return self

        return _wait().__await__()


@pytest.mark.asyncio
@pytest.mark.usefixtures("livekit_required_env")
async def test_entrypoint_starts_agent_with_db_instructions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = FakeContext()
    session = FakeSession()
    captured_agent_kwargs: dict[str, object] = {}
    saved_snapshot: dict[str, object] = {}

    monkeypatch.setattr(main_module, "_settings", AgentSettings())
    monkeypatch.setattr(main_module, "build_session", lambda *args, **kwargs: session)

    async def fake_resolve_session_id(room_name: str):
        return uuid4()

    async def fake_resolve_prompt_locale(
        sessionmaker,
        session_id,
        *,
        preferred_locale,
        default_locale,
    ):
        _ = (sessionmaker, session_id, preferred_locale, default_locale)
        return "ru"

    async def fake_load_prompt_bundle(sessionmaker, locale, *, default_locale):
        _ = (sessionmaker, locale, default_locale)
        return PromptBundle(
            requested_locale="ru",
            locale_chain=("ru", "en"),
            layers={
                "system_prompt": "System",
                "voice_prompt": "Voice",
                "mode_voice_guidance": "Voice guidance",
                "mode_text_guidance": "Text guidance",
            },
            versions={
                "system_prompt": 1,
                "voice_prompt": 1,
                "mode_voice_guidance": 1,
                "mode_text_guidance": 1,
            },
            resolved_locales={
                "system_prompt": "en",
                "voice_prompt": "en",
                "mode_voice_guidance": "en",
                "mode_text_guidance": "en",
            },
        )

    monkeypatch.setattr(main_module, "resolve_session_id", fake_resolve_session_id)
    monkeypatch.setattr(main_module, "resolve_prompt_locale", fake_resolve_prompt_locale)
    monkeypatch.setattr(main_module, "load_prompt_bundle", fake_load_prompt_bundle)
    monkeypatch.setattr(main_module, "build_instructions", lambda layers: "System\n\nVoice")

    async def fake_save_config_snapshot(sessionmaker, session_id, prompt_bundle) -> None:
        saved_snapshot["session_id"] = session_id
        saved_snapshot["layers"] = prompt_bundle.layers

    class FakeModeContext:
        def __init__(self) -> None:
            self.current_mode = "voice"
            self.current_language = None

        def set_language(self, language: str | None) -> None:
            self.current_language = language

    class FakeTwypeAgent:
        def __init__(self, **kwargs: object) -> None:
            captured_agent_kwargs.update(kwargs)
            self.mode_context = FakeModeContext()

        def set_chat_response_publisher(self, publisher) -> None:
            self.publisher = publisher

    monkeypatch.setattr(main_module, "save_config_snapshot", fake_save_config_snapshot)
    monkeypatch.setattr(main_module, "TwypeAgent", FakeTwypeAgent)

    await main_module.entrypoint(ctx)

    assert session.started_with is not None
    assert captured_agent_kwargs["instructions"] == "System\n\nVoice"
    assert captured_agent_kwargs["mode_voice_guidance"] == "Voice guidance"
    assert captured_agent_kwargs["mode_text_guidance"] == "Text guidance"
    assert saved_snapshot["layers"] == {
        "system_prompt": "System",
        "voice_prompt": "Voice",
        "mode_voice_guidance": "Voice guidance",
        "mode_text_guidance": "Text guidance",
    }


@pytest.mark.asyncio
@pytest.mark.usefixtures("livekit_required_env")
async def test_entrypoint_handles_text_chat_message_via_data_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = FakeContext()
    ctx.proc.userdata["db_sessionmaker"] = None
    session = FakeSession()
    published_chat_responses: list[dict[str, object]] = []
    saved_user_messages: list[dict[str, object]] = []
    saved_assistant_messages: list[dict[str, object]] = []
    resolved_session_id = uuid4()
    persisted_response_id = uuid4()

    async def emit_assistant_message() -> None:
        handler = session.handlers["conversation_item_added"]
        handler(
            SimpleNamespace(
                item=SimpleNamespace(
                    role="assistant",
                    content="Hello back",
                )
            )
        )
        await asyncio.sleep(0)

    session.current_speech = FakeSpeechHandle(modality="text", on_await=emit_assistant_message)

    monkeypatch.setattr(main_module, "_settings", AgentSettings())
    monkeypatch.setattr(main_module, "build_session", lambda *args, **kwargs: session)

    async def fake_resolve_session_id(room_name: str):
        _ = room_name
        return resolved_session_id

    monkeypatch.setattr(main_module, "resolve_session_id", fake_resolve_session_id)

    async def fake_save_transcript(session_id, text, sentiment_raw, *, mode="voice"):
        saved_user_messages.append(
            {
                "session_id": session_id,
                "text": text,
                "sentiment_raw": sentiment_raw,
                "mode": mode,
            }
        )
        return uuid4()

    async def fake_save_agent_response(session_id, text, *, mode="voice"):
        saved_assistant_messages.append(
            {
                "session_id": session_id,
                "text": text,
                "mode": mode,
            }
        )
        return persisted_response_id

    async def fake_publish_chat_response(room, *, text, is_final, message_id=None) -> None:
        published_chat_responses.append(
            {
                "room": room,
                "text": text,
                "is_final": is_final,
                "message_id": message_id,
            }
        )

    monkeypatch.setattr(main_module, "save_transcript", fake_save_transcript)
    monkeypatch.setattr(main_module, "save_agent_response", fake_save_agent_response)
    monkeypatch.setattr(main_module, "publish_chat_response", fake_publish_chat_response)

    await main_module.entrypoint(ctx)

    packet = SimpleNamespace(
        data=json.dumps({"type": "chat_message", "text": " Hello "}).encode("utf-8"),
        participant=SimpleNamespace(identity="user-1"),
    )
    ctx.room.handlers["data_received"](packet)
    for _ in range(10):
        if published_chat_responses:
            break
        await asyncio.sleep(0)

    assert len(session.generate_reply_calls) == 1
    generate_reply_call = session.generate_reply_calls[0]
    assert generate_reply_call["input_modality"] == "text"
    user_input = generate_reply_call["user_input"]
    assert isinstance(user_input, llm.ChatMessage)
    assert user_input.role == "user"
    assert user_input.content == ["Hello"]
    assert user_input.extra == {"mode": "text"}
    assert saved_user_messages and saved_user_messages[0]["mode"] == "text"
    assert saved_user_messages[0]["text"] == "Hello"
    assert saved_user_messages[0]["session_id"] == resolved_session_id
    assert saved_assistant_messages and saved_assistant_messages[0]["mode"] == "text"
    assert saved_assistant_messages[0]["text"] == "Hello back"
    assert saved_assistant_messages[0]["session_id"] == resolved_session_id
    assert published_chat_responses == [
        {
            "room": ctx.room,
            "text": "Hello back",
            "is_final": True,
            "message_id": str(persisted_response_id),
        }
    ]
    started_agent = session.started_with["agent"]
    assert started_agent.mode_context.current_mode == "text"


@pytest.mark.asyncio
@pytest.mark.usefixtures("livekit_required_env")
async def test_entrypoint_keeps_voice_persistence_and_transcript_publishing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = FakeContext()
    ctx.proc.userdata["db_sessionmaker"] = None
    session = FakeSession()
    saved_user_messages: list[dict[str, object]] = []
    saved_assistant_messages: list[dict[str, object]] = []
    published_transcripts: list[dict[str, object]] = []
    resolved_session_id = uuid4()

    monkeypatch.setattr(main_module, "_settings", AgentSettings())
    monkeypatch.setattr(main_module, "build_session", lambda *args, **kwargs: session)

    async def fake_resolve_session_id(room_name: str):
        _ = room_name
        return resolved_session_id

    monkeypatch.setattr(main_module, "resolve_session_id", fake_resolve_session_id)

    async def fake_save_transcript(session_id, text, sentiment_raw, *, mode="voice"):
        saved_user_messages.append(
            {
                "session_id": session_id,
                "text": text,
                "sentiment_raw": sentiment_raw,
                "mode": mode,
            }
        )
        return uuid4()

    async def fake_save_agent_response(session_id, text, *, mode="voice"):
        saved_assistant_messages.append(
            {
                "session_id": session_id,
                "text": text,
                "mode": mode,
            }
        )
        return uuid4()

    async def fake_publish_transcript(
        room,
        *,
        role="user",
        is_final,
        text,
        language,
        message_id=None,
        sentiment_raw=None,
    ) -> None:
        published_transcripts.append(
            {
                "room": room,
                "role": role,
                "is_final": is_final,
                "text": text,
                "language": language,
                "message_id": message_id,
                "sentiment_raw": sentiment_raw,
            }
        )

    monkeypatch.setattr(main_module, "save_transcript", fake_save_transcript)
    monkeypatch.setattr(main_module, "save_agent_response", fake_save_agent_response)
    monkeypatch.setattr(main_module, "publish_transcript", fake_publish_transcript)

    await main_module.entrypoint(ctx)

    session.handlers["user_input_transcribed"](
        SimpleNamespace(
            transcript=" Hello ",
            is_final=True,
            language="en",
        )
    )
    await asyncio.sleep(0)

    session.current_speech = FakeSpeechHandle(modality="audio")
    session.handlers["conversation_item_added"](
        SimpleNamespace(
            item=SimpleNamespace(
                role="assistant",
                content="Voice reply",
            )
        )
    )
    await asyncio.sleep(0)

    assert saved_user_messages and saved_user_messages[0]["mode"] == "voice"
    assert saved_user_messages[0]["session_id"] == resolved_session_id
    assert saved_assistant_messages and saved_assistant_messages[0]["mode"] == "voice"
    assert saved_assistant_messages[0]["session_id"] == resolved_session_id
    assert published_transcripts[0]["role"] == "user"
    assert published_transcripts[0]["text"] == "Hello"
    assert published_transcripts[-1]["role"] == "assistant"
    assert published_transcripts[-1]["text"] == "Voice reply"
    assert session.started_with["agent"].mode_context.current_mode == "voice"


@pytest.mark.asyncio
@pytest.mark.usefixtures("livekit_required_env")
async def test_entrypoint_switches_mode_from_text_to_voice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = FakeContext()
    ctx.proc.userdata["db_sessionmaker"] = None
    session = FakeSession()
    saved_user_messages: list[dict[str, object]] = []
    resolved_session_id = uuid4()

    monkeypatch.setattr(main_module, "_settings", AgentSettings())
    monkeypatch.setattr(main_module, "build_session", lambda *args, **kwargs: session)

    async def fake_resolve_session_id(room_name: str):
        _ = room_name
        return resolved_session_id

    monkeypatch.setattr(main_module, "resolve_session_id", fake_resolve_session_id)

    async def fake_save_transcript(session_id, text, sentiment_raw, *, mode="voice"):
        saved_user_messages.append(
            {
                "session_id": session_id,
                "text": text,
                "mode": mode,
            }
        )
        return uuid4()

    monkeypatch.setattr(main_module, "save_transcript", fake_save_transcript)

    await main_module.entrypoint(ctx)

    session.current_speech = FakeSpeechHandle(modality="text")
    ctx.room.handlers["data_received"](
        SimpleNamespace(
            data=json.dumps({"type": "chat_message", "text": "Text first"}).encode("utf-8"),
            participant=SimpleNamespace(identity="user-1"),
        )
    )
    await asyncio.sleep(0)

    started_agent = session.started_with["agent"]
    assert started_agent.mode_context.current_mode == "text"

    session.handlers["user_input_transcribed"](
        SimpleNamespace(
            transcript=" Voice second ",
            is_final=True,
            language="en",
        )
    )
    await asyncio.sleep(0)

    assert started_agent.mode_context.current_mode == "voice"
    assert [message["mode"] for message in saved_user_messages] == ["text", "voice"]
