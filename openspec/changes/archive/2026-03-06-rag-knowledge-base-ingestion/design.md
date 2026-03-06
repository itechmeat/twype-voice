## Context

Database tables `knowledge_sources` and `knowledge_chunks` exist with pgvector extension enabled. The `embedding` column (Vector) and `search_vector` column (TSVECTOR) are defined but no data populates them. No HNSW or GIN indexes exist yet. LiteLLM proxy serves chat LLM models, while ingestion embeddings are generated directly from Gemini by the API container. The `rag_prompt` layer is already seeded and assembled into agent instructions.

S13 creates the ingestion pipeline that fills the knowledge base. S14 will build the query-time search on top of this data.

Constraints:
- All source code in English (CLAUDE.md rule).
- Script runs inside the `api` container with access to `DATABASE_URL`.
- Embeddings generated directly via Gemini API from the API container.
- pgvector Vector column has no fixed dimension yet — the migration must set the dimension to match the chosen embedding model.

## Goals / Non-Goals

**Goals:**
- CLI script (`scripts/ingest.py`) that ingests documents from a local directory into the knowledge base.
- Support for PDF, EPUB, DOCX, and HTML text extraction.
- Semantic chunking that produces meaningful, self-contained blocks (not fixed token windows).
- Embedding generation via Gemini `batchEmbedContents`.
- TSVECTOR population for full-text search.
- HNSW index on embeddings and GIN index on search_vector for efficient retrieval.
- Sample knowledge data in the seed script for development.

**Non-Goals:**
- Audio transcription — deferred. The `source_type` schema supports it, but the ingestion script will not handle audio files in S13. Audio sources can be added as pre-transcribed text.
- Real-time / incremental ingestion — the script is a batch tool, run manually.
- RAG query-time search (S14), dual-layer responses (S15), or source attribution API (S16).
- Web scraping or URL fetching — the script reads local files only.
- GraphRAG or knowledge graph construction.

## Decisions

### D1: Embedding model — gemini-embedding-001 via direct Gemini API

**Decision:** Use `gemini-embedding-001` directly from the API container. Request `outputDimensionality=1536` and `taskType=RETRIEVAL_DOCUMENT`. The ingest script calls Gemini `batchEmbedContents` with `GOOGLE_API_KEY`.

**Alternatives considered:**
- OpenAI embeddings via LiteLLM — rejected because ingestion only needs embeddings, while direct Gemini gives explicit control over `taskType` and dimensionality without adding a proxy hop.
- Local model (e.g., sentence-transformers) — rejected because it requires GPU or adds significant latency on CPU.

**Rationale:** Gemini embeddings are already part of the project provider set, support retrieval-specific task types, and can emit 1536-dimensional vectors that match the pgvector schema.

### D2: Semantic chunking via deterministic token-aware splitter with overlap

**Decision:** Use an internal deterministic splitter with paragraph-first packing, sentence-aware fallback, word fallback, and token-window fallback. Target chunk size: 500–800 tokens. Overlap: 50 tokens. Token counting via `tiktoken` (`cl100k_base`).

**Alternatives considered:**
- Fixed-size chunking (e.g., 512 tokens) — rejected because it cuts mid-sentence and loses context.
- LLM-based semantic chunking (e.g., ask the LLM to split) — rejected because it is slow and expensive for bulk ingestion.
- `langchain-text-splitters` — rejected to avoid an unnecessary dependency chain and `pydantic.v1` compatibility warnings.

**Rationale:** The internal splitter keeps the behavior deterministic and testable while preserving natural boundaries without relying on the LangChain stack.

### D3: HNSW index with cosine distance

**Decision:** Create HNSW index on `knowledge_chunks.embedding` using cosine distance operator (`vector_cosine_ops`). Parameters: `m=16`, `ef_construction=64`. Also create GIN index on `search_vector` for full-text search.

**Alternatives considered:**
- IVFFlat index — rejected because it requires pre-training on data (needs `CREATE INDEX` after data load) and is less accurate for small-to-medium datasets.
- No index (brute-force) — rejected because even with ~10K chunks, sequential scan becomes slow.

