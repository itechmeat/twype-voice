## 1. Dual-layer parser module

- [x] 1.1 Create `apps/agent/src/dual_layer_parser.py` with `DualLayerResult` and `TextItem` dataclasses
- [x] 1.2 Implement streaming parser that splits LLM output by `---VOICE---` / `---TEXT---` delimiters, yielding voice tokens immediately
- [x] 1.3 Implement text part parser: split into bullet items, extract `[N]` references, map to chunk UUIDs via ordered RagChunk list
- [x] 1.4 Handle edge cases: no delimiters (fallback to voice-only), empty voice part, delimiter mid-token, out-of-range references
- [x] 1.5 Write unit tests for parser: both parts present, no delimiters, empty parts, reference extraction, out-of-range indices

## 2. Agent RAG chunk storage

- [x] 2.1 Add `_last_rag_chunks: list[RagChunk]` attribute to `TwypeAgent`, reset to `[]` before each LLM turn
- [x] 2.2 Store RAG chunks in `_inject_rag_context` after successful search (before formatting)
- [x] 2.3 Include chunk index numbers in `format_rag_context` output (e.g., `[1] Source: ...`) so the LLM can reference them

## 3. Dual-layer routing in agent pipeline

- [x] 3.1 Modify `TwypeAgent.tts_node` in voice mode: wrap LLM output stream through the dual-layer parser, forward only voice part tokens to `super().tts_node()`
- [x] 3.2 After text part is parsed in voice mode, send `structured_response` via data channel
- [x] 3.3 Modify `TwypeAgent.tts_node` in text mode: run LLM output through the dual-layer parser, send text part as `structured_response` if present, fall back to `chat_response` if no text part
- [x] 3.4 Store `DualLayerResult` on agent instance for persistence access

## 4. Data channel protocol extension

- [x] 4.1 Add `publish_structured_response` function to `datachannel.py` with `items` (list of dicts with `text` and `chunk_ids`), `is_final`, optional `message_id`
- [x] 4.2 Add `"structured_response"` to the ignored types list in `receive_chat_message`
- [x] 4.3 Write unit tests for `publish_structured_response` payload format and reliable/unreliable delivery

## 5. Response persistence with source IDs

- [x] 5.1 Update `save_agent_response` in `transcript.py` to accept optional `source_ids: list[str] | None` parameter
- [x] 5.2 Update response persistence handler in `main.py` to read `all_chunk_ids` from stored `DualLayerResult` and pass as `source_ids`
- [x] 5.3 Write test verifying `source_ids` is persisted as JSONB array of UUID strings

## 6. Prompt update

- [x] 6.1 Update `dual_layer_prompt` in `scripts/seed.py` with delimiter format instructions, `[N]` reference notation, and a concrete example
- [x] 6.2 Run seed script against dev database to apply updated prompt

## 7. Integration verification

- [ ] 7.1 Manual end-to-end test: voice mode produces audio from voice part AND structured text via data channel
- [ ] 7.2 Manual end-to-end test: text mode sends structured_response via data channel without TTS
- [ ] 7.3 Manual end-to-end test: response without RAG context falls back gracefully (no delimiters, full response to TTS)
- [ ] 7.4 Verify `source_ids` populated in `messages` table after a RAG-backed response
