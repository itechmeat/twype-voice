from __future__ import annotations

from itertools import pairwise
from pathlib import Path

from src.knowledge_ingestion.chunking import ChunkingConfig, chunk_document
from src.knowledge_ingestion.types import ExtractedDocument, ExtractedSegment

from .knowledge_test_utils import make_manifest_source


def test_chunk_document_splits_long_documents() -> None:
    sentence = "Grounding helps bring attention back to the present moment."
    long_text = " ".join([sentence] * 180)
    document = ExtractedDocument(
        source=make_manifest_source(),
        path=Path("fixture.txt"),
        segments=[ExtractedSegment(text=long_text, section="Long form")],
    )

    chunks = chunk_document(
        document,
        ChunkingConfig(chunk_size_tokens=700, chunk_overlap_tokens=50),
    )

    assert len(chunks) >= 2
    assert all(chunk.token_count <= 800 for chunk in chunks)
    assert chunks[0].section == "Long form"


def test_chunk_document_keeps_short_document_in_single_chunk() -> None:
    document = ExtractedDocument(
        source=make_manifest_source(),
        path=Path("fixture.txt"),
        segments=[ExtractedSegment(text="Short grounding note.", section="Note")],
    )

    chunks = chunk_document(document)

    assert len(chunks) == 1
    assert chunks[0].content == "Short grounding note."
    assert chunks[0].token_count > 0


def test_chunk_document_preserves_sentence_boundaries() -> None:
    sentences = [
        "Grounding begins with a slow exhale.",
        "Then the person names five visible objects.",
        "After that they describe three sounds in the room.",
    ]
    text = " ".join(sentences * 80)
    document = ExtractedDocument(
        source=make_manifest_source(),
        path=Path("fixture.txt"),
        segments=[ExtractedSegment(text=text, section="Exercise", page_number=12)],
    )

    chunks = chunk_document(
        document,
        ChunkingConfig(chunk_size_tokens=150, chunk_overlap_tokens=25),
    )

    assert len(chunks) > 1
    assert all(chunk.content.rstrip()[-1] in ".!?" for chunk in chunks[:-1])
    assert all(chunk.page_range == "12" for chunk in chunks)


def test_chunk_document_keeps_overlap_and_section_metadata() -> None:
    sentence_a = "Breathing slowly helps reduce acute stress."
    sentence_b = "Naming visible objects helps restore orientation."
    document = ExtractedDocument(
        source=make_manifest_source(),
        path=Path("fixture.txt"),
        segments=[
            ExtractedSegment(text=" ".join([sentence_a] * 25), section="Breathing", page_number=3),
            ExtractedSegment(
                text=" ".join([sentence_b] * 25),
                section="Orientation",
                page_number=4,
            ),
        ],
    )

    chunks = chunk_document(
        document,
        ChunkingConfig(chunk_size_tokens=80, chunk_overlap_tokens=20),
    )

    assert len(chunks) > 1
    assert chunks[0].section == "Breathing"
    assert chunks[-1].section == "Orientation"
    assert any(
        current.content.split(". ")[-1].rstrip(".!?") in following.content
        for current, following in pairwise(chunks)
    )
