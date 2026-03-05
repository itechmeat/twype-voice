## Why

The voice pipeline (VAD → STT → LLM → TTS) is complete, but the agent only handles audio input. Users need a text chat option via LiveKit data channel — for noisy environments, accessibility, or preference. The `messages` table already supports `mode = 'text'`, and the data channel infrastructure exists for outbound transcripts, but there is no inbound text message handling.

## What Changes

- Add a Data Channel Handler in the agent that listens for incoming text messages from the client via LiveKit data channel
- Route received text directly to the LLM, bypassing STT entirely
- Stream the LLM text response back to the client via data channel (no TTS invocation in text mode)
- Persist text messages to the `messages` table with `mode = 'text'`
- Define a JSON protocol for client → agent text messages (distinct from the existing `transcript` type used for agent → client)

## Capabilities

### New Capabilities

- `text-chat-handler`: Receiving, processing, and responding to text messages via LiveKit data channel — including the inbound message protocol, LLM routing without STT/TTS, streaming response delivery, and persistence with `mode = 'text'`

### Modified Capabilities

- `agent-transcript-persistence`: User and assistant messages are currently saved with hardcoded `mode="voice"`. Must support `mode` parameter to correctly persist text-mode messages.

## Impact

- **`apps/agent/src/`**: New data channel receive handler; modifications to `main.py` (event wiring), `datachannel.py` (inbound protocol + response publishing), `transcript.py` (mode parameter)
- **Data channel protocol**: New inbound message type `chat_message` (client → agent); new outbound message type `chat_response` for streaming text responses
- **No database schema changes**: `messages.mode` already supports `'text'`; no new tables or columns needed
- **No API changes**: existing `/sessions/{id}/messages` endpoint already returns all messages regardless of mode
