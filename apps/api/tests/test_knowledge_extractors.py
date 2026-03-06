from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter
from src.knowledge_ingestion.extractors import extract_document

from .knowledge_test_utils import make_manifest_source, write_docx, write_epub, write_pdf


def test_extract_pdf_tracks_page_numbers(tmp_path: Path) -> None:
    file_path = tmp_path / "fixture.pdf"
    write_pdf(
        file_path,
        [
            "Calm breathing starts with a slow exhale.",
            "Ground your feet on the floor.",
        ],
    )

    extracted = extract_document(file_path, make_manifest_source(file="fixture.pdf"))

    assert extracted is not None
    assert [segment.page_number for segment in extracted.segments] == [1, 2]
    assert extracted.segments[0].text.startswith("Calm breathing")


def test_extract_epub_uses_chapter_titles_as_sections(tmp_path: Path) -> None:
    file_path = tmp_path / "fixture.epub"
    write_epub(
        file_path,
        [
            ("Chapter One", ["Start with the room around you."]),
            ("Chapter Two", ["Name the next safe action."]),
        ],
    )

    extracted = extract_document(file_path, make_manifest_source(file="fixture.epub"))

    assert extracted is not None
    assert [segment.section for segment in extracted.segments] == ["Chapter One", "Chapter Two"]


def test_extract_docx_preserves_paragraphs(tmp_path: Path) -> None:
    file_path = tmp_path / "fixture.docx"
    write_docx(file_path, "Grounding", ["First paragraph.", "Second paragraph."])

    extracted = extract_document(file_path, make_manifest_source(file="fixture.docx"))

    assert extracted is not None
    assert [segment.text for segment in extracted.segments] == [
        "First paragraph.",
        "Second paragraph.",
    ]
    assert extracted.segments[0].section == "Grounding"


def test_extract_html_uses_nearest_heading_as_section(tmp_path: Path) -> None:
    file_path = tmp_path / "fixture.html"
    file_path.write_text(
        """
<html>
  <body>
    <h1>Main Section</h1>
    <p>Stay with the sensations in your hands.</p>
    <h2>Next Step</h2>
    <p>Drink a glass of water.</p>
  </body>
</html>
""".strip(),
        encoding="utf-8",
    )

    extracted = extract_document(file_path, make_manifest_source(file="fixture.html"))

    assert extracted is not None
    assert [segment.section for segment in extracted.segments] == ["Main Section", "Next Step"]
    assert extracted.segments[1].text == "Drink a glass of water."


def test_extract_pdf_without_text_returns_none(tmp_path: Path) -> None:
    file_path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=144)
    with file_path.open("wb") as output:
        writer.write(output)

    extracted = extract_document(file_path, make_manifest_source(file="blank.pdf"))

    assert extracted is None


def test_extract_document_returns_none_for_unsupported_type(tmp_path: Path) -> None:
    file_path = tmp_path / "notes.txt"
    file_path.write_text("Unsupported", encoding="utf-8")

    extracted = extract_document(file_path, make_manifest_source(file="notes.txt"))

    assert extracted is None
