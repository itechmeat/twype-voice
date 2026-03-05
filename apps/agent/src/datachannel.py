from __future__ import annotations

import json
from typing import Any


def _encode_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


async def publish_transcript(
    room: Any,
    *,
    is_final: bool,
    text: str,
    language: str,
    message_id: str | None = None,
    sentiment_raw: float | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "transcript",
        "is_final": is_final,
        "text": text,
        "language": language,
    }

    if is_final:
        if message_id is not None:
            payload["message_id"] = message_id
        if sentiment_raw is not None:
            payload["sentiment_raw"] = sentiment_raw

    await room.local_participant.publish_data(
        _encode_json(payload),
        reliable=is_final,
    )
