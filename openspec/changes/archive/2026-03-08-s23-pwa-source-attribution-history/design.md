# S23 — PWA Source Attribution & History: Design

## Context

The RAG pipeline (S14-S16) produces structured responses where each bullet point carries `chunk_ids` linking back to ingested source material. The API already serves source metadata via `POST /api/sources/resolve` and session history via `GET /api/sessions/history` and `GET /api/sessions/{id}/messages`. However, the PWA has no interactive UI for any of this. `ChatMessage` renders a static `"Source ready"` badge when `chunk_ids.length > 0` — users cannot inspect sources or review past conversations.

This is a frontend-only change. No new backend work is required.

### Existing patterns observed

- **Data fetching:** TanStack Query with `useMutation` (see `use-start-session.ts`). The project uses a shared `QueryClient` from `lib/query-client.ts` with `retry: false`.
- **API calls:** `apiFetch<T>` from `lib/api-client.ts` handles auth, refresh tokens, and JSON serialization. All API methods follow the pattern of a raw response type guard + camelCase transformer.
- **State management:** Chat state uses `useReducer` with a discriminated union action type (`chat-state.ts`). No global store — state is local to `ChatPage`.
- **Routing:** `react-router` with `ProtectedLayout` / `PublicLayout` wrappers. All authenticated routes nest under `ProtectedLayout`.
- **Component structure:** Flat component files under `src/components/`, page components under `src/pages/`, hooks under `src/hooks/`.

## Goals / Non-Goals

### Goals

- Replace the static source badge with clickable source indicators that show full metadata (title, author, section, page range, URL) on demand
- Add a session history page listing past sessions
- Add a session detail view that replays past dialogue as read-only chat messages
- Add API client methods and TanStack Query hooks for the three consumed endpoints

### Non-Goals

- Modifying any backend endpoint or schema
- Source metadata editing or feedback mechanisms
- Offline caching of session history or sources
- Search/filter within session history (can be added later without breaking anything)
- Real-time updates to the history list while a session is active

## Decisions

### 1. Source detail UI: popover, not drawer or modal

**Choice:** Render source metadata in a positioned popover anchored to the source indicator icon.

**Rationale:**
- A drawer or full modal is heavyweight for showing 3-6 fields (type, title, author, section, page range, URL). A popover keeps context — the user can see the bullet point that generated the source while reading the metadata.
- The popover dismisses on outside click or Escape, matching standard UI conventions without requiring a routing change or overlay backdrop.
- Mobile: the popover can expand to near-full-width at small viewports. No separate mobile treatment needed at MVP.

**Component:** `SourcePopover` — receives `chunk_ids: string[]`, fetches on open, renders metadata list. Manages its own open/closed state.

### 2. Source data fetching: fetch-on-click with TanStack Query cache

**Choice:** Call `POST /api/sources/resolve` when the user clicks a source indicator, not when the message renders.

**Rationale:**
- Most users will not click every source indicator. Eager fetching would create unnecessary API load proportional to message count rather than user intent.
- TanStack Query caching keyed by sorted `chunk_ids` ensures repeat clicks on the same source indicator are instant. The same chunk appearing in multiple bullets shares cache entries at the individual-source level if we normalize, but for simplicity the cache key should be the full `chunk_ids` array (sorted and joined). The resolve endpoint is idempotent — repeated calls are harmless.
- `staleTime` should be generous (5-10 minutes) since source metadata is effectively immutable within a session.

**Hook:** `useResolveSources` — wraps `useQuery` (not `useMutation`) with `enabled: false`, triggered manually via `refetch()` on popover open. This gives us caching for free while keeping the fetch lazy.

### 3. Source indicator: icon per source type, replacing the badge

**Choice:** Replace the `"Source ready"` `<span>` with a row of small icons (one per resolved source type: book, video, podcast, article, post) rendered inline after the bullet text.

**Nuance:** The source types are only known after resolution. Before the user clicks, we know `chunk_ids.length > 0` but not the types. The pre-click state should render a single generic "has sources" indicator (e.g., a small citation icon or footnote marker). After the popover loads and caches, the indicator can optionally enrich to show type-specific icons — but this is a polish item, not a structural requirement. The MVP indicator is: clickable icon when `chunk_ids.length > 0`.

**Component change:** `ChatMessage.renderMessageBody` replaces the `<span className="chat-message__source-badge">` with `<SourceIndicator chunkIds={item.chunk_ids} />`, which internally manages the popover.

### 4. Session history: two new routes, two new pages

