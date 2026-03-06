from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('book', 'video', 'podcast', 'article', 'post')",
            name="ck_knowledge_sources_source_type_allowed",
        ),
        UniqueConstraint(
            "title",
            "source_type",
            name="uq_knowledge_sources_title_source_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    source_type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    language: Mapped[str] = mapped_column(String(10))
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
