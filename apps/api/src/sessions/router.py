from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user, get_session
from src.localization import resolve_request_locale, translate
from src.models.user import User
from src.schemas.sessions import (
    MessageItem,
    SessionHistoryResponse,
    SessionListItem,
    SessionStartResponse,
)
from src.sessions.dependencies import get_livekit_settings
from src.sessions.exceptions import SessionNotFoundError
from src.sessions.livekit import create_livekit_token
from src.sessions.service import create_session, get_session_messages, get_user_sessions
from src.sessions.settings import LiveKitSettings

router = APIRouter()


@router.post("/start", response_model=SessionStartResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    livekit: LiveKitSettings = Depends(get_livekit_settings),
) -> SessionStartResponse:
    session = await create_session(user.id, db)
    token = create_livekit_token(
        identity=str(user.id),
        room_name=session.room_name,
        api_key=livekit.LIVEKIT_API_KEY,
        api_secret=livekit.LIVEKIT_API_SECRET,
    )
    await db.commit()
    return SessionStartResponse(
        session_id=session.id,
        room_name=session.room_name,
        livekit_token=token,
    )


@router.get("/history", response_model=SessionHistoryResponse)
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
) -> SessionHistoryResponse:
    limit = min(limit, 100)
    sessions, total = await get_user_sessions(
        user.id,
        offset=offset,
        limit=limit,
        db=db,
    )
    items = [
        SessionListItem(
            id=s.id,
            room_name=s.room_name,
            status=s.status,
            started_at=s.started_at,
            ended_at=s.ended_at,
        )
        for s in sessions
    ]
    return SessionHistoryResponse(items=items, total=total)


@router.get("/{session_id}/messages", response_model=list[MessageItem])
async def list_messages(
    session_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[MessageItem]:
    locale = resolve_request_locale(request.headers.get("Accept-Language"))

    try:
        messages = await get_session_messages(session_id=session_id, user_id=user.id, db=db)
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=translate("sessions.session_not_found", locale=locale),
        ) from exc

    return [
        MessageItem(
            id=m.id,
            role=m.role,
            mode=m.mode,
            content=m.content,
            source_ids=m.source_ids,
            created_at=m.created_at,
        )
        for m in messages
    ]
