## Context

The agent pipeline (S09-S14) currently sends the full LLM output to either TTS (voice mode) or data channel (text mode) without structural separation. The `dual_layer_prompt` (S10) asks the LLM to produce two formulations, but no code parses, splits, or routes them independently. RAG chunks are injected into context (S14) with UUIDs available in `RagChunk.chunk_id`, but `source_ids` on the `Message` model is never populated.

S15 must split a single LLM response stream into a voice part (routed to TTS) and a text part (routed to data channel), with chunk IDs extracted and persisted.

## Goals / Non-Goals

**Goals:**
- Parse the LLM streaming output to extract voice and text parts using delimiter tokens
- Route voice part to TTS and text part to data channel simultaneously in voice mode
- Route only text part to data channel in text mode
- Extract RAG chunk IDs from text part bullet points and persist them in `source_ids`
- Label reasoning points (not backed by RAG) without chunk IDs

**Non-Goals:**
- Client-side rendering of structured responses (S22)
- Source metadata API endpoint (S16)
- Changing the database schema — `source_ids` JSONB and `content` already exist
- Changing the RAG search itself (S14 is complete)

## Decisions

### D1: Delimiter-based structured format over JSON output

The LLM will produce output with simple text delimiters (`---VOICE---` / `---TEXT---`) rather than JSON-wrapped responses.

**Rationale:** Streaming JSON is fragile — incomplete brackets break parsing mid-stream. Text delimiters are trivially detectable in a token stream and degrade gracefully if the LLM omits them (the entire response becomes the voice part as a fallback). This also keeps the prompt simple.

**Alternatives considered:**
- *JSON output:* Requires accumulating the full response before parsing, defeats streaming. Would need a JSON repair step for partial outputs.
- *XML tags:* Similar to delimiters but heavier syntax, more prompt tokens, higher chance of LLM confusion.
- *Tool-use / function calling:* Forces non-streaming, adds latency, overkill for structured text.

### D2: Chunk ID references via inline markers

In the text part, the LLM will reference RAG sources by index markers like `[1]`, `[2]` matching the order of chunks injected in the RAG context. The parser maps indices back to `RagChunk.chunk_id` UUIDs.

**Rationale:** LLMs reliably reproduce small integer references. Asking the LLM to output UUIDs is error-prone and wastes tokens. The mapping is deterministic since `format_rag_context` outputs chunks in a fixed order.

**Alternatives considered:**
- *UUID in output:* LLMs hallucinate long hex strings. Unreliable.
- *Title-based matching:* Fuzzy, ambiguous with similar titles.
- *Post-hoc matching (embedding similarity):* Adds latency, unnecessary when we control the context injection order.

### D3: Store chunk IDs from injected RAG context on the agent instance

The `_inject_rag_context` method already has the `chunks` list. Store it on the agent instance (e.g., `self._last_rag_chunks`) so the response parser can map `[N]` references back to chunk UUIDs without re-querying.

**Rationale:** Zero additional DB/API calls. The chunks are already in memory during the same request cycle. Reset per turn.

### D4: Graceful fallback when delimiters are missing

If the LLM response contains no `---TEXT---` delimiter, the entire output is treated as voice-only. No text part is sent via data channel (beyond the existing transcript). This ensures backward compatibility and robustness.

**Rationale:** LLMs may occasionally ignore formatting instructions. A missing delimiter should not crash the pipeline or produce empty responses.

### D5: Data channel message type `structured_response`

Introduce a new data channel message type `structured_response` for the text part, separate from the existing `chat_response`. This carries an array of bullet points, each with text and optional `chunk_ids`.

**Rationale:** The existing `chat_response` is a flat text string. Structured responses need a different shape (array of items with metadata). Using a new type lets the client differentiate and render appropriately without breaking backward compatibility.

**Format:**
```json
{
  "type": "structured_response",
  "items": [
    {"text": "Point about X", "chunk_ids": ["uuid1", "uuid2"]},
    {"text": "Reasoning point Y", "chunk_ids": []}
  ],
  "is_final": true,
  "message_id": "uuid"
}
```

### D6: Voice mode sends both parts; text mode sends only text part

In voice mode, the parser splits the stream: voice part goes to TTS, and after the text part is fully accumulated it is sent as a `structured_response` via data channel. In text mode, TTS is skipped (as before) and the text part is sent via data channel. If no text part exists, voice mode behaves as before (full response to TTS).

## Risks / Trade-offs

**[LLM may not consistently follow the delimiter format]** → Fallback: treat the entire response as voice-only. The `dual_layer_prompt` update with explicit examples and delimiter tokens will maximize compliance. Monitor and iterate on prompt wording.

**[Streaming latency for text part in voice mode]** → The text part is accumulated (not streamed token-by-token) because it needs parsing for chunk IDs. This is acceptable since the text part is supplementary — the voice response streams immediately.

**[Prompt token overhead]** → The updated `dual_layer_prompt` with format examples adds ~100-150 tokens. Negligible compared to RAG context injection (~500-1000 tokens).

**[Index mapping assumes stable chunk order]** → `format_rag_context` iterates `chunks` in list order, which is the search result order (by score DESC). The mapping `[N] → chunks[N-1].chunk_id` is deterministic within a single turn. No risk of reordering.
