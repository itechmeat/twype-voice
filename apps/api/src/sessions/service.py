from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.message import Message
from src.models.session import Session
from src.sessions.exceptions import SessionNotFoundError


async def create_session(user_id: uuid.UUID, db: AsyncSession) -> Session:
    room_name = f"session-{uuid.uuid4()}"
    session = Session(user_id=user_id, room_name=room_name, status="active")
    db.add(session)
    await db.flush()
    return session


async def get_user_sessions(
    user_id: uuid.UUID, offset: int, limit: int, db: AsyncSession
) -> tuple[list[Session], int]:
    total = await db.scalar(
        select(func.count()).select_from(Session).where(Session.user_id == user_id)
    )
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(result.scalars().all())
    return items, int(total or 0)


async def get_session_messages(
    session_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> list[Message]:
    session_exists = await db.scalar(
        select(Session.id).where(Session.id == session_id, Session.user_id == user_id)
    )
    if session_exists is None:
        raise SessionNotFoundError

    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())
