from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

import tiktoken

from .types import ChunkDraft, ExtractedDocument, ExtractedSegment

_PARAGRAPH_BREAK_PATTERN = re.compile(r"\n{2,}")
_SENTENCE_PATTERN = re.compile(r".+?(?:[.!?](?=\s|$)|$)", re.DOTALL)
_WORD_PATTERN = re.compile(r"\S+\s*")


@dataclass(slots=True, frozen=True)
class ChunkingConfig:
    chunk_size_tokens: int = 700
    chunk_overlap_tokens: int = 50
    encoding_name: str = "cl100k_base"


@dataclass(slots=True, frozen=True)
class _SegmentSpan:
    start: int
    end: int
    section: str | None
    page_number: int | None


@dataclass(slots=True, frozen=True)
class _TextUnit:
    start: int
    end: int
    token_count: int


def _build_full_text(segments: list[ExtractedSegment]) -> tuple[str, list[_SegmentSpan]]:
    parts: list[str] = []
    spans: list[_SegmentSpan] = []
    cursor = 0

    for index, segment in enumerate(segments):
        if index > 0:
            parts.append("\n\n")
            cursor += 2

        text = segment.text.strip()
        start = cursor
        end = start + len(text)
        parts.append(text)
        spans.append(
            _SegmentSpan(
                start=start,
                end=end,
                section=segment.section,
                page_number=segment.page_number,
            )
        )
        cursor = end

    return "".join(parts), spans


def _format_page_range(page_numbers: list[int]) -> str | None:
    if not page_numbers:
        return None
    first = min(page_numbers)
    last = max(page_numbers)
    if first == last:
        return str(first)
    return f"{first}-{last}"


