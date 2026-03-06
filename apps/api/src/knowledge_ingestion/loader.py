from __future__ import annotations

import uuid
from dataclasses import dataclass

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.knowledge_constants import EMBEDDING_DIMENSION
from src.models import KnowledgeChunk, KnowledgeSource

from .types import EmbeddedChunk, ManifestSource


@dataclass(slots=True, frozen=True)
class PreparedSource:
    source: ManifestSource
    chunks: list[EmbeddedChunk]


class DatabaseLoader:
    async def load(self, session: AsyncSession, prepared_sources: list[PreparedSource]) -> None:
        for prepared_source in prepared_sources:
            source_id = await self._upsert_source(session, prepared_source.source)
            await self._replace_chunks(session, source_id, prepared_source.chunks)

    async def _upsert_source(self, session: AsyncSession, source: ManifestSource) -> uuid.UUID:
        values = {
            "id": uuid.uuid4(),
            "source_type": source.source_type,
            "title": source.title,
            "author": source.author,
            "url": source.url,
            "language": source.language,
            "tags": source.tags or None,
        }

        statement = insert(KnowledgeSource).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[KnowledgeSource.title, KnowledgeSource.source_type],
            set_={
                "author": statement.excluded.author,
                "url": statement.excluded.url,
                "language": statement.excluded.language,
                "tags": statement.excluded.tags,
            },
        )
        statement = statement.returning(KnowledgeSource.id)
        source_id = await session.scalar(statement)
        if source_id is None:
            raise RuntimeError("Failed to upsert knowledge source")
        return source_id

    async def _replace_chunks(
        self,
        session: AsyncSession,
        source_id: uuid.UUID,
        chunks: list[EmbeddedChunk],
    ) -> None:
        await session.execute(
            sa.delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id)
        )

        if not chunks:
            return

        content_param = sa.bindparam("content")
        statement = sa.insert(KnowledgeChunk).values(
            id=sa.bindparam("id"),
            source_id=sa.bindparam("source_id"),
            content=content_param,
            section=sa.bindparam("section"),
            page_range=sa.bindparam("page_range"),
            embedding=sa.bindparam("embedding", type_=Vector(EMBEDDING_DIMENSION)),
            search_vector=sa.func.to_tsvector("simple", content_param),
            token_count=sa.bindparam("token_count"),
        )

        rows = [
            {
                "id": uuid.uuid4(),
                "source_id": source_id,
                "content": chunk.content,
                "section": chunk.section,
                "page_range": chunk.page_range,
                "embedding": chunk.embedding,
                "token_count": chunk.token_count,
            }
            for chunk in chunks
        ]
        await session.execute(statement, rows)
