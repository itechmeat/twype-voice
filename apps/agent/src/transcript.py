from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

if TYPE_CHECKING:
    from src.models.message import Message
    from src.models.session import Session

logger = logging.getLogger("twype-agent")

_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _load_models() -> tuple[type[Message], type[Session]]:
    try:
        from src.models.message import Message as MessageModel
        from src.models.session import Session as SessionModel

        return MessageModel, SessionModel
    except Exception as exc:
        raise RuntimeError("twype-api models are not available") from exc


def configure_transcript_store(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    global _sessionmaker
    _sessionmaker = sessionmaker


async def resolve_session_id(room_name: str) -> uuid.UUID | None:
    if _sessionmaker is None:
        raise RuntimeError("transcript store is not configured")

    _message_model, session_model = _load_models()

    async with _sessionmaker() as session:
        return await session.scalar(
            select(session_model.id).where(session_model.room_name == room_name)
        )


async def save_transcript(
    session_id: uuid.UUID,
    text: str,
    sentiment_raw: float | None,
    *,
    mode: Literal["voice", "text"] = "voice",
) -> uuid.UUID | None:
    cleaned_text = text.strip()
    if not cleaned_text:
        return None

    if _sessionmaker is None:
        raise RuntimeError("transcript store is not configured")

    message_model, _session_model = _load_models()

    try:
        async with _sessionmaker() as session:
            message = message_model(
                session_id=session_id,
                role="user",
                mode=mode,
                content=cleaned_text,
                voice_transcript=cleaned_text if mode == "voice" else None,
                sentiment_raw=sentiment_raw if mode == "voice" else None,
            )
            session.add(message)
            await session.commit()
            await session.refresh(message)
            return message.id
    except Exception:
        logger.exception("failed to persist transcript, session_id=%s", session_id)
        return None


async def save_agent_response(
    session_id: uuid.UUID,
    text: str,
    *,
    mode: Literal["voice", "text"] = "voice",
) -> uuid.UUID | None:
    cleaned_text = text.strip()
    if not cleaned_text:
        return None

    if _sessionmaker is None:
        raise RuntimeError("transcript store is not configured")

    message_model, _session_model = _load_models()

    try:
        async with _sessionmaker() as session:
            message = message_model(
                session_id=session_id,
                role="assistant",
                mode=mode,
                content=cleaned_text,
                voice_transcript=cleaned_text if mode == "voice" else None,
                sentiment_raw=None,
            )
            session.add(message)
            await session.commit()
            await session.refresh(message)
            return message.id
    except Exception:
        logger.exception("failed to persist agent response, session_id=%s", session_id)
        return None
