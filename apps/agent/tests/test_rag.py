from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import agent as agent_module
import pytest
from livekit.agents import llm
from rag import RagChunk, RagEngine, format_rag_context
from settings import AgentSettings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from testsupport import (
    default_test_database_url,
    ensure_database_exists,
    ensure_pgvector_extension,
)

AGENT_KWARGS = {
    "instructions": "System",
    "mode_voice_guidance": "Voice guidance",
    "mode_text_guidance": "Text guidance",
}


def _test_database_url() -> str:
    return default_test_database_url(os.environ)


class FakeEmbeddingClient:
    def __init__(
        self,
        embeddings: list[list[float]] | None = None,
        *,
        error: Exception | None = None,
    ) -> None:
        self.embeddings = embeddings or []
        self.error = error
        self.calls: list[list[object]] = []

    async def embed_inputs(self, inputs: list[object]) -> list[list[float]]:
        self.calls.append(inputs)
        if self.error is not None:
            raise self.error
        return self.embeddings


def _embedding(*values: float) -> list[float]:
    base = [0.0] * 1536
    for index, value in enumerate(values):
        base[index] = value
    return base


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"


@pytest.fixture
async def rag_db_engine() -> AsyncIterator[AsyncEngine]:
    database_url = _test_database_url()
    await ensure_database_exists(database_url)
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await ensure_pgvector_extension(conn)
        await conn.execute(text("DROP TABLE IF EXISTS knowledge_chunks"))
        await conn.execute(text("DROP TABLE IF EXISTS knowledge_sources"))
        await conn.execute(
            text(
                """
                CREATE TABLE knowledge_sources (
                    id uuid PRIMARY KEY,
                    source_type varchar(20) NOT NULL,
                    title varchar(500) NOT NULL,
                    author varchar(255),
                    language varchar(10) NOT NULL
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE knowledge_chunks (
                    id uuid PRIMARY KEY,
                    source_id uuid NOT NULL REFERENCES knowledge_sources(id),
                    content text NOT NULL,
                    section varchar(500),
                    page_range varchar(50),
                    embedding vector(1536),
                    search_vector tsvector
                )
                """
            )
        )
    yield engine
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS knowledge_chunks"))
        await conn.execute(text("DROP TABLE IF EXISTS knowledge_sources"))
    await engine.dispose()