**Choice:**
- `/history` — `HistoryPage` — paginated list of past sessions
- `/history/:sessionId` — `SessionDetailPage` — read-only message replay

Both routes nest under `ProtectedLayout`.

**Rationale:**
- Separate routes (not tabs or modals on ChatPage) because history browsing and live chat are distinct user intents. Users navigating history should not maintain a LiveKit connection.
- The session detail page reuses `ChatMessage` for rendering individual messages, but wraps them in a read-only container (no `TextInput`, no `InterimTranscript`, no streaming state). This maximizes component reuse without coupling history rendering to live chat state.

### 5. Session history data fetching

**Choice:** `useQuery` for both the session list and session messages.

- `useSessionHistory` — calls `GET /api/sessions/history`, query key `["sessions", "history"]`. Supports pagination params (`offset`, `limit`) passed as query key components.
- `useSessionMessages` — calls `GET /api/sessions/{id}/messages`, query key `["sessions", sessionId, "messages"]`. Fetched when `sessionId` route param is present.

**Rationale:** These are standard read queries — `useQuery` with automatic caching is the right fit. The session list can use a short `staleTime` (30s) since new sessions appear after the user returns from chat. Session messages are immutable once the session ends, so `staleTime: Infinity` is appropriate for completed sessions (and short for active ones, though viewing active session history is a non-goal).

### 6. API client layer: typed fetch functions in api-client or a dedicated module

**Choice:** Add three new exported functions to a new `lib/api-sources.ts` and `lib/api-sessions.ts` module (or co-locate in `api-client.ts` if the team prefers minimal files). Each function follows the existing pattern: raw response type guard, camelCase transformer, `apiFetch` call.

Functions:
- `resolveSources(chunkIds: string[])` — `POST /api/sources/resolve`
- `fetchSessionHistory(offset: number, limit: number)` — `GET /api/sessions/history`
- `fetchSessionMessages(sessionId: string)` — `GET /api/sessions/{id}/messages`

**Rationale:** Matches the `use-start-session.ts` pattern of raw type guard + transformer. Splitting into domain-specific modules prevents `api-client.ts` from becoming a catch-all, while keeping the core `apiFetch` utility focused on HTTP mechanics.

### 7. Message rendering reuse for history

**Choice:** `ChatMessage` remains the single renderer for both live and historical messages. The `MessageItem` schema from the API (`role`, `mode`, `content`, `source_ids`, `created_at`) maps to `ChatMessageEntry` via a transformer function.

**Mapping:**
- `role: "user"` + `mode: "voice"` -> `UserVoiceMessage`
- `role: "user"` + `mode: "text"` -> `UserTextMessage` (with `deliveryStatus: "sent"`)
- `role: "assistant"` -> attempt to parse `content` as structured JSON; if it has `items` with `chunk_ids`, map to `AgentStructuredMessage`; otherwise `AgentPlainMessage`

This transformer lives alongside the session API functions. `ChatMessage` requires no changes beyond the source indicator swap.

### 8. Navigation

**Choice:** Add a navigation link to `/history` in the `ProtectedLayout` or a shared header/nav component. The history page has a "back to chat" link. Session detail has a "back to history" link.

No complex navigation state needed — React Router handles this natively.

## Risks / Trade-offs

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Popover positioning on mobile.** CSS-only popovers can overflow viewport on small screens. | Medium | Use CSS anchor positioning or a lightweight positioning utility. Test on 320px viewport. If problematic, fall back to a bottom sheet on mobile — but defer until testing confirms the issue. |
| **Large chunk_ids arrays.** A bullet could theoretically reference many chunks, making the POST body large and the popover crowded. | Low | The API schema caps `chunk_ids` at 50. The popover should scroll if more than ~5 sources resolve. No truncation needed at the API layer. |
| **History message format ambiguity.** The `content` field from `MessageItem` may be plain text or JSON-encoded structured response. The transformer must handle both without false positives. | Medium | Use strict JSON parse with schema validation — only treat as structured if the parsed object has an `items` array where every item has `text` and `chunk_ids`. Fall back to plain text on any parse failure. |
| **No pagination UI pattern exists yet.** The history list is the first paginated view in the app. | Low | Start with "load more" button (append next page). Simpler than offset-based page navigation and works well on mobile. Can evolve to infinite scroll later — the query key structure supports it. |
| **Source indicator click area on touch devices.** Small icons next to bullet text may be hard to tap. | Low | Ensure minimum 44x44px touch target on the clickable area via padding, even if the visible icon is smaller. |
