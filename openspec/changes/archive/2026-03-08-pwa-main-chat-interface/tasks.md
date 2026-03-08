## 1. Dependencies and Configuration

- [x] 1.1 Add `livekit-client` and `@livekit/components-react` to `apps/web/package.json`
- [x] 1.2 Add Vite proxy rule for `/livekit-signaling/` to `vite.config.ts` (proxy to Caddy/LiveKit)
- [x] 1.3 Create LiveKit URL helper (`apps/web/src/lib/livekit-url.ts`) — resolves URL from `VITE_LIVEKIT_URL` env or constructs from `window.location`

## 2. Data Channel Hooks

- [x] 2.1 Create `useDataChannel` hook (`apps/web/src/hooks/use-data-channel.ts`) — subscribes to `RoomEvent.DataReceived`, parses JSON, dispatches by `type`, ignores own/malformed messages
- [x] 2.2 Create `useSendDataChannel` hook (`apps/web/src/hooks/use-send-data-channel.ts`) — provides `send(type, payload)` with reliable delivery, warns on disconnected state

## 3. Session and Room Connection

- [x] 3.1 Create `useStartSession` hook (`apps/web/src/hooks/use-start-session.ts`) — TanStack Query mutation calling `POST /sessions/start`, returns `sessionId`, `roomName`, `livekitToken`
- [x] 3.2 Create `ChatPage` component (`apps/web/src/pages/ChatPage.tsx`) — calls `useStartSession` on mount, renders `LiveKitRoom` with token/URL, includes `RoomAudioRenderer`, shows connection state (connecting/connected/reconnecting/disconnected)

## 4. Chat Message State

- [x] 4.1 Create chat message types and reducer (`apps/web/src/lib/chat-state.ts`) — message types (user-voice, user-text, agent-plain, agent-structured), reducer actions (add message, update interim, clear interim)
- [x] 4.2 Wire data channel handlers into chat reducer — handle `chat_response`, `structured_response`, `transcript`, `emotional_state` message types

## 5. Chat Feed UI

- [x] 5.1 Create `ChatFeed` component (`apps/web/src/components/ChatFeed.tsx`) — scrollable message list, auto-scroll with scroll-up detection, new-messages indicator
- [x] 5.2 Create `ChatMessage` component (`apps/web/src/components/ChatMessage.tsx`) — renders user/agent messages with mode label (voice/text), structured response items with source indicator placeholder
- [x] 5.3 Create `InterimTranscript` component (`apps/web/src/components/InterimTranscript.tsx`) — displays interim STT text in distinguished style
- [x] 5.4 Create `AgentStateIndicator` component (`apps/web/src/components/AgentStateIndicator.tsx`) — shows listening/thinking/speaking state from agent participant attributes

## 6. Voice Controls

- [x] 6.1 Create `MicToggle` component (`apps/web/src/components/MicToggle.tsx`) — toggle button using `useLocalParticipant` to mute/unmute audio track, visual state reflection
- [x] 6.2 Create `AudioLevelIndicator` component (`apps/web/src/components/AudioLevelIndicator.tsx`) — real-time volume visualization for local mic and agent audio tracks

## 7. Text Input

- [x] 7.1 Create `TextInput` component (`apps/web/src/components/TextInput.tsx`) — multi-line input, Enter to send, Shift+Enter for newline, send button, empty message prevention, disabled when disconnected
- [x] 7.2 Wire text input to data channel — sends `chat_message` via `useSendDataChannel`, adds optimistic user message to chat reducer

## 8. Routing Update

- [x] 8.1 Update `router.tsx` — replace `HomePage` import with `ChatPage` at `/` route
- [x] 8.2 Update `ProtectedLayout` — adjust app shell header for chat context (remove placeholder text)

## 9. Tests

- [x] 9.1 Unit tests for `chat-state.ts` reducer — all action types, message ordering
- [x] 9.2 Unit tests for `livekit-url.ts` — env var override, URL construction from location
- [x] 9.3 Component tests for `TextInput` — Enter/Shift+Enter behavior, empty message prevention, disabled state
- [x] 9.4 Component tests for `ChatFeed` — message rendering, auto-scroll behavior
