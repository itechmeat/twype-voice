## Context

The PWA frontend (S21) has authentication screens and a placeholder `HomePage`. The backend agent (S05–S20) is fully functional: voice pipeline, text chat via data channel, dual-layer responses, emotional adaptation, and mode switching. The missing piece is the client-side chat interface that connects the user to the agent via LiveKit.

The client connects to LiveKit in two ways:
- **WebRTC** (via LiveKit Client SDK) — audio tracks for voice mode, data channels for text/structured messages
- **REST** (via `apiFetch`) — `POST /sessions/start` to get a LiveKit token, session history later in S23

The agent sends several data channel message types: `chat_response`, `structured_response`, `transcript`, `emotional_state`. The client sends `chat_message`.

LiveKit signaling is proxied through Caddy at `/livekit-signaling/`. Media goes directly via UDP.

## Goals / Non-Goals

**Goals:**
- Replace the `HomePage` placeholder with a working chat interface
- Connect to LiveKit rooms using tokens from `POST /sessions/start`
- Support both voice (microphone) and text (input field) interaction
- Display a unified message feed with agent responses and user messages
- Show real-time interim transcripts from the agent's STT
- Display agent state (connecting, listening, thinking, speaking)
- Handle incoming `chat_response`, `structured_response`, `transcript` message types
- Audio visualization for microphone input

**Non-Goals:**
- Source attribution UI (bullet point icons, popups) — deferred to S23
- Session history and past dialogue viewing — deferred to S23
- PWA features (service worker, manifest, offline) — deferred to S24
- Styling polish or design system — minimal functional CSS only
- Emotional state visualization — data received but not rendered in S22
- Mobile-specific layout optimizations — deferred to S24

## Decisions

### D1: Use `@livekit/components-react` for room connection and audio

**Decision:** Use LiveKit's React component library for room lifecycle, audio rendering, and participant state.

**Rationale:** The library provides `LiveKitRoom`, `useRoomContext`, `useParticipants`, `useLocalParticipant`, `useConnectionState`, and audio rendering out of the box. Building this from scratch with `livekit-client` alone would duplicate significant state management.

**Alternative considered:** Raw `livekit-client` SDK only — rejected because it requires manual React state synchronization for room events, participant changes, and track subscriptions.

### D2: LiveKit URL from Caddy proxy path

**Decision:** The client connects to LiveKit signaling via the same origin using the `/livekit-signaling/` path proxied by Caddy. The WebSocket URL is constructed as `ws(s)://<host>/livekit-signaling/`.

**Rationale:** Avoids exposing a separate LiveKit port or domain. Caddy already proxies this path to `livekit:7880`. In development, Vite proxy handles it alongside `/api`.

**Alternative considered:** Environment variable with full LiveKit URL — rejected because it introduces an additional config value and complicates the Caddy-based deployment.

### D3: Data channel message handling via custom hook

**Decision:** Create a `useDataChannel` hook that subscribes to the room's data received events, parses JSON messages, and dispatches them by `type` field to registered handlers.

**Rationale:** The agent sends 4+ message types (`chat_response`, `structured_response`, `transcript`, `emotional_state`). A centralized dispatcher keeps message parsing in one place and lets individual UI components subscribe to specific types.

**Alternative considered:** Using `@livekit/components-react`'s built-in `useDataChannel` — may not support the custom JSON protocol; our hook gives full control over message parsing and type dispatch.

### D4: Session lifecycle — start on page mount, single session per visit

**Decision:** When the chat page mounts, the app calls `POST /sessions/start` via TanStack Query mutation, receives a token + room name, and connects to LiveKit. One session per page visit. Refresh or logout ends the session.

**Rationale:** Simplest UX for MVP — user logs in, immediately enters a conversation. No session picker or "start new chat" button needed.

**Alternative considered:** Explicit "Start session" button — rejected for MVP; adds a step without value when there's a single agent.

### D5: Message state management — local React state, not TanStack Query cache

**Decision:** Chat messages (from data channel) are managed in a `useReducer` within the chat page component tree. Not stored in TanStack Query cache.

**Rationale:** Messages arrive via WebRTC data channel (push), not HTTP (pull). TanStack Query is designed for server-state caching. A reducer handles the append-only, event-driven nature of chat messages cleanly.

**Alternative considered:** TanStack Query cache with manual updates — over-engineered for real-time push data.

### D6: Agent state derived from LiveKit participant metadata and track events

**Decision:** Agent state (listening, thinking, speaking) is derived from the agent participant's published tracks and metadata. The `@livekit/components-react` hooks provide participant state changes reactively.

**Rationale:** LiveKit Agents SDK publishes agent state via participant attributes. The client can read these without custom data channel messages.

## Risks / Trade-offs

- **[LiveKit signaling via Caddy path]** If the WebSocket upgrade fails through the proxy path, the room connection will not establish. Mitigation: verify Caddy WebSocket proxy works; fall back to `VITE_LIVEKIT_URL` env var if needed.
- **[No reconnection UI]** If the WebRTC connection drops mid-session, the user has no explicit reconnect button. Mitigation: `LiveKitRoom` component handles automatic reconnection; show a "reconnecting" state indicator.
- **[Data channel reliability]** Interim transcripts use unreliable delivery for low latency; some may be dropped. Mitigation: acceptable for interim transcripts; final messages use reliable delivery.
- **[Single session per visit]** User cannot start a new session without refreshing. Mitigation: acceptable for MVP; S23 adds session management.
