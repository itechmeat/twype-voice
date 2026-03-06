from __future__ import annotations

from pathlib import Path

import pytest
from src.knowledge_ingestion.manifest import ManifestError, load_manifest


def test_load_manifest_parses_valid_entries_and_skips_invalid(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    (tmp_path / "manifest.yaml").write_text(
        """
sources:
  - file: "guide.pdf"
    source_type: "article"
    title: "Useful Guide"
    language: "en"
    tags: ["stress"]
  - file: "broken.pdf"
    source_type: "unknown"
    title: "Broken"
    language: "en"
  - file: "missing-title.pdf"
    source_type: "book"
    language: "en"
""".strip(),
        encoding="utf-8",
    )

    sources = load_manifest(tmp_path)

    assert len(sources) == 1
    assert sources[0].file == "guide.pdf"
    assert "Skipping manifest entry 2" in caplog.text
    assert "Skipping manifest entry 3" in caplog.text


def test_load_manifest_requires_manifest_file(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match=r"manifest\.yaml not found"):
        load_manifest(tmp_path)
