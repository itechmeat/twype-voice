## 1. API Client Layer

- [x] 1.1 Create `apps/web/src/lib/api-sources.ts` with `resolveSources(chunkIds)` function (POST /api/sources/resolve, short-circuit on empty array, response type + transformer)
- [x] 1.2 Create `apps/web/src/lib/api-sessions.ts` with `getSessionHistory(offset, limit)` and `getSessionMessages(sessionId)` functions (GET endpoints, response types + transformers)
- [x] 1.3 Create `apps/web/src/hooks/use-resolve-sources.ts` — TanStack Query hook with `enabled: false`, manual `refetch()`, cache key by sorted chunk_ids, `staleTime: 5min`
- [x] 1.4 Create `apps/web/src/hooks/use-session-history.ts` — TanStack Query hook for session list with pagination params (offset, limit)
- [x] 1.5 Create `apps/web/src/hooks/use-session-messages.ts` — TanStack Query hook for session messages by sessionId

## 2. Source Attribution UI

- [x] 2.1 Create `apps/web/src/components/SourceIndicator.tsx` — clickable icon component that accepts `chunkIds`, renders generic citation icon pre-resolution, manages popover open state
- [x] 2.2 Create `apps/web/src/components/SourcePopover.tsx` — popover displaying resolved source metadata (title, type, author, section, page_range, URL link), loading and error states with retry, dismiss on outside click / Escape / close button
- [x] 2.3 Update `apps/web/src/components/ChatMessage.tsx` — replace static "Source ready" badge with `<SourceIndicator>` for each structured item with non-empty `chunk_ids`

## 3. Session History UI

- [x] 3.1 Create `apps/web/src/pages/HistoryPage.tsx` — session list in reverse chronological order, "load more" pagination, empty/loading/error states
- [x] 3.2 Create message transformer utility in `apps/web/src/lib/message-transformer.ts` — converts API `MessageItem` to `ChatMessageEntry` union (parse structured JSON content, fallback to plain text)
- [x] 3.3 Create `apps/web/src/pages/SessionDetailPage.tsx` — read-only dialogue replay using `ChatMessage`, back navigation to history, source indicators on historical messages with `source_ids`, loading/error/empty states
- [x] 3.4 Update `apps/web/src/router.tsx` — add `/history` and `/history/:sessionId` routes under `ProtectedLayout`
- [x] 3.5 Add navigation link to `/history` in `ProtectedLayout` or shared header

## 4. Tests

- [x] 4.1 Tests for `resolveSources`, `getSessionHistory`, `getSessionMessages` API client functions
- [x] 4.2 Tests for message transformer (plain text, structured JSON, malformed content fallback)
- [x] 4.3 Tests for `SourceIndicator` and `SourcePopover` components (render, click, dismiss, loading, error)
- [x] 4.4 Tests for `HistoryPage` and `SessionDetailPage` (render states, navigation, pagination)
