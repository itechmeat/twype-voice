from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), index=True
    )

    role: Mapped[str] = mapped_column(String(20))
    mode: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    voice_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    sentiment_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    valence: Mapped[float | None] = mapped_column(Float, nullable=True)
    arousal: Mapped[float | None] = mapped_column(Float, nullable=True)

    source_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    session = relationship("Session")
