from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.knowledge_chunk import KnowledgeChunk
from src.models.knowledge_source import KnowledgeSource
from src.sources.service import resolve_chunks

from tests.helpers import auth_headers, create_verified_user


async def _create_source_with_chunks(
    session: AsyncSession,
    *,
    source_type: str = "article",
    title: str | None = None,
    author: str | None = "Dr. Smith",
    url: str | None = "https://example.com/source",
    language: str = "en",
    tags: list[str] | None = None,
    sections: list[str | None] | None = None,
    page_ranges: list[str | None] | None = None,
) -> tuple[KnowledgeSource, list[KnowledgeChunk]]:
    source = KnowledgeSource(
        source_type=source_type,
        title=title or f"Source {uuid.uuid4()}",
        author=author,
        url=url,
        language=language,
        tags=tags or ["fixture"],
    )
    session.add(source)
    await session.flush()

    chunk_sections = sections or ["Section A"]
    chunk_page_ranges = page_ranges or [None] * len(chunk_sections)
    chunks = [
        KnowledgeChunk(
            source_id=source.id,
            content=f"Chunk {index}",
            section=section,
            page_range=chunk_page_ranges[index],
        )
        for index, section in enumerate(chunk_sections)
    ]
    session.add_all(chunks)
    await session.flush()
    return source, chunks


class TestResolveChunksService:
    async def test_returns_joined_source_metadata(self, session: AsyncSession):
        source, chunks = await _create_source_with_chunks(
            session,
            source_type="book",
            title="Medical Guide",
            author="Dr. Smith",
            url=None,
            sections=["Chapter 3", None],
            page_ranges=["45-47", None],
        )
        await session.commit()

        items = await resolve_chunks([chunks[0].id, chunks[1].id], session)

        assert [item.chunk_id for item in items] == [chunks[0].id, chunks[1].id]
        assert items[0].source_type == source.source_type
        assert items[0].title == source.title
        assert items[0].author == source.author
        assert items[0].url is None
        assert items[0].section == "Chapter 3"
        assert items[0].page_range == "45-47"
        assert items[1].section is None
        assert items[1].page_range is None

    async def test_returns_empty_when_all_ids_missing(self, session: AsyncSession):
        items = await resolve_chunks([uuid.uuid4()], session)

        assert items == []

    async def test_returns_early_for_empty_input(self):
        db = AsyncMock()

        items = await resolve_chunks([], db)

        assert items == []
        db.execute.assert_not_called()

    async def test_omits_missing_ids_and_preserves_found_order(self, session: AsyncSession):
        _, chunks = await _create_source_with_chunks(
            session,
            sections=["Intro", "Appendix"],
            page_ranges=["1-2", "99-100"],
        )
        missing_id = uuid.uuid4()
        await session.commit()

        items = await resolve_chunks([missing_id, chunks[1].id, chunks[0].id], session)

        assert [item.chunk_id for item in items] == [chunks[1].id, chunks[0].id]


class TestResolveSourcesEndpoint:
    async def test_success(self, client: AsyncClient, session: AsyncSession, unique_email: str):
        user = await create_verified_user(session, unique_email)
        _, chunks = await _create_source_with_chunks(
            session,
            source_type="article",
            title="Trusted Article",
            author="Alex Doe",
            url="https://example.com/article",
            sections=["Section 1", "Section 2"],
            page_ranges=["10-11", "12-13"],
        )
        await session.commit()

        resp = await client.post(
            "/sources/resolve",
            headers=auth_headers(user.id),
            json={"chunk_ids": [str(chunks[0].id), str(chunks[1].id)]},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert [item["chunk_id"] for item in data["items"]] == [
            str(chunks[0].id),
            str(chunks[1].id),
        ]
        assert data["items"][0]["source_type"] == "article"
        assert data["items"][0]["title"] == "Trusted Article"
        assert data["items"][0]["author"] == "Alex Doe"
        assert data["items"][0]["url"] == "https://example.com/article"
        assert data["items"][0]["section"] == "Section 1"
        assert data["items"][0]["page_range"] == "10-11"

    async def test_empty_chunk_ids_returns_empty_items(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        user = await create_verified_user(session, unique_email)
        await session.commit()

        resp = await client.post(
            "/sources/resolve",
            headers=auth_headers(user.id),
            json={"chunk_ids": []},
        )

        assert resp.status_code == 200
        assert resp.json() == {"items": []}

    async def test_accepts_exactly_50_chunk_ids(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        user = await create_verified_user(session, unique_email)
        await session.commit()

        resp = await client.post(
            "/sources/resolve",
            headers=auth_headers(user.id),
            json={"chunk_ids": [str(uuid.uuid4()) for _ in range(50)]},
        )

        assert resp.status_code == 200
        assert resp.json() == {"items": []}

    async def test_rejects_more_than_50_chunk_ids(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        user = await create_verified_user(session, unique_email)
        await session.commit()

        resp = await client.post(
            "/sources/resolve",
            headers=auth_headers(user.id),
            json={"chunk_ids": [str(uuid.uuid4()) for _ in range(51)]},
        )

        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert any(error["loc"][-1] == "chunk_ids" for error in detail)

    async def test_requires_authentication(self, client: AsyncClient):
        resp = await client.post("/sources/resolve", json={"chunk_ids": [str(uuid.uuid4())]})

        assert resp.status_code == 401

    async def test_all_missing_chunk_ids_return_empty_items(
        self, client: AsyncClient, session: AsyncSession, unique_email: str
    ):
        user = await create_verified_user(session, unique_email)
        await session.commit()

        resp = await client.post(
            "/sources/resolve",
            headers=auth_headers(user.id),
            json={"chunk_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
        )

        assert resp.status_code == 200
        assert resp.json() == {"items": []}
