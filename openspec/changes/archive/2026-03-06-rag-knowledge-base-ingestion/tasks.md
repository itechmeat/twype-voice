## 1. Infrastructure and dependencies

- [x] 1.1 Add document parsing and ingestion dependencies to `apps/api/pyproject.toml`: `pypdf`, `python-docx`, `ebooklib`, `beautifulsoup4`, `tiktoken`, `httpx`
- [x] 1.2 Configure direct Gemini embeddings for ingestion using `GOOGLE_API_KEY`
- [x] 1.3 Create Alembic migration: alter `embedding` column to `Vector(1536)`, create HNSW index (`ix_knowledge_chunks_embedding_hnsw`) with `vector_cosine_ops`, create GIN index (`ix_knowledge_chunks_search_vector_gin`)

## 2. Text extraction

- [x] 2.1 Create `scripts/ingest.py` with CLI entry point accepting a directory path argument
- [x] 2.2 Implement manifest YAML parser with validation (required fields, source_type enum)
- [x] 2.3 Implement PDF text extraction with page boundary tracking using `pypdf`
- [x] 2.4 Implement EPUB text extraction with chapter structure using `ebooklib` + `beautifulsoup4`
- [x] 2.5 Implement DOCX text extraction using `python-docx`
- [x] 2.6 Implement HTML text extraction with heading-based section detection using `beautifulsoup4`
- [x] 2.7 Write unit tests for each extractor: PDF, EPUB, DOCX, HTML (with small fixture files)

## 3. Chunking and enrichment

- [x] 3.1 Implement deterministic semantic chunking with paragraph/sentence/token-aware splitting (500–800 tokens, 50 overlap, `cl100k_base` tokenizer)
- [x] 3.2 Implement metadata enrichment: attach section, page_range, language, token_count to each chunk
- [x] 3.3 Write unit tests for chunking: long document split, short document single chunk, sentence boundary respect

## 4. Embedding generation

- [x] 4.1 Implement embedding client calling Gemini `batchEmbedContents` via `httpx` with batch size 100
- [x] 4.2 Handle embedding API errors: log and exit without partial data
- [x] 4.3 Write unit tests for embedding client with mocked HTTP responses

## 5. Database loading

- [x] 5.1 Implement upsert for `knowledge_sources` (match by title + source_type)
- [x] 5.2 Implement chunk insertion with `to_tsvector('simple', content)` for `search_vector` column
- [x] 5.3 Implement re-ingestion: delete existing chunks for source before inserting new ones, within a transaction
- [x] 5.4 Write unit tests for DB loading: insert, upsert, re-ingestion, transaction rollback

## 6. Seed data

- [x] 6.1 Add sample `knowledge_sources` record (English article) and at least 3 `knowledge_chunks` with pre-computed 1536-dim embeddings to `scripts/seed.py`
- [x] 6.2 Ensure seed is idempotent for knowledge data (upsert by title + source_type, replace chunks)
- [x] 6.3 Write seed test verifying knowledge source and chunks exist after seeding

## 7. Integration and end-to-end

- [x] 7.1 Write end-to-end test: manifest + small PDF fixture → extract → chunk → mock embed → load → verify DB records
- [x] 7.2 Verify `scripts/ingest.py` runs successfully inside the API container with `DATABASE_URL` and `GOOGLE_API_KEY`
