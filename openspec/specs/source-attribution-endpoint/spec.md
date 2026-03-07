## Requirements

### Requirement: Resolve chunk IDs to source metadata
The system SHALL provide a `POST /sources/resolve` endpoint that accepts a JSON body with a `chunk_ids` field (list of UUID strings) and returns full source metadata for each found chunk. The response SHALL be a list of objects, each containing chunk-level fields (`chunk_id`, `section`, `page_range`) and source-level fields (`source_type`, `title`, `author`, `url`). The endpoint SHALL require authentication via JWT Bearer token.

#### Scenario: Successful resolution of chunk IDs
- **WHEN** authenticated user sends `POST /sources/resolve` with `{ "chunk_ids": ["uuid-1", "uuid-2"] }` and both chunks exist
- **THEN** system returns 200 with a list of 2 items, each containing `chunk_id`, `section`, `page_range`, `source_type`, `title`, `author`, `url`

#### Scenario: Some chunk IDs not found
- **WHEN** authenticated user sends `POST /sources/resolve` with `{ "chunk_ids": ["existing-uuid", "nonexistent-uuid"] }`
- **THEN** system returns 200 with a list containing only the item for `existing-uuid`; the nonexistent UUID is silently omitted

#### Scenario: All chunk IDs not found
- **WHEN** authenticated user sends `POST /sources/resolve` with chunk IDs that do not exist in the database
- **THEN** system returns 200 with an empty list

#### Scenario: Empty chunk_ids list
- **WHEN** authenticated user sends `POST /sources/resolve` with `{ "chunk_ids": [] }`
- **THEN** system returns 200 with an empty list without executing a database query

#### Scenario: Unauthenticated request
- **WHEN** request to `POST /sources/resolve` has no valid JWT
- **THEN** system returns 401 Unauthorized

### Requirement: Limit chunk IDs per request
The system SHALL reject requests with more than 50 chunk IDs. The validation SHALL be performed before any database query.

#### Scenario: Chunk IDs within limit
- **WHEN** authenticated user sends `POST /sources/resolve` with 50 chunk IDs
- **THEN** system processes the request normally

#### Scenario: Chunk IDs exceed limit
- **WHEN** authenticated user sends `POST /sources/resolve` with 51 or more chunk IDs
- **THEN** system returns 422 with a validation error indicating the maximum is 50

### Requirement: Query joins knowledge_chunks with knowledge_sources
The system SHALL resolve chunk metadata by joining `knowledge_chunks` on `knowledge_sources` via `source_id`. The query SHALL select: `knowledge_chunks.id`, `knowledge_chunks.section`, `knowledge_chunks.page_range`, `knowledge_sources.source_type`, `knowledge_sources.title`, `knowledge_sources.author`, `knowledge_sources.url`. The query SHALL filter by `knowledge_chunks.id IN (chunk_ids)`.

#### Scenario: Chunk with all source fields populated
- **WHEN** a chunk belongs to a source with `source_type="book"`, `title="Medical Guide"`, `author="Dr. Smith"`, `url=null`
- **THEN** the response item SHALL have `source_type="book"`, `title="Medical Guide"`, `author="Dr. Smith"`, `url=null`

#### Scenario: Chunk with section and page_range
- **WHEN** a chunk has `section="Chapter 3"` and `page_range="45-47"`
- **THEN** the response item SHALL have `section="Chapter 3"` and `page_range="45-47"`

#### Scenario: Chunk without optional fields
- **WHEN** a chunk has `section=null` and `page_range=null` and its source has `author=null` and `url=null`
- **THEN** the response item SHALL have `section=null`, `page_range=null`, `author=null`, `url=null`

### Requirement: Sources router registration
The sources router SHALL be registered in the FastAPI application at the `/sources` prefix with the `sources` tag.

#### Scenario: Router is accessible
- **WHEN** the API starts
- **THEN** endpoint `POST /sources/resolve` is available and documented in OpenAPI schema

### Requirement: Response schema
The response SHALL be a JSON object with an `items` field containing a list of source item objects. Each source item SHALL have the following fields: `chunk_id` (UUID string), `source_type` (string: one of book, video, podcast, article, post), `title` (string), `author` (string or null), `url` (string or null), `section` (string or null), `page_range` (string or null).

#### Scenario: Response structure
- **WHEN** authenticated user resolves 2 valid chunk IDs
- **THEN** the response body SHALL be `{ "items": [{ "chunk_id": "...", "source_type": "...", "title": "...", "author": ..., "url": ..., "section": ..., "page_range": ... }, ...] }`
