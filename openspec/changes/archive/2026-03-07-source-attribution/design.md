## Context

The dual-layer response system (S15) produces structured text items with `chunk_ids` — references to `knowledge_chunks` rows. The agent persists these IDs in `messages.source_ids` (JSONB). The client receives `chunk_ids` via data channel in real-time and can retrieve them from message history. However, there is no API to resolve chunk UUIDs into human-readable source metadata.

Current state:
- `knowledge_chunks` table holds chunk-level data: `id`, `source_id`, `section`, `page_range`
- `knowledge_sources` table holds source-level data: `source_type`, `title`, `author`, `url`, `language`, `tags`
- `messages.source_ids` stores JSONB array of chunk UUID strings
- `MessageItem` schema does not expose `source_ids`
- No `/sources` router exists

## Goals / Non-Goals

**Goals:**
- Provide an authenticated API endpoint to resolve chunk UUIDs into full source metadata
- Expose `source_ids` in the session messages endpoint response
- Follow existing API patterns (router module, Pydantic schemas, async SQLAlchemy)

**Non-Goals:**
- Client-side rendering of source attribution (deferred to S23 PWA story)
- Caching or precomputing source metadata
- Pagination within source results (chunk_ids lists are small, typically 3-10)

## Decisions

### D1: `POST /sources/resolve` with JSON body instead of `GET /sources/{chunk_ids}`

The plan mentions `GET /sources/{chunk_ids}`, but embedding multiple UUIDs in a URL path or query string is impractical (URL length limits, encoding complexity). A POST with a JSON body `{ "chunk_ids": ["uuid1", "uuid2", ..."] }` is cleaner for batch lookups.

**Alternative considered:** `GET /sources?ids=uuid1&ids=uuid2` — works but becomes unwieldy with many UUIDs and doesn't express the batch-resolve intent clearly.

### D2: Response grouped by chunk, not by source

Each item in the response corresponds to one chunk UUID, carrying both chunk-level metadata (`section`, `page_range`) and source-level metadata (`source_type`, `title`, `author`, `url`). This avoids the client needing to do a second join and maps directly to how chunk_ids appear in text items.

**Alternative considered:** Grouping by source (one source with nested chunks) — more normalized but harder for the client to map back to individual bullet points which reference specific chunks.

### D3: New `sources` router module at `apps/api/src/sources/`

Following the pattern of `auth/` and `sessions/` — a dedicated module with `router.py`, `service.py`, and schemas in `src/schemas/sources.py`. Registered at prefix `/sources` in `main.py`.

### D4: Limit chunk_ids per request to 50

Prevents abuse and keeps query performance bounded. The typical request contains 3-10 chunk IDs from a single response's text items. A limit of 50 covers edge cases (e.g., fetching sources for an entire conversation page).

### D5: Unknown chunk IDs silently omitted

If a chunk UUID doesn't exist in the database, it is simply absent from the response. No error is raised. This handles stale references gracefully (e.g., after knowledge base re-ingestion).

### D6: Add `source_ids` to `MessageItem` schema

The existing `MessageItem` Pydantic model gains `source_ids: list[str] | None = None`. The router maps `m.source_ids` directly. No database or migration changes needed — the column already exists.

## Risks / Trade-offs

- **[Stale chunk IDs]** After re-ingestion, old chunk UUIDs in `messages.source_ids` may no longer exist in `knowledge_chunks`. Mitigation: D5 — silently omit missing chunks. The client should handle partial results gracefully.
- **[No auth scoping per chunk]** Any authenticated user can resolve any chunk UUID. Mitigation: chunk metadata is not sensitive (titles, page numbers). Knowledge base content is shared across all users. If per-user knowledge bases are introduced later, add access control then.
- **[POST for a read operation]** Slightly unconventional REST. Mitigation: the `/resolve` suffix signals this is a lookup action, not a create. Common pattern for batch resolution endpoints.
