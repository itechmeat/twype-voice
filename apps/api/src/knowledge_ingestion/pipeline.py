from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from .chunking import ChunkingConfig, chunk_document
from .embeddings import EmbeddingClient, EmbeddingInput
from .extractors import extract_document
from .loader import DatabaseLoader, PreparedSource
from .manifest import load_manifest
from .types import ChunkDraft, EmbeddedChunk, ManifestSource

logger = logging.getLogger(__name__)


async def ingest_directory(
    directory: Path,
    *,
    session: AsyncSession,
    embedding_client: EmbeddingClient,
    chunking_config: ChunkingConfig | None = None,
    loader: DatabaseLoader | None = None,
) -> int:
    manifest_sources = load_manifest(directory)
    resolved_loader = loader or DatabaseLoader()
    processed_sources = 0

    for source in manifest_sources:
        file_path = source.resolve_path(directory)
        if not file_path.exists():
            logger.warning("Referenced file %s does not exist; skipping", source.file)
            continue

        extracted = extract_document(file_path, source)
        if extracted is None:
            continue

        chunks = chunk_document(extracted, config=chunking_config)
        if not chunks:
            logger.warning("No chunks generated for %s; skipping", source.file)
            continue

        prepared_source = await _prepare_source(source, chunks, embedding_client)
        await resolved_loader.load(session, [prepared_source])
        processed_sources += 1

    return processed_sources


async def _prepare_source(
    source: ManifestSource,
    chunks: list[ChunkDraft],
    embedding_client: EmbeddingClient,
) -> PreparedSource:
    embedding_inputs = [
        EmbeddingInput(
            text=chunk.content,
            title=source.title,
            task_type="RETRIEVAL_DOCUMENT",
        )
        for chunk in chunks
    ]
    embeddings = await embedding_client.embed_inputs(embedding_inputs)

    embedded_chunks = [
        EmbeddedChunk(
            content=chunk.content,
            section=chunk.section,
            page_range=chunk.page_range,
            language=chunk.language,
            token_count=chunk.token_count,
            embedding=embedding,
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]
    return PreparedSource(source=source, chunks=embedded_chunks)
