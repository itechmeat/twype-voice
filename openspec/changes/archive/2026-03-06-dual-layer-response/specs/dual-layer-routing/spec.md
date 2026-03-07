## ADDED Requirements

### Requirement: Route voice part to TTS in voice mode
In voice mode, the agent SHALL pass only the voice part (extracted by the dual-layer parser) to the TTS pipeline. The text part SHALL NOT be sent to TTS.

#### Scenario: Voice part sent to TTS
- **WHEN** the LLM produces a dual-layer response and the agent is in voice mode
- **THEN** only the voice part tokens SHALL be forwarded to `super().tts_node()`

#### Scenario: No voice part produced
- **WHEN** the LLM produces a response with an empty voice part (only text part)
- **THEN** no audio SHALL be synthesized and the TTS node SHALL return `None`

### Requirement: Send text part via data channel in voice mode
In voice mode, after the text part is fully parsed, the agent SHALL send a `structured_response` message via data channel containing the parsed bullet items and their chunk IDs.

#### Scenario: Structured response sent alongside voice
- **WHEN** the LLM produces a dual-layer response in voice mode
- **THEN** the voice part streams to TTS AND a `structured_response` data channel message is sent with the parsed text items

#### Scenario: No text part in voice mode
- **WHEN** the LLM produces a response without a text part (no delimiter) in voice mode
- **THEN** no `structured_response` message SHALL be sent via data channel; the response behaves as before (full text to TTS)

### Requirement: Send text part via data channel in text mode
In text mode, the agent SHALL send the text part as a `structured_response` via data channel. If no text part exists, the full response SHALL be sent as a plain `chat_response` (existing behavior).

#### Scenario: Text mode with dual-layer response
- **WHEN** the LLM produces a dual-layer response and the agent is in text mode
- **THEN** the text part SHALL be sent as a `structured_response` via data channel; no TTS invoked

#### Scenario: Text mode without text part
- **WHEN** the LLM produces a response without delimiters in text mode
- **THEN** the full response SHALL be sent as a `chat_response` via data channel (fallback to existing behavior)

### Requirement: Store RAG chunk list per turn for parser access
The agent SHALL store the list of `RagChunk` objects returned by the RAG engine on the agent instance after each `_inject_rag_context` call. The parser SHALL use this list to map `[N]` references to chunk UUIDs. The list SHALL be reset to empty before each new LLM turn.

#### Scenario: Chunks available to parser
- **WHEN** `_inject_rag_context` retrieves 4 chunks and the LLM produces a response with `[2]` references
- **THEN** the parser SHALL map `[2]` to `self._last_rag_chunks[1].chunk_id`

#### Scenario: No RAG context injected
- **WHEN** `_inject_rag_context` finds no relevant chunks
- **THEN** `self._last_rag_chunks` SHALL be an empty list and the parser SHALL treat all references as unresolvable
