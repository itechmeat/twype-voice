from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from .types import ManifestSource

logger = logging.getLogger(__name__)

ALLOWED_SOURCE_TYPES = {"book", "video", "podcast", "article", "post"}


class ManifestError(RuntimeError):
    pass


class ManifestSourceModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    file: str
    source_type: str
    title: str
    language: str
    author: str | None = None
    url: str | None = None
    tags: list[str] = []

    @field_validator("file", "title", "language")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, value: str) -> str:
        if value not in ALLOWED_SOURCE_TYPES:
            allowed = ", ".join(sorted(ALLOWED_SOURCE_TYPES))
            raise ValueError(f"must be one of: {allowed}")
        return value


def load_manifest(directory: Path) -> list[ManifestSource]:
    manifest_path = directory / "manifest.yaml"
    if not manifest_path.exists():
        raise ManifestError(f"manifest.yaml not found in {directory}")

    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ManifestError("manifest.yaml must contain a mapping with a 'sources' key")

    raw_sources = payload.get("sources", [])
    if not isinstance(raw_sources, list):
        raise ManifestError("manifest.yaml 'sources' value must be a list")

    validated_sources: list[ManifestSource] = []
    for index, raw_source in enumerate(raw_sources, start=1):
        try:
            model = ManifestSourceModel.model_validate(raw_source)
        except ValidationError as exc:
            logger.warning("Skipping manifest entry %s: %s", index, exc.errors()[0]["msg"])
            continue

        validated_sources.append(
            ManifestSource(
                file=model.file,
                source_type=model.source_type,
                title=model.title,
                language=model.language,
                author=model.author,
                url=model.url,
                tags=list(model.tags),
            )
        )

    return validated_sources
