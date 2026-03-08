from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient

from .livekit_room import LiveKitRoomClient


@dataclass(slots=True, frozen=True)
class AuthContext:
    email: str
    password: str
    access_token: str
    refresh_token: str


@dataclass(slots=True)
class StartedSession:
    session_id: str
    room_name: str
    livekit_token: str
    room: LiveKitRoomClient


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def extract_chunk_ids(message_payload: dict[str, Any]) -> list[str]:
    items = message_payload.get("items")
    if not isinstance(items, list):
        return []

    chunk_ids: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_chunk_ids = item.get("chunk_ids")
        if not isinstance(raw_chunk_ids, list):
            continue
        for chunk_id in raw_chunk_ids:
            if isinstance(chunk_id, str):
                chunk_ids.append(chunk_id)
    return chunk_ids


def contains_cyrillic(text: str) -> bool:
    return re.search(r"[\u0400-\u04FF]", text) is not None


def contains_latin(text: str) -> bool:
    return re.search(r"[A-Za-z]", text) is not None


@asynccontextmanager
async def started_livekit_session(
    *,
    client: AsyncClient,
    access_token: str,
    livekit_url: str,
) -> AsyncIterator[StartedSession]:
    response = await client.post("/sessions/start", headers=auth_headers(access_token))
    response.raise_for_status()
    payload = response.json()

    room = await LiveKitRoomClient.connect(
        url=livekit_url,
        token=payload["livekit_token"],
    )

    try:
        yield StartedSession(
            session_id=str(payload["session_id"]),
            room_name=str(payload["room_name"]),
            livekit_token=str(payload["livekit_token"]),
            room=room,
        )
    finally:
        await room.disconnect()