def _trim_range(full_text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and full_text[start].isspace():
        start += 1
    while end > start and full_text[end - 1].isspace():
        end -= 1
    return start, end


def _token_count(text: str, encoding: tiktoken.Encoding) -> int:
    return len(encoding.encode(text))


def _paragraph_ranges(full_text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    cursor = 0
    for match in _PARAGRAPH_BREAK_PATTERN.finditer(full_text):
        start, end = _trim_range(full_text, cursor, match.start())
        if start < end:
            ranges.append((start, end))
        cursor = match.end()

    start, end = _trim_range(full_text, cursor, len(full_text))
    if start < end:
        ranges.append((start, end))
    return ranges


def _sentence_ranges(full_text: str, start: int, end: int) -> list[tuple[int, int]]:
    text = full_text[start:end]
    ranges: list[tuple[int, int]] = []
    for match in _SENTENCE_PATTERN.finditer(text):
        sentence_start = start + match.start()
        sentence_end = start + match.end()
        sentence_start, sentence_end = _trim_range(full_text, sentence_start, sentence_end)
        if sentence_start < sentence_end:
            ranges.append((sentence_start, sentence_end))
    return ranges or [(start, end)]


def _token_split_ranges(
    full_text: str,
    start: int,
    end: int,
    *,
    encoding: tiktoken.Encoding,
    chunk_size_tokens: int,
) -> list[tuple[int, int]]:
    span_text = full_text[start:end]
    token_ids = encoding.encode(span_text)
    if not token_ids:
        return []

    ranges: list[tuple[int, int]] = []
    search_cursor = 0
    for token_start in range(0, len(token_ids), chunk_size_tokens):
        token_end = min(len(token_ids), token_start + chunk_size_tokens)
        part = encoding.decode(token_ids[token_start:token_end])
        local_start = span_text.find(part, search_cursor)
        if local_start < 0:
            local_start = search_cursor
        local_end = local_start + len(part)
        range_start, range_end = _trim_range(full_text, start + local_start, start + local_end)
        if range_start < range_end:
            ranges.append((range_start, range_end))
        search_cursor = local_end
    return ranges


def _word_ranges(
    full_text: str,
    start: int,
    end: int,
    *,
    encoding: tiktoken.Encoding,
    chunk_size_tokens: int,
) -> list[tuple[int, int]]:
    text = full_text[start:end]
    ranges: list[tuple[int, int]] = []
    current_start: int | None = None
    current_end: int | None = None

    for match in _WORD_PATTERN.finditer(text):
        word_start = start + match.start()
        word_end = start + match.end()
        trimmed_start, trimmed_end = _trim_range(full_text, word_start, word_end)
        if trimmed_start >= trimmed_end:
            continue

        word_text = full_text[trimmed_start:trimmed_end]
        if _token_count(word_text, encoding) > chunk_size_tokens:
            if current_start is not None and current_end is not None:
                ranges.append((current_start, current_end))
                current_start = None
                current_end = None
            ranges.extend(
                _token_split_ranges(
                    full_text,
                    trimmed_start,
                    trimmed_end,
                    encoding=encoding,
                    chunk_size_tokens=chunk_size_tokens,
                )
            )
            continue

        if current_start is None or current_end is None:
            current_start = trimmed_start
            current_end = trimmed_end
            continue

        candidate_end = trimmed_end
        candidate_text = full_text[current_start:candidate_end].strip()
        if _token_count(candidate_text, encoding) <= chunk_size_tokens:
            current_end = candidate_end
            continue

        ranges.append((current_start, current_end))
        current_start = trimmed_start
        current_end = trimmed_end

    if current_start is not None and current_end is not None:
        ranges.append((current_start, current_end))
    return ranges


def _build_units(
    full_text: str,
    *,
    encoding: tiktoken.Encoding,
    chunk_size_tokens: int,
) -> list[_TextUnit]:
    units: list[_TextUnit] = []

    def add_range(start: int, end: int) -> None:
        text = full_text[start:end].strip()
        if not text:
            return
        token_count = _token_count(text, encoding)
        units.append(_TextUnit(start=start, end=end, token_count=token_count))

    for paragraph_start, paragraph_end in _paragraph_ranges(full_text):
        paragraph_text = full_text[paragraph_start:paragraph_end]
        if _token_count(paragraph_text, encoding) <= chunk_size_tokens:
            add_range(paragraph_start, paragraph_end)
            continue

        for sentence_start, sentence_end in _sentence_ranges(
            full_text,
            paragraph_start,
            paragraph_end,
        ):
            sentence_text = full_text[sentence_start:sentence_end]
            if _token_count(sentence_text, encoding) <= chunk_size_tokens:
                add_range(sentence_start, sentence_end)
                continue

            for word_start, word_end in _word_ranges(
                full_text,
                sentence_start,
                sentence_end,
                encoding=encoding,
                chunk_size_tokens=chunk_size_tokens,
            ):
                add_range(word_start, word_end)

    return units


def _chunk_token_count(
    full_text: str,
    units: list[_TextUnit],
    start_index: int,
    end_index: int,
    *,
    encoding: tiktoken.Encoding,
) -> int:
    chunk_text = full_text[units[start_index].start : units[end_index].end].strip()
    return _token_count(chunk_text, encoding)


def _next_chunk_start(
    full_text: str,
    units: list[_TextUnit],
    current_start: int,
    current_end: int,
    *,
    encoding: tiktoken.Encoding,
    overlap_tokens: int,
) -> int:
    if current_end + 1 >= len(units) or overlap_tokens <= 0:
        return current_end + 1

    candidate_start = current_end
    while candidate_start > current_start:
        overlap_count = _chunk_token_count(
            full_text,
            units,
            candidate_start,
            current_end,
            encoding=encoding,
        )
        if overlap_count >= overlap_tokens:
            return candidate_start
        candidate_start -= 1

    return current_end + 1


def chunk_document(
    document: ExtractedDocument,
    config: ChunkingConfig | None = None,
) -> list[ChunkDraft]:
    if not document.segments:
        return []

    resolved_config = config or ChunkingConfig()
    encoding = tiktoken.get_encoding(resolved_config.encoding_name)
    full_text, spans = _build_full_text(document.segments)
    units = _build_units(
        full_text,
        encoding=encoding,
        chunk_size_tokens=resolved_config.chunk_size_tokens,
    )
    if not units:
        return []

    chunks: list[ChunkDraft] = []
    index = 0
    while index < len(units):
        end_index = index
        while end_index + 1 < len(units):
            candidate_tokens = _chunk_token_count(
                full_text,
                units,
                index,
                end_index + 1,
                encoding=encoding,
            )
            if candidate_tokens > resolved_config.chunk_size_tokens:
                break
            end_index += 1

        chunk_start = units[index].start
        chunk_end = units[end_index].end
        chunk_text = full_text[chunk_start:chunk_end].strip()

        overlapping_spans = [
            span for span in spans if span.end > chunk_start and span.start < chunk_end
        ]
        sections = [span.section for span in overlapping_spans if span.section]
        page_numbers = [
            span.page_number for span in overlapping_spans if span.page_number is not None
        ]
        section = Counter(sections).most_common(1)[0][0] if sections else None

        chunks.append(
            ChunkDraft(
                content=chunk_text,
                section=section,
                page_range=_format_page_range(page_numbers),
                language=document.source.language,
                token_count=_token_count(chunk_text, encoding),
            )
        )

        next_index = _next_chunk_start(
            full_text,
            units,
            index,
            end_index,
            encoding=encoding,
            overlap_tokens=resolved_config.chunk_overlap_tokens,
        )
        if next_index <= index:
            next_index = end_index + 1
        index = next_index

    return chunks
