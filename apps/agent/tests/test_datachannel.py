from __future__ import annotations

import json

import pytest
from datachannel import publish_transcript


class _DummyParticipant:
    def __init__(self) -> None:
        self.calls: list[tuple[bytes, bool]] = []

    async def publish_data(self, data: bytes, *, reliable: bool) -> None:
        self.calls.append((data, reliable))


class _DummyRoom:
    def __init__(self) -> None:
        self.local_participant = _DummyParticipant()


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
        text="привет",
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
    assert payload["text"] == "привет"
    assert payload["language"] == "ru"
    assert payload["message_id"] == "00000000-0000-0000-0000-000000000000"
    assert payload["sentiment_raw"] == 0.25
