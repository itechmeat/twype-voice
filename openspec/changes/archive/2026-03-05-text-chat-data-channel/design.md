## Context

The agent currently operates in voice-only mode: audio arrives via WebRTC, passes through VAD → STT → LLM → TTS, and the synthesized audio is sent back. Outbound data channel is already used for publishing transcripts (`datachannel.py` with `publish_transcript`), but there is no listener for inbound data channel messages.

The `messages` table has `mode IN ('voice', 'text')` since S02, and both `save_transcript` and `save_agent_response` in `transcript.py` hardcode `mode="voice"`. The LiveKit room object exposes a `data_received` event for incoming data packets from participants.

## Goals / Non-Goals

**Goals:**

- Accept text messages from the client via LiveKit data channel and generate LLM responses
- Stream text responses back via data channel without invoking TTS
- Persist both user and assistant text messages with `mode='text'`
- Reuse the existing `AgentSession` LLM integration (chat context, conversation history)

**Non-Goals:**

- Mode switching logic (S12) — this story only handles pure text input
- Client-side UI (S22) — only the agent-side handler
- Dual-layer response format (S15) — text responses are plain text for now
- Typing indicators or read receipts

## Decisions

### 1. Inbound message protocol

**Decision:** Define a JSON envelope `{"type": "chat_message", "text": "..."}` sent by the client as a reliable data packet. The agent listens on the room's `data_received` event.

**Why:** Matches the existing outbound protocol pattern (`{"type": "transcript", ...}`). Using `type` field allows multiplexing different message types on the same data channel. Reliable delivery ensures no messages are lost.

**Alternatives considered:**
- Separate LiveKit data topics — adds complexity with no benefit at this stage
- Protobuf encoding — premature; JSON is already used for outbound, keeping consistency

### 2. LLM routing: inject into AgentSession chat context

**Decision:** Use `AgentSession.generate_reply(user_input=text)` to inject text into the existing conversation pipeline. This feeds the text directly to the LLM node, bypassing STT, and the session manages chat context automatically.

**Why:** `AgentSession` already maintains chat history and handles LLM streaming. Using `generate_reply` keeps text messages in the same conversation thread as voice messages, which is essential for S12 (mode switching). The session's `conversation_item_added` event fires for assistant responses, so existing persistence handlers in `main.py` will capture them automatically.

**Alternatives considered:**
- Direct LLM API call outside the session — breaks conversation continuity, duplicates context management
- Custom pipeline fork — unnecessary complexity when `generate_reply` exists

### 3. Outbound response streaming

**Decision:** Reuse the existing `conversation_item_added` event handler in `main.py` for persisting and publishing assistant responses. Add a new outbound message type `{"type": "chat_response", "text": "...", "is_final": bool}` for streaming chunks, separate from `transcript` type.

**Why:** The `conversation_item_added` handler already saves assistant messages and publishes them via data channel. For text mode, we need streaming chunks (interim text) before the final message, so a dedicated `chat_response` type lets the client distinguish voice transcripts from text chat responses. The final `conversation_item_added` event handles persistence as-is.

**Alternatives considered:**
- Reuse `transcript` type with a `mode` field — muddies the protocol; transcripts are STT artifacts, chat responses are direct LLM output
- Only send final response — poor UX, users expect to see streaming text

### 4. Suppressing TTS for text-mode responses

**Decision:** Track current input mode (voice vs text) per message. When `generate_reply` is triggered by a text input, set a flag. In the `TwypeAgent.tts_node` override, check this flag and return `None` to skip synthesis. Reset the flag after the response completes.

**Why:** The voice pipeline automatically routes LLM output to TTS. We need a clean way to suppress TTS without modifying the session internals. Overriding `tts_node` is the idiomatic LiveKit Agents approach (same pattern used for `llm_node` thinking sounds).

**Alternatives considered:**
- Separate AgentSession without TTS — two sessions add complexity and break shared context
- Post-hoc cancellation of TTS output — fragile, race conditions

### 5. Persistence mode parameter

**Decision:** Add an optional `mode` parameter (default `"voice"`) to `save_transcript` and `save_agent_response` in `transcript.py`. The data channel handler passes `mode="text"`.

**Why:** Minimal change. The column already exists with the check constraint. Default preserves backward compatibility with existing voice pipeline callers.

## Risks / Trade-offs

- **Concurrent voice + text input** — If a user sends text while also speaking, both will feed into the same LLM context. This is acceptable for S11; S12 will add proper mode arbitration. → Mitigation: messages are serialized through `generate_reply`, so no data corruption.

- **Streaming chunks for text responses** — `generate_reply` returns the final assembled response, not intermediate chunks. We may need to tap into the LLM stream to send interim chunks. → Mitigation: If `generate_reply` doesn't expose streaming, use the `agent_speech_committed` or similar event for the final text, accepting that streaming is deferred to S12.

- **No authentication on data channel messages** — Any room participant could send `chat_message` packets. → Mitigation: LiveKit rooms are already secured via tokens with specific permissions; only authenticated users can join.
