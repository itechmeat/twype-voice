from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import sqlalchemy as sa
from languages import normalize_language_code
from settings import AgentSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.knowledge_ingestion.embeddings import (
    EmbeddingClient,
    EmbeddingInput,
    EmbeddingSettings,
)

logger = logging.getLogger("twype-agent.rag")

_VECTOR_LIMIT = 20
_TEXT_LIMIT = 20
_RRF_K = 60

HYBRID_SEARCH_SQL = sa.text(
    """
    WITH query_input AS (
        SELECT
            CAST(:query_embedding AS vector(1536)) AS embedding,
            plainto_tsquery('simple', :query_text) AS ts_query
    ),
    vector_search AS (
        SELECT
            chunk.id AS chunk_id,
            row_number() OVER (
                ORDER BY chunk.embedding <=> query_input.embedding, chunk.id
            ) AS rank_vector
        FROM knowledge_chunks AS chunk
        CROSS JOIN query_input
        WHERE chunk.embedding IS NOT NULL
        ORDER BY chunk.embedding <=> query_input.embedding, chunk.id
        LIMIT 20
    ),
    text_search AS (
        SELECT
            chunk.id AS chunk_id,
            row_number() OVER (
                ORDER BY ts_rank(chunk.search_vector, query_input.ts_query) DESC, chunk.id
            ) AS rank_text
        FROM knowledge_chunks AS chunk
        CROSS JOIN query_input
        WHERE chunk.search_vector @@ query_input.ts_query
        ORDER BY ts_rank(chunk.search_vector, query_input.ts_query) DESC, chunk.id
        LIMIT 20
    ),
    combined AS (
        SELECT
            COALESCE(vector_search.chunk_id, text_search.chunk_id) AS chunk_id,
            vector_search.rank_vector,
            text_search.rank_text
        FROM vector_search
        FULL OUTER JOIN text_search
            ON text_search.chunk_id = vector_search.chunk_id
    ),
    ranked AS (
        SELECT
            combined.chunk_id,
            (
                CASE
                    WHEN combined.rank_vector IS NULL THEN 0.0
                    ELSE 1.0 / (:rrf_k + combined.rank_vector)
                END
                +
                CASE
                    WHEN combined.rank_text IS NULL THEN 0.0
                    ELSE 1.0 / (:rrf_k + combined.rank_text)
                END
            ) AS base_score
        FROM combined
    )
    SELECT
        chunk.id AS chunk_id,
        chunk.content,
        source.source_type,
        source.title,
        source.author,
        chunk.section,
        chunk.page_range,
        ranked.base_score
            * CASE
                WHEN :language IS NOT NULL AND source.language = :language THEN :language_boost
                ELSE 1.0
            END AS score
    FROM ranked
    JOIN knowledge_chunks AS chunk
        ON chunk.id = ranked.chunk_id
    JOIN knowledge_sources AS source
        ON source.id = chunk.source_id
    ORDER BY score DESC, chunk.id
    LIMIT :top_k
    """
).bindparams(
    sa.bindparam("query_embedding", type_=sa.String()),
    sa.bindparam("query_text", type_=sa.String()),
    sa.bindparam("rrf_k", type_=sa.Integer(), value=_RRF_K),
    sa.bindparam("language", type_=sa.String()),
    sa.bindparam("language_boost", type_=sa.Float()),
    sa.bindparam("top_k", type_=sa.Integer()),
)


class EmbeddingClientProtocol(Protocol):
    async def embed_inputs(self, inputs: list[EmbeddingInput]) -> list[list[float]]: ...


@dataclass(slots=True, frozen=True)
class RagChunk:
    chunk_id: UUID
    content: str
    source_type: str
    title: str
    author: str | None
    section: str | None
    page_range: str | None
    score: float


class RagEngine:
    def __init__(
        self,
        settings: AgentSettings,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        embedding_client: EmbeddingClientProtocol | None = None,
    ) -> None:
        self._settings = settings
        self._sessionmaker = sessionmaker
        if settings.GOOGLE_API_KEY is None:
            raise RuntimeError("GOOGLE_API_KEY must be set when RAG is enabled")
        self._embedding_client = embedding_client or EmbeddingClient(
            EmbeddingSettings(
                api_key=settings.GOOGLE_API_KEY,
                timeout_seconds=settings.RAG_EMBEDDING_TIMEOUT,
                default_task_type="RETRIEVAL_QUERY",
            )
        )

    async def embed_query(self, text: str) -> list[float] | None:
        cleaned = text.strip()
        if not cleaned:
            return None

        try:
            embeddings = await self._embedding_client.embed_inputs([EmbeddingInput(text=cleaned)])
        except Exception:
            logger.exception("failed to generate query embedding")
            return None

        if not embeddings or not embeddings[0]:
            return None
        return embeddings[0]

    async def search(self, query_text: str, language: str | None) -> list[RagChunk]:
        cleaned_query = query_text.strip()
        if not cleaned_query:
            return []

        embedding = await self.embed_query(cleaned_query)
        if embedding is None:
            return []

        params = {
            "query_embedding": _format_vector_literal(embedding),
            "query_text": cleaned_query,
            "rrf_k": _RRF_K,
            "language": normalize_language_code(language),
            "language_boost": self._settings.RAG_LANGUAGE_BOOST,
            "top_k": self._settings.RAG_TOP_K,
        }

        try:
            async with self._sessionmaker() as session:
                result = await session.execute(HYBRID_SEARCH_SQL, params)
        except Exception:
            logger.exception("failed to execute hybrid search")
            return []

        try:
            chunks: list[RagChunk] = []
            for row in result.mappings().all():
                chunks.append(
                    RagChunk(
                        chunk_id=row["chunk_id"],
                        content=str(row["content"]),
                        source_type=str(row["source_type"]),
                        title=str(row["title"]),
                        author=str(row["author"]) if row["author"] is not None else None,
                        section=str(row["section"]) if row["section"] is not None else None,
                        page_range=(
                            str(row["page_range"]) if row["page_range"] is not None else None
                        ),
                        score=float(row["score"]),
                    )
                )
        except Exception:
            logger.exception("failed to parse hybrid search results")
            return []

        return chunks


def format_rag_context(chunks: list[RagChunk]) -> str:
    if not chunks:
        return ""

    blocks = [
        "[Knowledge Base Context]",
        "The following excerpts are from verified sources. Use them to support your response.",
        "",
    ]
    for chunk in chunks:
        source_line = f"Source: {chunk.title}"
        if chunk.author:
            source_line += f" by {chunk.author}"
        source_line += f" ({chunk.source_type})"
        blocks.append(source_line)

        details: list[str] = []
        if chunk.section:
            details.append(f"Section: {chunk.section}")
        if chunk.page_range:
            details.append(f"Pages: {chunk.page_range}")
        if details:
            blocks.append(" | ".join(details))

        blocks.append("---")
        blocks.append(chunk.content.strip())
        blocks.append("")

    return "\n".join(blocks).rstrip()


def _format_vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in values) + "]"
