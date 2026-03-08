from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TTSConfig(Base):
    __tablename__ = "tts_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    voice_id: Mapped[str] = mapped_column(String(255), unique=True)
    model_id: Mapped[str] = mapped_column(String(100))

    expressiveness: Mapped[float] = mapped_column(Float, default=0.5, server_default=text("0.5"))
    speed: Mapped[float] = mapped_column(Float, default=1.0, server_default=text("1.0"))
    language: Mapped[str] = mapped_column(String(10))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
