## Context

The agent currently runs a VAD-only pipeline: Silero VAD detects speech segments but the audio is not transcribed. The `AgentSession` is configured with `vad` and `turn_detection="vad"` but has no `stt` component. The `messages` table already has `content`, `voice_transcript`, `sentiment_raw` columns ready for STT data. The architecture specifies Deepgram as the STT provider, connected via WebSocket streaming.

LiveKit Agents SDK (>=1.4.4) supports pluggable STT via `AgentSession(stt=...)`. The `livekit-plugins-deepgram` plugin provides a `DeepgramSTT` class that handles streaming recognition, interim results, and final transcripts out of the box.

## Goals / Non-Goals

**Goals:**
- Integrate Deepgram STT into the agent pipeline with streaming interim + final transcripts
- Support Russian and English language recognition
- Extract sentiment score from Deepgram and persist it with the transcript
- Save final user transcripts to the `messages` table
- Deliver interim transcripts to the client via data channel for real-time display

**Non-Goals:**
- Turn Detector integration (S09)
- LLM or TTS pipeline stages (S07, S08)
- Multi-language auto-detection (manual `STT_LANGUAGE` config for now)
- Custom Deepgram model training
- Data channel protocol design for text chat (S11)

## Decisions

### D1: Use `livekit-plugins-deepgram` directly

**Decision:** Use the official LiveKit Deepgram plugin rather than a custom WebSocket integration.

**Rationale:** The plugin handles connection lifecycle, reconnection, audio format negotiation, and streaming results. It integrates natively with `AgentSession(stt=...)`. Building a custom client would duplicate proven logic and risk compatibility issues with future SDK updates.

**Alternatives considered:**
- Direct Deepgram SDK (`deepgram-sdk`): more control but requires manual audio piping from LiveKit, no `AgentSession` integration.
- Google Cloud STT: supported by LiveKit plugins but not the golden profile provider; Deepgram has lower latency for streaming.

### D2: Deepgram model and language configuration

**Decision:** Use Deepgram's `nova-3` model (latest general-purpose) with explicit language setting via `STT_LANGUAGE` env var (default: `multi` for auto-detect). Model configurable via `STT_MODEL` env var.

**Rationale:** `nova-3` supports both Russian and English with good accuracy. Explicit language config avoids auto-detection latency for known single-language sessions while `multi` allows flexibility.

**Alternatives considered:**
- Hardcoded `ru` language: too restrictive, English users would get poor results.
- Per-session language selection via API: good UX but adds complexity to the session start flow; deferred to a future story.

### D3: Sentiment extraction from Deepgram

**Decision:** Enable Deepgram's `sentiment` feature in the STT config. Extract the sentiment score from the final transcript result and map it to `sentiment_raw` (-1..1) on the message record.

**Rationale:** Deepgram provides sentence-level sentiment as part of its response at no additional latency cost. This is the "fast signal" referenced in the architecture for the Circumplex emotional model (S17). Storing it now prepares the data pipeline.

**Note:** Deepgram sentiment is available on final results only, not interim. The `sentiment_raw` field stores the average sentiment across all sentences in the utterance.

### D4: Transcript persistence — agent writes directly to DB

**Decision:** The agent process writes message records directly to PostgreSQL using the shared SQLAlchemy models from `twype-api`.

**Rationale:** The agent already depends on `twype-api` (see `pyproject.toml`). Direct DB writes avoid the latency and complexity of an HTTP round-trip through the API service. The `messages` table schema is stable and shared.

**Alternatives considered:**
- HTTP call to FastAPI `POST /messages`: adds latency on the voice pipeline critical path, requires auth token management in the agent.
- Message queue (Redis/RabbitMQ): over-engineered for a single-VPS deployment with direct DB access.

### D5: Interim transcripts via LiveKit data channel

**Decision:** Publish interim transcripts to the room via LiveKit's `room.local_participant.publish_data()` as JSON messages with a `type: "transcript"` envelope. Use `reliable=false` (lossy) for interim, `reliable=true` for final transcripts.

**Rationale:** Data channel is already part of the LiveKit room — no additional infrastructure needed. Lossy delivery for interim results is acceptable since they are replaced by the final transcript. This matches the architecture diagram (Data Channel Handler in agent).

**Message format:**
```json
{
  "type": "transcript",
  "is_final": false,
  "text": "Расскажи мне о...",
  "language": "ru"
}
```
Final transcript adds `message_id` and `sentiment_raw`.

### D6: Agent settings extension

**Decision:** Add `DEEPGRAM_API_KEY` (required), `STT_LANGUAGE` (default: `multi`), and `STT_MODEL` (default: `nova-3`) to `AgentSettings`. Keep the flat pydantic-settings pattern already established.

**Rationale:** Consistent with existing VAD settings pattern. Environment-based config aligns with the Docker deployment model. `DEEPGRAM_API_KEY` is injected from `.env`, never hardcoded.

## Risks / Trade-offs

- **[Deepgram API availability]** → Deepgram is a cloud service; network issues or API outages will break STT. Mitigation: the agent logs the error and continues running (VAD still works). No fallback STT provider in this story — S09 will address pipeline resilience.

- **[Sentiment accuracy for Russian]** → Deepgram's sentiment model is primarily trained on English. Russian sentiment scores may be less reliable. Mitigation: `sentiment_raw` is a "fast signal" input to the Circumplex model (S17), not the sole source of emotional state. LLM-based interpretation provides the main analysis.

- **[DB write latency on agent process]** → Writing to PostgreSQL from the agent adds I/O to the voice pipeline. Mitigation: the DB write happens after the final transcript is received (not on the critical audio path). The write is fire-and-forget with error logging — it does not block the next pipeline stage.

- **[Data channel message ordering]** → Lossy delivery for interim transcripts means some may arrive out of order or be dropped. Mitigation: each interim message contains the full current text (not a diff), so the client always displays the latest received text regardless of ordering.
