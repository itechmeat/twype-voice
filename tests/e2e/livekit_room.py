from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from livekit import rtc


@dataclass(slots=True, frozen=True)
class LiveKitMessage:
    payload: dict[str, Any]
    participant_identity: str | None
    topic: str | None
    received_at: float


class LiveKitRoomClient:
    def __init__(self, room: rtc.Room) -> None:
        self.room = room
        self._messages: asyncio.Queue[LiveKitMessage] = asyncio.Queue()
        self._participants: asyncio.Queue[rtc.RemoteParticipant] = asyncio.Queue()

    @classmethod
    async def connect(cls, *, url: str, token: str) -> LiveKitRoomClient:
        room = rtc.Room()
        client = cls(room)

        @room.on("participant_connected")
        def _on_participant_connected(participant: rtc.RemoteParticipant) -> None:
            client._participants.put_nowait(participant)

        @room.on("data_received")
        def _on_data_received(data_packet: rtc.DataPacket) -> None:
            try:
                payload = json.loads(data_packet.data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return

            if not isinstance(payload, dict):
                return

            client._messages.put_nowait(
                LiveKitMessage(
                    payload=payload,
                    participant_identity=getattr(data_packet.participant, "identity", None),
                    topic=data_packet.topic,
                    received_at=time.monotonic(),
                )
            )

        await room.connect(url, token, rtc.RoomOptions(auto_subscribe=True))
        return client

    async def disconnect(self) -> None:
        await self.room.disconnect()

    async def wait_for_remote_participant(
        self,
        *,
        predicate: Callable[[rtc.RemoteParticipant], bool] | None = None,
        wait_seconds: float = 15.0,
    ) -> rtc.RemoteParticipant:
        match = predicate or (lambda _participant: True)

        for participant in self.room.remote_participants.values():
            if match(participant):
                return participant

        started_at = time.monotonic()
        while True:
            remaining = wait_seconds - (time.monotonic() - started_at)
            if remaining <= 0:
                raise TimeoutError("timed out waiting for remote participant")
            participant = await asyncio.wait_for(self._participants.get(), timeout=remaining)
            if match(participant):
                return participant

    async def send_chat_message(self, text: str) -> None:
        payload = json.dumps(
            {
                "type": "chat_message",
                "text": text,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        await self.room.local_participant.publish_data(payload, reliable=True)

    async def wait_for_message(
        self,
        *,
        wait_seconds: float = 30.0,
        allowed_types: set[str] | None = None,
        predicate: Callable[[LiveKitMessage], bool] | None = None,
    ) -> LiveKitMessage:
        started_at = time.monotonic()

        while True:
            remaining = wait_seconds - (time.monotonic() - started_at)
            if remaining <= 0:
                raise TimeoutError("timed out waiting for LiveKit data channel message")

            message = await asyncio.wait_for(self._messages.get(), timeout=remaining)

            payload_type = message.payload.get("type")
            if allowed_types is not None and payload_type not in allowed_types:
                continue

            if predicate is not None and not predicate(message):
                continue

            return message
