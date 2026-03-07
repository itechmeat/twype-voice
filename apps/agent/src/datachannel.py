from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("twype-agent")


def _encode_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def receive_chat_message(
    data_packet: Any,
    *,
    local_participant_identity: str | None = None,
) -> str | None:
    participant = getattr(data_packet, "participant", None)
    participant_identity = getattr(participant, "identity", None)
    if (
        local_participant_identity is not None
        and isinstance(participant_identity, str)
        and participant_identity == local_participant_identity
    ):
        return None

    raw_data = getattr(data_packet, "data", None)
    if not isinstance(raw_data, (bytes, bytearray)):
        logger.warning("ignored malformed data packet without bytes payload")
        return None

    try:
        payload = json.loads(bytes(raw_data).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("ignored malformed chat_message payload")
        return None

    if not isinstance(payload, dict):
        logger.warning("ignored non-object chat_message payload")
        return None

    payload_type = payload.get("type")
    if payload_type != "chat_message":
        if payload_type not in {"transcript", "chat_response", "structured_response"}:
            logger.debug("ignored unsupported data channel message type=%r", payload_type)
        return None

    text = payload.get("text")
    if not isinstance(text, str):
        logger.warning("ignored chat_message without text field")
        return None

    cleaned_text = text.strip()
    if not cleaned_text:
        return None

    return cleaned_text


async def publish_transcript(
    room: Any,
    *,
    role: str = "user",
    is_final: bool,
    text: str,
    language: str,
    message_id: str | None = None,
    sentiment_raw: float | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "transcript",
        "role": role,
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


async def publish_chat_response(
    room: Any,
    *,
    text: str,
    is_final: bool,
    message_id: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "chat_response",
        "text": text,
        "is_final": is_final,
    }

    if is_final and message_id is not None:
        payload["message_id"] = message_id

    await room.local_participant.publish_data(
        _encode_json(payload),
        reliable=is_final,
    )


async def publish_emotional_state(
    room: Any,
    *,
    quadrant: str,
    valence: float,
    arousal: float,
    trend_valence: str,
    trend_arousal: str,
    is_refined: bool = False,
    message_id: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "emotional_state",
        "quadrant": quadrant,
        "valence": valence,
        "arousal": arousal,
        "trend_valence": trend_valence,
        "trend_arousal": trend_arousal,
        "is_refined": is_refined,
    }

    if message_id is not None:
        payload["message_id"] = message_id

    await room.local_participant.publish_data(
        _encode_json(payload),
        reliable=True,
    )


async def publish_proactive_nudge(
    room: Any,
    *,
    proactive_type: str,
    message_id: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "proactive_nudge",
        "proactive_type": proactive_type,
    }

    if message_id is not None:
        payload["message_id"] = message_id

    await room.local_participant.publish_data(
        _encode_json(payload),
        reliable=True,
    )


async def publish_structured_response(
    room: Any,
    *,
    items: list[dict[str, Any]],
    is_final: bool,
    message_id: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "structured_response",
        "items": items,
        "is_final": is_final,
    }

    if is_final and message_id is not None:
        payload["message_id"] = message_id

    await room.local_participant.publish_data(
        _encode_json(payload),
        reliable=is_final,
    )
