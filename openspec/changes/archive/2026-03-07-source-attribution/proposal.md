## Why

The dual-layer response system (S15) already extracts RAG chunk IDs and sends them to the client via data channel. The agent persists `source_ids` on message records. However, chunk IDs alone are opaque — the client has no way to resolve them into human-readable source metadata (title, author, section, page range, URL, source type). Without a dedicated API endpoint, the client cannot render source attribution UI: indicator icons, popup details, or direct links to original materials. This is the final backend piece needed before the PWA can display source attribution (S23).

## What Changes

- New FastAPI endpoint `GET /sources` that accepts a list of chunk UUIDs and returns full source metadata by joining `knowledge_chunks` with `knowledge_sources`
- Modify the session messages endpoint to include `source_ids` in its response schema, so the client can collect chunk IDs from message history and resolve them via the sources endpoint

## Capabilities

### New Capabilities
- `source-attribution-endpoint`: FastAPI endpoint that resolves chunk UUIDs to full source metadata (source_type, title, author, section, page_range, url) by joining knowledge_chunks and knowledge_sources tables

### Modified Capabilities
- `session-endpoints`: The `GET /sessions/{id}/messages` response schema SHALL include `source_ids` (list of UUID strings or null) from the messages table, so the client can use them to fetch source attribution

## Impact

- **API code**: New router/endpoint in `apps/api/`, new Pydantic response schemas
- **Existing endpoint**: `GET /sessions/{id}/messages` response schema gains `source_ids` field
- **Database**: No schema changes — `messages.source_ids` and `knowledge_chunks`/`knowledge_sources` tables already exist
- **Dependencies**: No new dependencies
- **Agent**: No changes — agent already persists `source_ids` via S15
