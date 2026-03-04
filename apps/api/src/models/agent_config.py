from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AgentConfig(Base):
    __tablename__ = "agent_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(Text)

    version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=func.now()
    )
