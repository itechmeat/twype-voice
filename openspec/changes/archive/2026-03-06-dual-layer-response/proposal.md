## Why

The agent currently sends the same LLM output to both voice (TTS) and text (data channel) without structural separation. The `dual_layer_prompt` instructs the LLM to produce two formulations, but nothing parses, splits, or routes them to the correct channel. RAG chunk IDs are not attached to response points, blocking source attribution (S16). Dual-layer response is the bridge between RAG search (S14) and source attribution UI (S16).

## What Changes

- Define a structured LLM output format with explicit delimiters separating a voice part (2-5 sentences, conversational) from a text part (bullet points with `chunk_ids` arrays).
- Update the `dual_layer_prompt` seed to instruct the LLM to use the new structured format.
- Add a response parser that extracts voice and text parts from the LLM stream.
- In voice mode: send the voice part to TTS, send the text part via data channel simultaneously.
- In text mode: send only the text part via data channel (no TTS).
- Populate `source_ids` on the `Message` model with referenced RAG chunk IDs.
- Label response points not backed by knowledge base chunks as reasoning (no `chunk_ids`).
- Extend the data channel protocol with a new message type for structured text responses containing bullet points and their associated chunk IDs.

## Capabilities

### New Capabilities
- `dual-layer-parser`: Streaming parser that splits LLM output into voice and text parts, extracting chunk ID references from structured bullet points.
- `dual-layer-routing`: Routes parsed voice part to TTS and text part to data channel; handles both voice and text input modes.

### Modified Capabilities
- `prompt-builder`: Updated `dual_layer_prompt` with explicit formatting instructions and delimiter tokens for structured output.
- `text-chat-handler`: Extended data channel protocol to carry structured text responses with bullet points and chunk IDs arrays.
- `agent-response-persistence`: Populates `source_ids` JSONB field on the `Message` model with chunk UUIDs extracted from the text part.
- `database-seed`: Updated seed data for the new `dual_layer_prompt` content.

## Impact

- **Agent code** (`apps/agent/src/`): New parser module; changes to `agent.py` (`llm_node`, `tts_node`), `datachannel.py` (new message type), `transcript.py` (source_ids persistence).
- **Seed data** (`scripts/seed.py`): Updated `dual_layer_prompt` text.
- **Data channel protocol**: New `structured_response` message type — clients must handle it (future S22 work).
- **Database**: No schema changes — `source_ids` JSONB and `content` field already exist. The `content` field will store the full (unsplit) response for history; voice and text parts are transient routing concerns.
- **Dependencies**: No new packages required.
