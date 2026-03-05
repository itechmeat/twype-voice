from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from datachannel import publish_chat_response, publish_transcript, receive_chat_message


class _DummyParticipant:
    def __init__(self) -> None:
        self.calls: list[tuple[bytes, bool]] = []

    async def publish_data(self, data: bytes, *, reliable: bool) -> None:
        self.calls.append((data, reliable))


class _DummyRoom:
    def __init__(self) -> None:
        self.local_participant = _DummyParticipant()


def _packet(payload: object, *, participant_identity: str = "user-1") -> SimpleNamespace:
    data = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")

    return SimpleNamespace(
        data=data,
        participant=SimpleNamespace(identity=participant_identity),
    )


@pytest.mark.asyncio
async def test_publish_transcript_interim_lossy() -> None:
    room = _DummyRoom()

    await publish_transcript(
        room,
        is_final=False,
        text="hello",
        language="en",
    )

    assert room.local_participant.calls
    data, reliable = room.local_participant.calls[0]
    assert reliable is False

    payload = json.loads(data.decode("utf-8"))
    assert payload == {
        "type": "transcript",
        "role": "user",
        "is_final": False,
        "text": "hello",
        "language": "en",
    }


@pytest.mark.asyncio
async def test_publish_transcript_final_reliable_includes_extras() -> None:
    room = _DummyRoom()

    await publish_transcript(
        room,
        is_final=True,
        text="hello",
        language="ru",
        message_id="00000000-0000-0000-0000-000000000000",
        sentiment_raw=0.25,
    )

    assert room.local_participant.calls
    data, reliable = room.local_participant.calls[0]
    assert reliable is True

    payload = json.loads(data.decode("utf-8"))
    assert payload["type"] == "transcript"
    assert payload["role"] == "user"
    assert payload["is_final"] is True
    assert payload["text"] == "hello"
    assert payload["language"] == "ru"
    assert payload["message_id"] == "00000000-0000-0000-0000-000000000000"
    assert payload["sentiment_raw"] == 0.25


def test_receive_chat_message_returns_clean_text_for_valid_payload() -> None:
    packet = _packet({"type": "chat_message", "text": " Hello "})

    assert receive_chat_message(packet, local_participant_identity="agent-1") == "Hello"


def test_receive_chat_message_ignores_empty_text() -> None:
    packet = _packet({"type": "chat_message", "text": "   "})

    assert receive_chat_message(packet, local_participant_identity="agent-1") is None


def test_receive_chat_message_ignores_malformed_payload() -> None:
    packet = _packet(b"{bad json")

    assert receive_chat_message(packet, local_participant_identity="agent-1") is None


def test_receive_chat_message_ignores_unknown_type() -> None:
    packet = _packet({"type": "transcript", "text": "Hello"})

    assert receive_chat_message(packet, local_participant_identity="agent-1") is None


def test_receive_chat_message_ignores_self_originated_packets() -> None:
    packet = _packet({"type": "chat_message", "text": "Hello"}, participant_identity="agent-1")

    assert receive_chat_message(packet, local_participant_identity="agent-1") is None


@pytest.mark.asyncio
async def test_publish_chat_response_interim_is_lossy() -> None:
    room = _DummyRoom()

    await publish_chat_response(
        room,
        text="hel",
        is_final=False,
    )

    assert room.local_participant.calls
    data, reliable = room.local_participant.calls[0]
    assert reliable is False

    payload = json.loads(data.decode("utf-8"))
    assert payload == {
        "type": "chat_response",
        "text": "hel",
        "is_final": False,
    }


@pytest.mark.asyncio
async def test_publish_chat_response_final_includes_message_id() -> None:
    room = _DummyRoom()

    await publish_chat_response(
        room,
        text="hello",
        is_final=True,
        message_id="00000000-0000-0000-0000-000000000000",
    )

    assert room.local_participant.calls
    data, reliable = room.local_participant.calls[0]
    assert reliable is True

    payload = json.loads(data.decode("utf-8"))
    assert payload == {
        "type": "chat_response",
        "text": "hello",
        "is_final": True,
        "message_id": "00000000-0000-0000-0000-000000000000",
    }
