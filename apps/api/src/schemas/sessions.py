from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class SessionStartResponse(BaseModel):
    session_id: uuid.UUID
    room_name: str
    livekit_token: str


class SessionListItem(BaseModel):
    id: uuid.UUID
    room_name: str
    status: str
    started_at: datetime
    ended_at: datetime | None


class SessionHistoryResponse(BaseModel):
    items: list[SessionListItem]
    total: int


class MessageItem(BaseModel):
    id: uuid.UUID
    role: str
    mode: str
    content: str
    source_ids: list[str] | None = None
    created_at: datetime
