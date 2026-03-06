from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.knowledge_constants import EMBEDDING_DIMENSION
from src.knowledge_ingestion.loader import DatabaseLoader, PreparedSource
from src.knowledge_ingestion.types import EmbeddedChunk
from src.models import KnowledgeChunk, KnowledgeSource

from .knowledge_test_utils import make_manifest_source


def _embedded_chunk(content: str, *, section: str = "Section") -> EmbeddedChunk:
    return EmbeddedChunk(
        content=content,
        section=section,
        page_range="1-2",
        language="en",
        token_count=12,
        embedding=[0.001] * EMBEDDING_DIMENSION,
    )


@pytest.mark.asyncio
async def test_loader_inserts_and_reingests_sources(session) -> None:
    loader = DatabaseLoader()
    original = make_manifest_source(title="Stress Guide", source_type="article", tags=["stress"])
    updated = make_manifest_source(
        title="Stress Guide",
        source_type="article",
        author="Updated Author",
        tags=["stress", "breathing"],
    )

    await loader.load(
        session,
        [
            PreparedSource(
                source=original,
                chunks=[_embedded_chunk("First"), _embedded_chunk("Second")],
            )
        ],
    )
    await session.commit()

    await loader.load(
        session,
        [PreparedSource(source=updated, chunks=[_embedded_chunk("Replacement")])],
    )
    await session.commit()

    sources = list(
        (
            await session.execute(
                sa.select(KnowledgeSource).where(KnowledgeSource.title == "Stress Guide")
            )
        ).scalars()
    )
    chunks = list((await session.execute(sa.select(KnowledgeChunk))).scalars())
    search_vectors = (
        (await session.execute(sa.text("SELECT search_vector::text FROM knowledge_chunks")))
        .scalars()
        .all()
    )

    assert len(sources) == 1
    assert sources[0].author == "Updated Author"
    assert sources[0].tags == ["stress", "breathing"]
    assert len(chunks) == 1
    assert chunks[0].content == "Replacement"
    assert len(search_vectors) == 1
    assert search_vectors[0]


@pytest.mark.asyncio
async def test_loader_rolls_back_transaction_on_insert_error(db_engine) -> None:
    loader = DatabaseLoader()
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    original_execute = None

    async with factory() as session:
        original_execute = session.execute
        call_count = 0

        async def broken_execute(statement, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if "INSERT INTO knowledge_chunks" in str(statement):
                raise RuntimeError("boom")
            return await original_execute(statement, *args, **kwargs)

        session.execute = broken_execute  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="boom"):
            await loader.load(
                session,
                [PreparedSource(source=make_manifest_source(), chunks=[_embedded_chunk("Chunk")])],
            )

        await session.rollback()

    async with factory() as verification_session:
        source_count = await verification_session.scalar(
            sa.select(sa.func.count()).select_from(KnowledgeSource)
        )
        chunk_count = await verification_session.scalar(
            sa.select(sa.func.count()).select_from(KnowledgeChunk)
        )

    assert call_count >= 2
    assert source_count == 0
    assert chunk_count == 0
