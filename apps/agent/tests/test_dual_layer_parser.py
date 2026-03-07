from __future__ import annotations

import uuid

import pytest
from dual_layer_parser import (
    build_dual_layer_result,
    parse_dual_layer_stream,
    parse_text_items,
)
from rag import RagChunk


def _chunk(title: str) -> RagChunk:
    return RagChunk(
        chunk_id=uuid.uuid4(),
        content=f"{title} content",
        source_type="article",
        title=title,
        author=None,
        section=None,
        page_range=None,
        score=0.5,
    )


async def _stream(*tokens: str):
    for token in tokens:
        yield token


@pytest.mark.asyncio
async def test_parse_dual_layer_stream_splits_voice_and_text_parts() -> None:
    chunk_a = _chunk("A")
    chunk_b = _chunk("B")

    parser = parse_dual_layer_stream(
        _stream(
            "---VO",
            "ICE---\nShort ",
            "answer.",
            "\n---TEXT---\n- Point A [1]\n- Point B [2]\n",
        ),
        rag_chunks=[chunk_a, chunk_b],
    )

    voice_tokens = [token async for token in parser.iter_voice_tokens()]
    result = await parser.result()

    assert voice_tokens == ["Short ", "answer."]
    assert result.voice_text == "Short answer."
    assert [item.text for item in result.text_items] == ["Point A", "Point B"]
    assert result.text_items[0].chunk_ids == [chunk_a.chunk_id]
    assert result.text_items[1].chunk_ids == [chunk_b.chunk_id]
    assert result.all_chunk_ids == [chunk_a.chunk_id, chunk_b.chunk_id]


@pytest.mark.asyncio
async def test_parse_dual_layer_stream_falls_back_to_voice_only_without_delimiters() -> None:
    parser = parse_dual_layer_stream(_stream("Plain ", "response", " only."))

    voice_tokens = [token async for token in parser.iter_voice_tokens()]
    result = await parser.result()

    assert voice_tokens == ["Plain ", "response", " only."]
    assert result.voice_text == "Plain response only."
    assert result.text_items == []
    assert result.all_chunk_ids == []


@pytest.mark.asyncio
async def test_parse_dual_layer_stream_supports_empty_voice_part() -> None:
    parser = parse_dual_layer_stream(
        _stream("---TEXT---\n- Only bullets [1]\n"),
        rag_chunks=[_chunk("A")],
    )

    voice_tokens = [token async for token in parser.iter_voice_tokens()]
    result = await parser.result()

    assert voice_tokens == []
    assert result.voice_text == ""
    assert [item.text for item in result.text_items] == ["Only bullets"]
    assert len(result.text_items[0].chunk_ids) == 1


@pytest.mark.asyncio
async def test_parse_dual_layer_stream_handles_delimiter_mid_token() -> None:
    parser = parse_dual_layer_stream(
        _stream("end.\n---TEXT---\n- Start [1]"),
        rag_chunks=[_chunk("A")],
    )

    voice_tokens = [token async for token in parser.iter_voice_tokens()]
    result = await parser.result()

    assert voice_tokens == ["end."]
    assert result.voice_text == "end."
    assert [item.text for item in result.text_items] == ["Start"]


def test_parse_text_items_ignores_out_of_range_and_non_bullet_lines() -> None:
    chunk_a = _chunk("A")
    items = parse_text_items(
        "Header\n- Supported [1][9]\nTrailing\n* Reasoning point",
        [chunk_a],
    )

    assert [item.text for item in items] == ["Supported", "Reasoning point"]
    assert items[0].chunk_ids == [chunk_a.chunk_id]
    assert items[1].chunk_ids == []


def test_parse_text_items_ignores_zero_reference() -> None:
    chunk_a = _chunk("A")

    items = parse_text_items("- Invalid [0]\n- Valid [1]", [chunk_a])

    assert [item.text for item in items] == ["Invalid", "Valid"]
    assert items[0].chunk_ids == []
    assert items[1].chunk_ids == [chunk_a.chunk_id]


def test_build_dual_layer_result_deduplicates_chunk_ids() -> None:
    chunk_a = _chunk("A")
    chunk_b = _chunk("B")

    result = build_dual_layer_result(
        voice_text="Voice",
        text_part="- Point A [1][2]\n- Point B [1]\n",
        rag_chunks=[chunk_a, chunk_b],
    )

    assert result.voice_text == "Voice"
    assert result.all_chunk_ids == [chunk_a.chunk_id, chunk_b.chunk_id]


@pytest.mark.asyncio
async def test_parse_dual_layer_stream_exposes_full_text_and_blocks_double_consumption() -> None:
    parser = parse_dual_layer_stream(_stream("Hello", "\n---TEXT---\n- Detail"))

    first_pass = [token async for token in parser.iter_voice_tokens()]
    result = await parser.result()

    assert first_pass == ["Hello"]
    assert parser.full_text == "Hello\n---TEXT---\n- Detail"
    assert result.text_items[0].text == "Detail"

    with pytest.raises(RuntimeError, match="already consumed"):
        async for _token in parser.iter_voice_tokens():
            pass
