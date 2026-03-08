## Why

The PWA currently shows a placeholder screen after authentication (S21). Users cannot interact with the AI agent — there is no way to start a LiveKit session, speak via microphone, send text messages, or see agent responses. This is the core user-facing interface that connects the frontend to the entire voice/text pipeline built in S05–S20.

## What Changes

- Replace the `HomePage` placeholder with a full chat interface connected to LiveKit
- Add LiveKit Client SDK integration: room connection, audio track management, data channel messaging
- Implement microphone control UI (mute/unmute, audio level visualization)
- Implement a unified chat feed displaying voice transcripts and text messages from both user and agent
- Add a text input field for sending messages via data channel (`chat_message` type)
- Display agent state indicator (connecting, listening, thinking, speaking)
- Show interim voice transcripts in real time (from `transcript` data channel messages)
- Handle incoming `chat_response` and `structured_response` data channel messages
- Support switching between voice and text modes within the same session
- Call `POST /sessions/start` to create a session and obtain a LiveKit token before connecting

## Capabilities

### New Capabilities
- `livekit-room-connection`: LiveKit room lifecycle — connecting with token from `/sessions/start`, handling room events (connected, disconnected, reconnecting), cleanup on unmount
- `chat-feed`: Unified message list rendering voice transcripts, text messages, agent responses (plain and structured), interim transcripts, and agent state indicators
- `voice-controls`: Microphone toggle, audio level visualization, agent speaking indicator
- `text-input`: Text message composition and sending via LiveKit data channel (`chat_message` format)
- `data-channel-client`: Client-side data channel message handling — sending `chat_message`, receiving `chat_response`, `structured_response`, `transcript` types

### Modified Capabilities
- `pwa-routing`: The `/` route changes from a placeholder to the chat page component

## Impact

- **New dependencies:** `livekit-client`, `@livekit/components-react` added to `apps/web/package.json`
- **Modified files:** `HomePage.tsx` replaced with chat interface, `router.tsx` may gain session-related routes
- **API integration:** New call to `POST /sessions/start` via `apiFetch` + TanStack Query
- **LiveKit Server:** Client connects to rooms — requires `LIVEKIT_URL` available to the frontend (via Caddy proxy or env)
- **Data channel contract:** Client must match the agent's expected message formats (`chat_message`, `chat_response`, `structured_response`, `transcript`)
