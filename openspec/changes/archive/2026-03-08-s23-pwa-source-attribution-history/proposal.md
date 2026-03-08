## Why

The agent already generates structured responses with source references (`chunk_ids`) and the API serves source metadata and session history, but the PWA has no interactive UI to display this information. Users cannot inspect where answers come from, review past conversations, or verify the credibility of agent responses — defeating the purpose of the RAG source attribution pipeline built in S14–S16.

## What Changes

- Replace the static "Source ready" badge in `ChatMessage` with clickable source indicator icons (book, video, podcast, article, post) rendered next to each structured bullet point
- Add a source detail popup/drawer that fetches and displays full metadata (title, author, section, page range, URL) from `POST /sources/resolve` on click
- Add a session history page listing past sessions with timestamps and status, fetched from `GET /sessions/history`
- Add a session detail view that replays past dialogue messages fetched from `GET /sessions/{id}/messages`
- Add API client methods for sources resolution and session history endpoints
- Add routing for the new history pages

## Capabilities

### New Capabilities
- `source-attribution-ui`: Interactive source indicators on structured response bullets with popup/drawer showing full source metadata
- `session-history-ui`: Session history list page and past dialogue viewer with message rendering

### Modified Capabilities
- `chat-feed`: Add source indicator icons inline with structured message items (currently shows a static badge)

## Impact

- **Frontend only** — no backend changes required; all API endpoints are already implemented and tested
- **Affected code:** `apps/web/src/components/` (ChatMessage, new SourcePopup, new history components), `apps/web/src/pages/` (new HistoryPage, SessionDetailPage), `apps/web/src/lib/api-client.ts` (new methods), `apps/web/src/router.tsx` (new routes)
- **Dependencies:** none new — uses existing LiveKit client SDK, TanStack Query, and React Router
- **APIs consumed:** `POST /api/sources/resolve`, `GET /api/sessions/history`, `GET /api/sessions/{id}/messages`
