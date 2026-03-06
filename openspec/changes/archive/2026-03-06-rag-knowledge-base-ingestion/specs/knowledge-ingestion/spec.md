## ADDED Requirements

### Requirement: CLI entry point
The system SHALL provide a `scripts/ingest.py` script that accepts a directory path containing source files and a `manifest.yaml` describing each file's metadata. The script SHALL process all files listed in the manifest and load the results into `knowledge_sources` and `knowledge_chunks` tables.

#### Scenario: Ingest a directory with manifest
- **WHEN** `python scripts/ingest.py /path/to/sources` is run and the directory contains a valid `manifest.yaml` and referenced files
- **THEN** the script SHALL create `knowledge_sources` records and corresponding `knowledge_chunks` records for each file

#### Scenario: Missing manifest
- **WHEN** `python scripts/ingest.py /path/to/sources` is run and no `manifest.yaml` exists in the directory
- **THEN** the script SHALL exit with an error message indicating the missing manifest

#### Scenario: Missing referenced file
- **WHEN** `manifest.yaml` references a file that does not exist in the directory
- **THEN** the script SHALL log a warning for that file, skip it, and continue processing the remaining files

#### Scenario: Idempotent re-ingestion
- **WHEN** the script is run twice on the same manifest
- **THEN** existing `knowledge_sources` records SHALL be updated (matched by title + source_type) and their chunks SHALL be replaced, not duplicated

### Requirement: Manifest format
The manifest SHALL be a YAML file with a `sources` key containing a list of source entries. Each entry SHALL have: `file` (filename), `source_type` (one of: book, video, podcast, article, post), `title`, and `language`. Optional fields: `author`, `url`, `tags` (list of strings).

#### Scenario: Valid manifest parsed
- **WHEN** the manifest contains a valid source entry with all required fields
- **THEN** the script SHALL use those values to create the `knowledge_sources` record

#### Scenario: Invalid source_type rejected
- **WHEN** a manifest entry has `source_type: "unknown"`
- **THEN** the script SHALL log a warning and skip that entry

#### Scenario: Missing required field
- **WHEN** a manifest entry is missing the `title` field
- **THEN** the script SHALL log a warning and skip that entry

### Requirement: Text extraction from PDF
The script SHALL extract text from PDF files preserving page boundaries. Each page's content SHALL be associated with its page number for `page_range` metadata on resulting chunks.

#### Scenario: PDF with multiple pages
- **WHEN** a PDF file with 50 pages is processed
- **THEN** the extracted text SHALL include content from all pages and chunks SHALL have `page_range` values indicating their source pages (e.g., "12-13")

#### Scenario: PDF with no extractable text
- **WHEN** a PDF file contains only scanned images with no embedded text
- **THEN** the script SHALL log a warning that no text was extracted and skip the file

### Requirement: Text extraction from EPUB
The script SHALL extract text from EPUB files preserving chapter structure. Chapter titles SHALL be used as `section` metadata on resulting chunks.

#### Scenario: EPUB with chapters
- **WHEN** an EPUB file with multiple chapters is processed
- **THEN** the extracted text SHALL include content from all chapters and chunks SHALL have `section` values reflecting the chapter name

### Requirement: Text extraction from DOCX
The script SHALL extract text from DOCX files preserving paragraph structure.

#### Scenario: DOCX with paragraphs
- **WHEN** a DOCX file is processed
- **THEN** the extracted text SHALL include all paragraph content

### Requirement: Text extraction from HTML
The script SHALL extract text from HTML files, stripping tags and preserving meaningful structure (headings, paragraphs). Heading text SHALL be used as `section` metadata.

#### Scenario: HTML with headings
- **WHEN** an HTML file with `<h1>` and `<h2>` tags is processed
- **THEN** the extracted text SHALL include heading and body content, and chunks SHALL have `section` values from the nearest heading

### Requirement: Semantic chunking
The script SHALL split extracted text into chunks of 500–800 tokens with 50-token overlap using paragraph and sentence boundaries as split points. Token counting SHALL use the `cl100k_base` tokenizer. Each chunk SHALL be a self-contained meaningful block.

#### Scenario: Long document chunked
- **WHEN** a document with 10,000 tokens is processed
- **THEN** the result SHALL be approximately 15–20 chunks, each between 500 and 800 tokens, with 50-token overlap between consecutive chunks