@pytest.fixture
async def rag_sessionmaker(
    rag_db_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(rag_db_engine, expire_on_commit=False)


async def _seed_chunk(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    source_id: uuid.UUID,
    chunk_id: uuid.UUID,
    source_type: str,
    title: str,
    language: str,
    content: str,
    embedding: list[float],
    author: str | None = None,
    section: str | None = None,
    page_range: str | None = None,
) -> None:
    async with sessionmaker() as session:
        await session.execute(
            text(
                """
                INSERT INTO knowledge_sources (id, source_type, title, author, language)
                VALUES (:id, :source_type, :title, :author, :language)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "id": source_id,
                "source_type": source_type,
                "title": title,
                "author": author,
                "language": language,
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO knowledge_chunks (
                    id,
                    source_id,
                    content,
                    section,
                    page_range,
                    embedding,
                    search_vector
                )
                VALUES (
                    :id,
                    :source_id,
                    :content,
                    :section,
                    :page_range,
                    CAST(:embedding AS vector(1536)),
                    to_tsvector('simple', :content)
                )
                """
            ),
            {
                "id": chunk_id,
                "source_id": source_id,
                "content": content,
                "section": section,
                "page_range": page_range,
                "embedding": _vector_literal(embedding),
            },
        )
        await session.commit()


@pytest.mark.asyncio
@pytest.mark.usefixtures("livekit_required_env")
async def test_embed_query_returns_embedding(
    rag_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    client = FakeEmbeddingClient(embeddings=[_embedding(0.7, 0.3)])
    engine = RagEngine(AgentSettings(), rag_sessionmaker, embedding_client=client)

    embedding = await engine.embed_query("burnout symptoms")

    assert embedding == _embedding(0.7, 0.3)
    assert len(client.calls) == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("livekit_required_env")
async def test_embed_query_returns_none_on_error(
    rag_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    engine = RagEngine(
        AgentSettings(),
        rag_sessionmaker,
        embedding_client=FakeEmbeddingClient(error=RuntimeError("boom")),
    )

    assert await engine.embed_query("burnout symptoms") is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("livekit_required_env")
async def test_embed_query_returns_none_for_empty_text(
    rag_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    client = FakeEmbeddingClient(embeddings=[_embedding(0.1)])
    engine = RagEngine(AgentSettings(), rag_sessionmaker, embedding_client=client)

    assert await engine.embed_query("   ") is None
    assert client.calls == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("livekit_required_env")
async def test_hybrid_search_applies_rrf_language_boost_and_limit(
    rag_sessionmaker: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAG_TOP_K", "2")
    monkeypatch.setenv("RAG_LANGUAGE_BOOST", "2.0")

    source_a = uuid.uuid4()
    source_b = uuid.uuid4()
    source_c = uuid.uuid4()

    chunk_a = uuid.uuid4()
    chunk_b = uuid.uuid4()
    chunk_c = uuid.uuid4()

    await _seed_chunk(
        rag_sessionmaker,
        source_id=source_a,
        chunk_id=chunk_a,
        source_type="book",
        title="Russian Burnout Guide",
        author="Dr. Ivanov",
        language="ru",
        content="burnout signs recovery",
        section="Chapter 1",
        page_range="10-12",
        embedding=_embedding(0.85, 0.52),
    )
    await _seed_chunk(
        rag_sessionmaker,
        source_id=source_b,
        chunk_id=chunk_b,
        source_type="article",
        title="English Burnout Symptoms",
        language="en",
        content="burnout symptoms symptoms symptoms",
        embedding=_embedding(0.72, 0.68),
    )
    await _seed_chunk(
        rag_sessionmaker,
        source_id=source_c,
        chunk_id=chunk_c,
        source_type="post",
        title="Stress Recovery Notes",
        language="en",
        content="stress regulation recovery",
        embedding=_embedding(0.1, 0.9),
    )

    engine = RagEngine(
        AgentSettings(),
        rag_sessionmaker,
        embedding_client=FakeEmbeddingClient(embeddings=[_embedding(1.0, 0.0)]),
    )

    boosted = await engine.search("burnout symptoms", language="ru-RU")
    unboosted = await engine.search("burnout symptoms", language=None)

    assert [chunk.title for chunk in boosted] == [
        "Russian Burnout Guide",
        "English Burnout Symptoms",
    ]
    assert len(boosted) == 2
    assert boosted[0].score > unboosted[0].score


@pytest.mark.asyncio
@pytest.mark.usefixtures("livekit_required_env")
async def test_hybrid_search_returns_empty_when_no_rows(
    rag_sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    engine = RagEngine(
        AgentSettings(),
        rag_sessionmaker,
        embedding_client=FakeEmbeddingClient(embeddings=[_embedding(1.0)]),
    )

    assert await engine.search("burnout symptoms", language="en") == []


def test_format_rag_context_renders_full_metadata() -> None:
    formatted = format_rag_context(
        [
            RagChunk(
                chunk_id=uuid.uuid4(),
                content="Symptoms include exhaustion.",
                source_type="book",
                title="Burnout Prevention",
                author="Dr. Smith",
                section="Chapter 3",
                page_range="45-47",
                score=0.5,
            )
        ]
    )

    assert "[Knowledge Base Context]" in formatted
    assert "[1] Source: Burnout Prevention by Dr. Smith (book)" in formatted
    assert "Section: Chapter 3 | Pages: 45-47" in formatted
    assert "Symptoms include exhaustion." in formatted


def test_format_rag_context_handles_partial_metadata() -> None:
    formatted = format_rag_context(
        [
            RagChunk(
                chunk_id=uuid.uuid4(),
                content="Focus on sleep hygiene.",
                source_type="article",
                title="Recovery Basics",
                author=None,
                section=None,
                page_range=None,
                score=0.3,
            )
        ]
    )

    assert "[1] Source: Recovery Basics (article)" in formatted
    assert "Section:" not in formatted
    assert "Pages:" not in formatted


def test_format_rag_context_returns_empty_for_no_chunks() -> None:
    assert format_rag_context([]) == ""


@pytest.mark.asyncio
async def test_llm_node_appends_rag_context_when_results_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_llm_node(self, chat_ctx, tools, model_settings):
        captured["chat_ctx"] = chat_ctx
        return "OK"

    class FakeRagEngine:
        async def search(self, query_text: str, language: str | None):
            captured["query_text"] = query_text
            captured["language"] = language
            return [
                RagChunk(
                    chunk_id=uuid.uuid4(),
                    content="Use recovery routines.",
                    source_type="book",
                    title="Burnout Prevention",
                    author="Dr. Smith",
                    section="Chapter 2",
                    page_range="21-24",
                    score=0.5,
                )
            ]

    monkeypatch.setattr(agent_module.Agent, "llm_node", fake_llm_node)

    chat_ctx = llm.ChatContext.empty()
    chat_ctx.add_message(role="user", content="How do I recover from burnout?")

    agent = agent_module.TwypeAgent(
        instructions=AGENT_KWARGS["instructions"],
        mode_voice_guidance=AGENT_KWARGS["mode_voice_guidance"],
        mode_text_guidance=AGENT_KWARGS["mode_text_guidance"],
        default_language="en",
        rag_engine=FakeRagEngine(),
        thinking_sounds_enabled=False,
    )

    result = await agent.llm_node(chat_ctx, [], None)

    assert result == "OK"
    assert captured["query_text"] == "How do I recover from burnout?"
    assert captured["language"] == "en"
    assert len(agent._last_rag_chunks) == 1
    rag_message = captured["chat_ctx"].items[-1]
    assert isinstance(rag_message, llm.ChatMessage)
    assert rag_message.role == "system"
    assert "[1] Source: Burnout Prevention" in rag_message.text_content
    assert "Burnout Prevention" in rag_message.text_content


@pytest.mark.asyncio
async def test_llm_node_skips_rag_injection_when_search_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_llm_node(self, chat_ctx, tools, model_settings):
        captured["chat_ctx"] = chat_ctx
        return "OK"

    class FakeRagEngine:
        async def search(self, query_text: str, language: str | None):
            _ = (query_text, language)
            return []

    monkeypatch.setattr(agent_module.Agent, "llm_node", fake_llm_node)

    chat_ctx = llm.ChatContext.empty()
    chat_ctx.add_message(role="user", content="How do I recover from burnout?")

    agent = agent_module.TwypeAgent(
        instructions=AGENT_KWARGS["instructions"],
        mode_voice_guidance=AGENT_KWARGS["mode_voice_guidance"],
        mode_text_guidance=AGENT_KWARGS["mode_text_guidance"],
        rag_engine=FakeRagEngine(),
        thinking_sounds_enabled=False,
    )

    await agent.llm_node(chat_ctx, [], None)

    assert len(captured["chat_ctx"].items) == 2
    assert agent._last_rag_chunks == []


@pytest.mark.asyncio
async def test_llm_node_degrades_gracefully_when_rag_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_llm_node(self, chat_ctx, tools, model_settings):
        captured["chat_ctx"] = chat_ctx
        return "OK"

    class FakeRagEngine:
        async def search(self, query_text: str, language: str | None):
            _ = (query_text, language)
            raise RuntimeError("boom")

    monkeypatch.setattr(agent_module.Agent, "llm_node", fake_llm_node)

    chat_ctx = llm.ChatContext.empty()
    chat_ctx.add_message(role="user", content="How do I recover from burnout?")

    agent = agent_module.TwypeAgent(
        instructions=AGENT_KWARGS["instructions"],
        mode_voice_guidance=AGENT_KWARGS["mode_voice_guidance"],
        mode_text_guidance=AGENT_KWARGS["mode_text_guidance"],
        rag_engine=FakeRagEngine(),
        thinking_sounds_enabled=False,
    )

    await agent.llm_node(chat_ctx, [], None)

    assert len(captured["chat_ctx"].items) == 2
    assert agent._last_rag_chunks == []
