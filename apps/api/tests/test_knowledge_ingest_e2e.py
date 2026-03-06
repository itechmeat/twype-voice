from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from src.knowledge_constants import EMBEDDING_DIMENSION
from src.knowledge_ingestion import (
    EmbeddingClient,
    EmbeddingInput,
    EmbeddingSettings,
    ingest_directory,
)
from src.models import KnowledgeChunk, KnowledgeSource

from .knowledge_test_utils import write_pdf


@pytest.mark.asyncio
async def test_ingest_directory_extracts_chunks_embeds_and_loads(
    tmp_path: Path,
    session,
) -> None:
    write_pdf(
        tmp_path / "grounding.pdf",
        [
            "Grounding starts with naming five visible objects.",
            "After that, the person should describe four things they can touch.",
        ],
    )
    (tmp_path / "manifest.yaml").write_text(
        """
sources:
  - file: "grounding.pdf"
    source_type: "article"
    title: "Grounding Steps"
    language: "en"
    author: "Fixture Author"
    tags: ["grounding", "stress"]
""".strip(),
        encoding="utf-8",
    )

    class FakeEmbeddingClient(EmbeddingClient):
        def __init__(self) -> None:
            super().__init__(EmbeddingSettings(api_key="test-key", base_url="https://gemini.test"))

        async def embed_inputs(self, inputs: list[EmbeddingInput]) -> list[list[float]]:
            return [[0.001] * EMBEDDING_DIMENSION for _ in inputs]

    processed_sources = await ingest_directory(
        tmp_path,
        session=session,
        embedding_client=FakeEmbeddingClient(),
    )
    await session.commit()

    source = await session.scalar(
        sa.select(KnowledgeSource).where(KnowledgeSource.title == "Grounding Steps")
    )
    chunks = list((await session.execute(sa.select(KnowledgeChunk))).scalars())
    search_vectors = (
        await session.execute(sa.text("SELECT search_vector::text FROM knowledge_chunks"))
    ).scalars()

    assert processed_sources == 1
    assert source is not None
    assert source.author == "Fixture Author"
    assert len(chunks) >= 1
    assert all(chunk.embedding is not None for chunk in chunks)
    assert all(search_vector for search_vector in search_vectors)


@pytest.mark.asyncio
async def test_ingest_directory_embeds_sources_independently(
    tmp_path: Path,
    session,
) -> None:
    write_pdf(tmp_path / "first.pdf", ["First source page one."])
    write_pdf(tmp_path / "second.pdf", ["Second source page one.", "Second source page two."])
    (tmp_path / "manifest.yaml").write_text(
        """
sources:
  - file: "first.pdf"
    source_type: "article"
    title: "First"
    language: "en"
  - file: "second.pdf"
    source_type: "article"
    title: "Second"
    language: "en"
""".strip(),
        encoding="utf-8",
    )

    class FakeEmbeddingClient(EmbeddingClient):
        def __init__(self) -> None:
            super().__init__(EmbeddingSettings(api_key="test-key", base_url="https://gemini.test"))
            self.batch_sizes: list[int] = []
            self.batch_titles: list[str | None] = []

        async def embed_inputs(self, inputs: list[EmbeddingInput]) -> list[list[float]]:
            self.batch_sizes.append(len(inputs))
            self.batch_titles.append(inputs[0].title if inputs else None)
            return [[0.001] * EMBEDDING_DIMENSION for _ in inputs]

    embedding_client = FakeEmbeddingClient()

    processed_sources = await ingest_directory(
        tmp_path,
        session=session,
        embedding_client=embedding_client,
    )
    await session.commit()

    assert processed_sources == 2
    assert len(embedding_client.batch_sizes) == 2
    assert all(batch_size >= 1 for batch_size in embedding_client.batch_sizes)
    assert embedding_client.batch_titles == ["First", "Second"]


@pytest.mark.asyncio
async def test_ingest_directory_skips_missing_and_unsupported_sources(
    tmp_path: Path,
    session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    (tmp_path / "notes.txt").write_text("Unsupported", encoding="utf-8")
    (tmp_path / "manifest.yaml").write_text(
        """
sources:
  - file: "missing.pdf"
    source_type: "article"
    title: "Missing"
    language: "en"
  - file: "notes.txt"
    source_type: "article"
    title: "Unsupported"
    language: "en"
""".strip(),
        encoding="utf-8",
    )

    class FakeEmbeddingClient(EmbeddingClient):
        def __init__(self) -> None:
            super().__init__(EmbeddingSettings(api_key="test-key", base_url="https://gemini.test"))
            self.calls = 0

        async def embed_inputs(self, inputs: list[EmbeddingInput]) -> list[list[float]]:
            self.calls += 1
            return [[0.001] * EMBEDDING_DIMENSION for _ in inputs]

    embedding_client = FakeEmbeddingClient()

    with caplog.at_level("WARNING"):
        processed_sources = await ingest_directory(
            tmp_path,
            session=session,
            embedding_client=embedding_client,
        )

    source_count = await session.scalar(sa.select(sa.func.count()).select_from(KnowledgeSource))

    assert processed_sources == 0
    assert embedding_client.calls == 0
    assert source_count == 0
    assert "Referenced file missing.pdf does not exist; skipping" in caplog.text
    assert "Unsupported file type for notes.txt" in caplog.text


@pytest.mark.asyncio
async def test_ingest_directory_rejects_manifest_path_traversal(
    tmp_path: Path,
    session,
) -> None:
    inner_dir = tmp_path / "inner"
    inner_dir.mkdir()
    outside_file = tmp_path / "outside.pdf"
    write_pdf(outside_file, ["Outside the base directory."])
    (inner_dir / "manifest.yaml").write_text(
        f"""
sources:
  - file: "../{outside_file.name}"
    source_type: "article"
    title: "Outside"
    language: "en"
""".strip(),
        encoding="utf-8",
    )

    class FakeEmbeddingClient(EmbeddingClient):
        def __init__(self) -> None:
            super().__init__(EmbeddingSettings(api_key="test-key", base_url="https://gemini.test"))

        async def embed_inputs(self, inputs: list[EmbeddingInput]) -> list[list[float]]:
            return [[0.001] * EMBEDDING_DIMENSION for _ in inputs]

    with pytest.raises(ValueError, match="escapes base directory"):
        await ingest_directory(
            inner_dir,
            session=session,
            embedding_client=FakeEmbeddingClient(),
        )