#### Scenario: Short document not split
- **WHEN** a document with 300 tokens is processed
- **THEN** the result SHALL be a single chunk containing the full text

#### Scenario: Chunk boundaries respect sentences
- **WHEN** a chunk boundary falls mid-sentence
- **THEN** the splitter SHALL extend or shorten the chunk to the nearest sentence boundary

### Requirement: Metadata enrichment
Each chunk SHALL be enriched with metadata from the manifest and structural extraction: `section` (chapter or heading name), `page_range` (source pages), `language` (from manifest), and `token_count` (actual token count of the chunk).

#### Scenario: Chunk metadata populated
- **WHEN** a chunk is created from pages 12–13 of a PDF under section "Chapter 3"
- **THEN** the chunk SHALL have `section="Chapter 3"`, `page_range="12-13"`, and `token_count` set to the actual token count

### Requirement: Embedding generation via Gemini API
The script SHALL generate embeddings for each chunk by calling the Gemini `batchEmbedContents` endpoint with `gemini-embedding-001`. Embeddings SHALL be generated in batches of up to 100 chunks per request. The request SHALL set `taskType=RETRIEVAL_DOCUMENT` and `outputDimensionality=1536`. The resulting vectors SHALL be stored in the `knowledge_chunks.embedding` column.

#### Scenario: Batch embedding
- **WHEN** 250 chunks are ready for embedding
- **THEN** the script SHALL make 3 embedding API calls (100 + 100 + 50) and store the resulting vectors

#### Scenario: Embedding API failure
- **WHEN** the Gemini API is unreachable or returns an error
- **THEN** the script SHALL log the error and exit without loading partial data

#### Scenario: Embedding dimension matches schema
- **WHEN** embeddings are generated
- **THEN** each embedding vector SHALL have exactly 1536 dimensions

### Requirement: tsvector population
The script SHALL populate the `knowledge_chunks.search_vector` column using PostgreSQL `to_tsvector('simple', content)` executed server-side during the INSERT statement.

#### Scenario: search_vector set on insert
- **WHEN** a chunk is inserted into `knowledge_chunks`
- **THEN** the `search_vector` column SHALL contain a tsvector generated from the chunk's content using the `simple` dictionary

### Requirement: Database loading
The script SHALL insert `knowledge_sources` records (upsert by title + source_type) and then insert all associated `knowledge_chunks` records within a transaction. When re-ingesting, existing chunks for the source SHALL be deleted before inserting new ones.

#### Scenario: Source and chunks inserted
- **WHEN** a file with 20 chunks is ingested
- **THEN** one `knowledge_sources` record and 20 `knowledge_chunks` records SHALL be created in the database

#### Scenario: Re-ingestion replaces chunks
- **WHEN** a previously ingested source is re-ingested with updated content
- **THEN** old chunks for that source SHALL be deleted and new chunks SHALL be inserted

#### Scenario: Transaction rollback on error
- **WHEN** an error occurs during chunk insertion
- **THEN** the entire transaction for that source SHALL be rolled back, leaving no partial data

### Requirement: HNSW and GIN index migration
An Alembic migration SHALL create an HNSW index on `knowledge_chunks.embedding` using `vector_cosine_ops` and a GIN index on `knowledge_chunks.search_vector`. The migration SHALL also alter the `embedding` column to `Vector(1536)`.

#### Scenario: Migration creates indexes
- **WHEN** `alembic upgrade head` is run
- **THEN** the HNSW index `ix_knowledge_chunks_embedding_hnsw` and GIN index `ix_knowledge_chunks_search_vector_gin` SHALL exist on the `knowledge_chunks` table

#### Scenario: Embedding column dimension set
- **WHEN** the migration is applied
- **THEN** the `embedding` column SHALL accept only vectors of dimension 1536

### Requirement: Embedding credentials for ingestion
The API container SHALL receive `GOOGLE_API_KEY` so `scripts/ingest.py` can call the Gemini embeddings endpoint directly.

#### Scenario: Embedding credentials available
- **WHEN** `scripts/ingest.py` runs inside the API container with a valid `GOOGLE_API_KEY`
- **THEN** the script SHALL be able to generate embeddings without routing through LiteLLM
