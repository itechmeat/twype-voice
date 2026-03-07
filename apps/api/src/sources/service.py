from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.knowledge_chunk import KnowledgeChunk
from src.models.knowledge_source import KnowledgeSource
from src.schemas.sources import SourceItem


async def resolve_chunks(chunk_ids: list[uuid.UUID], db: AsyncSession) -> list[SourceItem]:
    if not chunk_ids:
        return []

    result = await db.execute(
        select(
            KnowledgeChunk.id,
            KnowledgeSource.source_type,
            KnowledgeSource.title,
            KnowledgeSource.author,
            KnowledgeSource.url,
            KnowledgeChunk.section,
            KnowledgeChunk.page_range,
        )
        .join(KnowledgeSource, KnowledgeChunk.source_id == KnowledgeSource.id)
        .where(KnowledgeChunk.id.in_(chunk_ids))
    )
    rows = result.all()
    items_by_id = {
        row.id: SourceItem(
            chunk_id=row.id,
            source_type=row.source_type,
            title=row.title,
            author=row.author,
            url=row.url,
            section=row.section,
            page_range=row.page_range,
        )
        for row in rows
    }
    return [items_by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in items_by_id]
