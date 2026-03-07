## 1. Pydantic Schemas

- [x] 1.1 Create `apps/api/src/schemas/sources.py` with `ResolveSourcesRequest` (chunk_ids: list[UUID], max 50), `SourceItem` (chunk_id, source_type, title, author, url, section, page_range), and `ResolveSourcesResponse` (items: list[SourceItem])
- [x] 1.2 Add `source_ids: list[str] | None = None` field to `MessageItem` in `apps/api/src/schemas/sessions.py`

## 2. Sources Service

- [x] 2.1 Create `apps/api/src/sources/__init__.py` and `apps/api/src/sources/service.py` with async function `resolve_chunks(chunk_ids: list[UUID], db: AsyncSession) -> list[SourceItem]` that joins `knowledge_chunks` + `knowledge_sources` and returns matched items
- [x] 2.2 Handle empty chunk_ids list (return early without DB query)

## 3. Sources Router

- [x] 3.1 Create `apps/api/src/sources/router.py` with `POST /resolve` endpoint, authenticated via `get_current_user`, calling the service and returning `ResolveSourcesResponse`
- [x] 3.2 Register sources router in `apps/api/src/main.py` at prefix `/sources` with tag `sources`

## 4. Session Messages Update

- [x] 4.1 Update `list_messages` in `apps/api/src/sessions/router.py` to include `source_ids=m.source_ids` in `MessageItem` construction

## 5. Tests

- [x] 5.1 Add unit tests for `resolve_chunks` service: valid IDs, missing IDs, empty list, mixed found/not-found
- [x] 5.2 Add endpoint tests for `POST /sources/resolve`: success, empty body, over-limit (51 IDs), unauthenticated, all-missing
- [x] 5.3 Add/update endpoint test for `GET /sessions/{id}/messages` verifying `source_ids` field is present in response
