from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True, frozen=True)
class ManifestSource:
    file: str
    source_type: str
    title: str
    language: str
    author: str | None = None
    url: str | None = None
    tags: list[str] = field(default_factory=list)

    def resolve_path(self, base_directory: Path) -> Path:
        resolved_base = base_directory.resolve()
        resolved_path = (base_directory / self.file).resolve()
        if not resolved_path.is_relative_to(resolved_base):
            raise ValueError(f"File path escapes base directory: {self.file}")
        return resolved_path


@dataclass(slots=True, frozen=True)
class ExtractedSegment:
    text: str
    section: str | None = None
    page_number: int | None = None


@dataclass(slots=True, frozen=True)
class ExtractedDocument:
    source: ManifestSource
    path: Path
    segments: list[ExtractedSegment]


@dataclass(slots=True, frozen=True)
class ChunkDraft:
    content: str
    section: str | None
    page_range: str | None
    language: str
    token_count: int


@dataclass(slots=True, frozen=True)
class EmbeddedChunk(ChunkDraft):
    embedding: list[float]
