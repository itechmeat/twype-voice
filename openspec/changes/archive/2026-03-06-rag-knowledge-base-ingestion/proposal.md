## Why

The agent has a `rag_prompt` layer instructing it to rely on knowledge base materials, but no data exists in `knowledge_chunks` to search against. S14 (hybrid search at query time) depends on ingested, chunked, and embedded content. The `scripts/ingest.py` script and supporting infrastructure are needed to populate the knowledge base from source documents.

## What Changes

- **Ingestion script** (`scripts/ingest.py`) — CLI tool that extracts text from PDF, EPUB, DOCX, and HTML files; performs semantic chunking; enriches metadata; generates embeddings via the Gemini API; and loads everything into `knowledge_sources` + `knowledge_chunks` tables.
- **Direct Gemini embedding client** — configure `ingest.py` to call `gemini-embedding-001` directly from the API container using `GOOGLE_API_KEY`.
- **HNSW index migration** — Alembic migration creating an HNSW index on `knowledge_chunks.embedding` and a GIN index on `knowledge_chunks.search_vector` for efficient hybrid search.
- **tsvector population** — the ingestion pipeline populates the `search_vector` column using PostgreSQL `to_tsvector()` for full-text search.
- **Python dependencies** — add document parsing libraries (`pypdf`, `python-docx`, `ebooklib`, `beautifulsoup4`) to the API workspace.

## Capabilities

### New Capabilities
- `knowledge-ingestion`: CLI script for extracting, chunking, embedding, and loading knowledge base content into PostgreSQL. Covers text extraction from multiple formats, semantic chunking, metadata enrichment, embedding generation, tsvector population, and batch insert.

### Modified Capabilities
- `database-seed`: Add sample knowledge source and chunks to the seed script for development and testing.

## Impact

- `scripts/ingest.py` — new file, core of this story
- `apps/api/migrations/versions/` — new migration for HNSW + GIN indexes
- `apps/api/pyproject.toml` — add document parsing dependencies
- `scripts/seed.py` — add sample knowledge source + chunks
- `openspec/specs/database-seed/spec.md` — updated requirements for knowledge seed data