**Rationale:** HNSW provides good recall with fast query time and does not require retraining when new data is added. Cosine distance is the standard for normalized embeddings. The parameters are conservative defaults suitable for up to 100K chunks.

### D4: Vector dimension set via migration

**Decision:** Create a new Alembic migration that:
1. Alters `knowledge_chunks.embedding` to `Vector(1536)` (typed dimension).
2. Creates HNSW index: `CREATE INDEX ix_knowledge_chunks_embedding_hnsw ON knowledge_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)`.
3. Creates GIN index: `CREATE INDEX ix_knowledge_chunks_search_vector_gin ON knowledge_chunks USING gin (search_vector)`.

**Rationale:** The initial migration created `Vector()` without a dimension. Setting the dimension is required for HNSW index creation and ensures all embeddings have consistent dimensionality.

### D5: Ingestion script architecture — pipeline stages

**Decision:** The ingest script follows a 5-stage pipeline:
1. **Extract** — read file, detect format, extract raw text + structural metadata (pages, chapters).
2. **Chunk** — split text into semantic chunks with overlap.
3. **Enrich** — attach metadata (source_type, section, page_range, language, token_count).
4. **Embed** — batch embed chunks via Gemini `batchEmbedContents` (batch size: 100 chunks per request).
5. **Load** — upsert source + insert chunks with embeddings and tsvector into PostgreSQL.

Each stage is a pure function (except Load which hits the DB). The script accepts a directory path and a metadata JSON/YAML file describing the sources.

**Alternatives considered:**
- Single monolithic function — rejected because it is hard to test and extend.
- Async pipeline with queues — rejected for MVP; batch processing is sufficient.

**Rationale:** Staged pipeline is testable, debuggable (can inspect output at each stage), and naturally extends to new formats.

### D6: Metadata input via YAML manifest

**Decision:** Each ingestion run requires a `manifest.yaml` file in the source directory describing the files and their metadata:

```yaml
sources:
  - file: "psychology-basics.pdf"
    source_type: book
    title: "Psychology Basics"
    author: "John Smith"
    language: en
    tags: ["psychology", "basics"]
  - file: "anxiety-guide.epub"
    source_type: book
    title: "Anxiety Management Guide"
    language: ru
```

The script reads the manifest, processes each file, and creates `knowledge_sources` + `knowledge_chunks` records.

**Alternatives considered:**
- CLI flags for metadata — rejected because it does not scale for multiple files.
- Auto-detect metadata from file content — rejected because it is unreliable and the metadata (author, language, tags) cannot be reliably extracted from all formats.

**Rationale:** YAML manifest is explicit, versionable, and supports batch ingestion of multiple files with different metadata.

### D7: tsvector population via SQL

**Decision:** Populate `search_vector` using PostgreSQL `to_tsvector('simple', content)` during the Load stage. Use the `simple` dictionary (no stemming) to support mixed-language content (en + ru). The tsvector is generated server-side via SQL in the INSERT statement.

**Alternatives considered:**
- Language-specific dictionaries (english, russian) — rejected because chunks may be mixed-language and selecting the right dictionary per chunk adds complexity.
- Python-side tsvector generation — rejected because PostgreSQL's `to_tsvector` is the authoritative source and avoids inconsistencies.

**Rationale:** `simple` dictionary splits on whitespace and lowercases, which is sufficient for keyword-level full-text search. S14 will combine tsvector with vector similarity for hybrid ranking.

## Risks / Trade-offs

**[Embedding model cost]** Gemini embeddings add per-token API cost for ingestion runs.
-> Mitigation: Batch embedding reduces API calls. Log token counts for cost tracking.

**[Chunk size tuning]** 500–800 tokens is a starting point. Too small = lost context, too large = diluted relevance.
-> Mitigation: Configurable via CLI flags. Can re-ingest with different settings.

**[HNSW index build time]** Building HNSW on >50K chunks can take minutes.
-> Mitigation: Index is created once via migration (empty table). Incremental inserts are fast. For large bulk loads, drop and recreate index.

**[Vector dimension lock-in]** Setting dimension to 1536 ties us to the chosen Gemini output dimensionality.
-> Mitigation: Changing the embedding model requires a migration to alter the dimension and re-embed all chunks. This is acceptable for MVP.
