from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from rag import RagChunk

VOICE_DELIMITER = "---VOICE---"
TEXT_DELIMITER = "---TEXT---"
_DELIMITERS = (
    (VOICE_DELIMITER, "voice"),
    (TEXT_DELIMITER, "text"),
)
_REFERENCE_PATTERN = re.compile(r"\[(\d+)\]")
_MULTISPACE_PATTERN = re.compile(r"\s{2,}")


@dataclass(slots=True, frozen=True)
class TextItem:
    text: str
    chunk_ids: list[UUID]


@dataclass(slots=True, frozen=True)
class DualLayerResult:
    voice_text: str
    text_items: list[TextItem]
    all_chunk_ids: list[UUID]


class DualLayerStreamParser:
    def __init__(
        self,
        tokens: AsyncIterable[str],
        *,
        rag_chunks: list[RagChunk] | None = None,
    ) -> None:
        self._tokens = tokens
        self._rag_chunks = rag_chunks or []
        self._buffer = ""
        self._voice_parts: list[str] = []
        self._text_parts: list[str] = []
        self._raw_parts: list[str] = []
        self._section = "voice"
        self._done = asyncio.Event()
        self._result: DualLayerResult | None = None
        self._consumed = False

    @property
    def full_text(self) -> str:
        return "".join(self._raw_parts)

    async def iter_voice_tokens(self) -> AsyncIterator[str]:
        if self._consumed:
            raise RuntimeError("dual-layer parser stream already consumed")

        self._consumed = True
        try:
            async for token in self._tokens:
                if not token:
                    continue

                self._raw_parts.append(token)
                self._buffer += token
                for piece in self._drain_buffer(final=False):
                    yield piece

            for piece in self._drain_buffer(final=True):
                yield piece
        finally:
            if not self._done.is_set():
                self._result = build_dual_layer_result(
                    voice_text="".join(self._voice_parts),
                    text_part="".join(self._text_parts),
                    rag_chunks=self._rag_chunks,
                )
                self._done.set()

    async def result(self) -> DualLayerResult:
        await self._done.wait()
        if self._result is None:
            raise RuntimeError("dual-layer parser did not produce a result")
        return self._result

    def _drain_buffer(self, *, final: bool) -> list[str]:
        emitted: list[str] = []

        while self._section != "text":
            delimiter_match = _find_next_delimiter(self._buffer)
            if delimiter_match is None:
                break

            delimiter_index, delimiter, next_section = delimiter_match
            prefix = _strip_trailing_boundary(self._buffer[:delimiter_index])
            if prefix:
                emitted.extend(self._emit_voice(prefix))

            remainder = self._buffer[delimiter_index + len(delimiter) :]
            self._buffer = _strip_leading_boundary(remainder)
            self._section = next_section

            if self._section == "text":
                if self._buffer:
                    self._text_parts.append(self._buffer)
                    self._buffer = ""
                break

        if self._section == "text":
            if self._buffer:
                self._text_parts.append(self._buffer)
                self._buffer = ""
            return emitted

        if final:
            if self._buffer:
                emitted.extend(self._emit_voice(self._buffer))
                self._buffer = ""
            return emitted

        holdback = _prefix_holdback_length(self._buffer)
        safe_length = len(self._buffer) - holdback
        if safe_length:
            emitted.extend(self._emit_voice(self._buffer[:safe_length]))
            self._buffer = self._buffer[safe_length:]

        return emitted

    def _emit_voice(self, text: str) -> list[str]:
        if not text:
            return []

        self._voice_parts.append(text)
        return [text]


def build_dual_layer_result(
    *,
    voice_text: str,
    text_part: str,
    rag_chunks: list[RagChunk] | None = None,
) -> DualLayerResult:
    text_items = parse_text_items(text_part, rag_chunks or [])
    all_chunk_ids: list[UUID] = []
    seen_chunk_ids: set[UUID] = set()

    for item in text_items:
        for chunk_id in item.chunk_ids:
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            all_chunk_ids.append(chunk_id)

    return DualLayerResult(
        voice_text=voice_text.strip(),
        text_items=text_items,
        all_chunk_ids=all_chunk_ids,
    )


def parse_dual_layer_stream(
    tokens: AsyncIterable[str],
    *,
    rag_chunks: list[RagChunk] | None = None,
) -> DualLayerStreamParser:
    return DualLayerStreamParser(tokens, rag_chunks=rag_chunks)


def parse_text_items(text_part: str, rag_chunks: list[RagChunk]) -> list[TextItem]:
    items: list[TextItem] = []

    for raw_line in text_part.splitlines():
        line = raw_line.strip()
        if not line.startswith(("- ", "* ")):
            continue

        body = line[2:].strip()
        if not body:
            continue

        chunk_ids: list[UUID] = []
        seen_chunk_ids: set[UUID] = set()
        for ref_index in _REFERENCE_PATTERN.findall(body):
            try:
                chunk_index = int(ref_index) - 1
            except ValueError:
                continue

            if chunk_index < 0:
                continue

            try:
                chunk = rag_chunks[chunk_index]
            except IndexError:
                continue

            if chunk.chunk_id in seen_chunk_ids:
                continue

            seen_chunk_ids.add(chunk.chunk_id)
            chunk_ids.append(chunk.chunk_id)

        clean_text = _REFERENCE_PATTERN.sub("", body)
        clean_text = re.sub(r"\s+([,.;:!?])", r"\1", clean_text)
        clean_text = _MULTISPACE_PATTERN.sub(" ", clean_text).strip()
        if not clean_text:
            continue

        items.append(TextItem(text=clean_text, chunk_ids=chunk_ids))

    return items


def _find_next_delimiter(buffer: str) -> tuple[int, str, str] | None:
    positions: list[tuple[int, str, str]] = []
    for delimiter, next_section in _DELIMITERS:
        position = buffer.find(delimiter)
        if position >= 0:
            positions.append((position, delimiter, next_section))

    if not positions:
        return None

    positions.sort(key=lambda item: item[0])
    return positions[0]


def _prefix_holdback_length(buffer: str) -> int:
    max_holdback = 0
    for delimiter, _next_section in _DELIMITERS:
        upper_bound = min(len(buffer), len(delimiter) - 1)
        for prefix_length in range(upper_bound, 0, -1):
            if delimiter.startswith(buffer[-prefix_length:]):
                max_holdback = max(max_holdback, prefix_length)
                break
    return max_holdback


def _strip_trailing_boundary(text: str) -> str:
    if text.endswith("\r\n"):
        return text[:-2]
    if text.endswith("\r") or text.endswith("\n"):
        return text[:-1]
    return text


def _strip_leading_boundary(text: str) -> str:
    if text.startswith("\r\n"):
        return text[2:]
    if text.startswith("\r") or text.startswith("\n"):
        return text[1:]
    return text
