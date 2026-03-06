from __future__ import annotations

from datetime import UTC, datetime

from jose import jwt
from src.sessions.livekit import create_livekit_token


def _extract_room(claims: dict[str, object]) -> str | None:
    video = claims.get("video")
    if isinstance(video, dict):
        room = video.get("room") or video.get("roomName") or video.get("room_name")
        if isinstance(room, str):
            return room
    return None


def _extract_identity(claims: dict[str, object]) -> str | None:
    identity = claims.get("sub") or claims.get("identity")
    return identity if isinstance(identity, str) else None


def test_create_livekit_token_contains_identity_and_room():
    identity = "9b4f0e4b-8c2c-4f8f-9b6a-0d10f3c0c999"
    room_name = "session-11111111-2222-3333-4444-555555555555"
    api_key = "test_api_key"
    api_secret = "test_api_secret_with_32_bytes_min"

    token = create_livekit_token(identity, room_name, api_key, api_secret)
    assert isinstance(token, str)
    assert token.count(".") == 2

    claims = jwt.decode(token, api_secret, algorithms=["HS256"], options={"verify_aud": False})

    assert _extract_identity(claims) == identity
    assert _extract_room(claims) == room_name

    exp = claims.get("exp")
    assert isinstance(exp, int)

    now_ts = int(datetime.now(UTC).timestamp())
    ttl = exp - now_ts
    assert 6 * 60 * 60 - 300 <= ttl <= 6 * 60 * 60 + 300
