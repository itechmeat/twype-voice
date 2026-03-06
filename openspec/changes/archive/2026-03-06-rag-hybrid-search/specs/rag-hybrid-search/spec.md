## ADDED Requirements

### Requirement: Query embedding generation
The agent SHALL convert the user's latest utterance text into an embedding vector by calling the Gemini API (`gemini-embedding-001`) with `taskType=RETRIEVAL_QUERY` and `outputDimensionality=1536`. The embedding SHALL use the same model and dimensions as the ingestion pipeline.

#### Scenario: Successful query embedding
- **WHEN** a user utterance "What are the symptoms of burnout?" is processed
- **THEN** the agent SHALL generate a 1536-dimension embedding vector via the Gemini `batchEmbedContents` endpoint with `taskType=RETRIEVAL_QUERY`

#### Scenario: Embedding API unavailable
- **WHEN** the Gemini API is unreachable or returns an error during query embedding
- **THEN** the agent SHALL log the error, skip RAG retrieval for this utterance, and proceed with the LLM call without knowledge base context

#### Scenario: Empty user utterance
- **WHEN** the extracted user utterance text is empty or whitespace-only
- **THEN** the agent SHALL skip RAG retrieval and proceed without knowledge base context

### Requirement: Hybrid search query
The agent SHALL execute a single SQL query against PostgreSQL that combines vector similarity search (pgvector cosine distance) and full-text search (tsvector) using Reciprocal Rank Fusion (RRF) scoring. The query SHALL join `knowledge_chunks` with `knowledge_sources` to return chunk content and source metadata.

#### Scenario: Hybrid search returns results
- **WHEN** a query embedding is generated and the `knowledge_chunks` table contains matching content
- **THEN** the search SHALL return chunks ranked by RRF score combining cosine similarity rank and full-text relevance rank, with source metadata (source_type, title, author, section, page_range)

#### Scenario: No matching chunks
- **WHEN** a query embedding is generated but no chunks match the similarity or full-text criteria
- **THEN** the search SHALL return an empty result set and the agent SHALL proceed without knowledge base context

#### Scenario: Full-text component matches but vector does not
- **WHEN** a query has strong keyword overlap with chunks but low semantic similarity
- **THEN** the full-text matches SHALL still appear in results via the RRF ranking, scored by their text rank alone

#### Scenario: Vector component matches but full-text does not
- **WHEN** a query is semantically similar to chunks but has no keyword overlap
- **THEN** the vector matches SHALL still appear in results via the RRF ranking, scored by their vector rank alone

### Requirement: Language-aware ranking
The hybrid search SHALL apply a configurable boost factor (default 1.5) to the RRF score of chunks whose `knowledge_sources.language` matches the user's detected language. Cross-language chunks SHALL NOT be excluded — only deprioritized.

#### Scenario: User language matches chunk language
- **WHEN** the user speaks Russian and chunks exist in both Russian and English
- **THEN** Russian-language chunks SHALL receive a 1.5x score boost, ranking higher than equally relevant English chunks

#### Scenario: Only cross-language chunks available
- **WHEN** the user speaks Russian but only English-language chunks match the query
- **THEN** the English chunks SHALL still be returned without the language boost

#### Scenario: Language boost is configurable
- **WHEN** the `RAG_LANGUAGE_BOOST` setting is set to 2.0
- **THEN** matching-language chunks SHALL receive a 2.0x score boost instead of the default 1.5x

### Requirement: Top-K result limit
The search SHALL return at most K results, where K is configurable via `RAG_TOP_K` setting (default 5). The K value SHALL be between 1 and 10 inclusive.

#### Scenario: Default top-K
- **WHEN** `RAG_TOP_K` is not set and 20 chunks match the query
- **THEN** the search SHALL return exactly 5 chunks, ordered by descending RRF score

#### Scenario: Custom top-K
- **WHEN** `RAG_TOP_K` is set to 3
- **THEN** the search SHALL return at most 3 chunks

#### Scenario: Fewer results than K
- **WHEN** `RAG_TOP_K` is 5 but only 2 chunks match
- **THEN** the search SHALL return 2 chunks

### Requirement: LLM context injection
The agent SHALL inject retrieved RAG chunks into the LLM chat context as a system message appended after the user's latest message, before each LLM call. The injected message SHALL contain chunk content and source metadata formatted for the LLM.

#### Scenario: RAG context injected into LLM call
- **WHEN** the hybrid search returns 3 chunks from different sources
- **THEN** the agent SHALL append a system message to the chat context containing all 3 chunks with their source metadata (title, author, source_type, section, page_range)

#### Scenario: No RAG results to inject
- **WHEN** the hybrid search returns zero results
- **THEN** the agent SHALL NOT inject any RAG context message and the LLM SHALL receive the chat context without knowledge base excerpts

#### Scenario: RAG context format
- **WHEN** a chunk from source "Burnout Prevention" by "Dr. Smith" (book), section "Chapter 3", pages "45-47" is retrieved
- **THEN** the injected context SHALL include the source title, author, source_type, section, page_range, and the full chunk content text

### Requirement: Context injection in both modes
The RAG retrieval and context injection SHALL work identically for both voice mode (utterance from STT) and text mode (message from data channel). The query text SHALL be extracted from the last user message in the LLM chat context.

#### Scenario: Voice mode RAG retrieval
- **WHEN** a user speaks a question via voice and the STT produces a final transcript
- **THEN** the agent SHALL perform RAG retrieval using the transcript text and inject results into the LLM context

#### Scenario: Text mode RAG retrieval
- **WHEN** a user sends a text message via the data channel
- **THEN** the agent SHALL perform RAG retrieval using the text message and inject results into the LLM context

### Requirement: Agent settings for RAG
The agent SHALL accept the following configuration via environment variables with defaults:
- `GOOGLE_API_KEY` (required): API key for Gemini embedding generation
- `RAG_ENABLED` (default: `true`): enable/disable RAG retrieval
- `RAG_TOP_K` (default: `5`, range: 1–10): maximum number of chunks to retrieve
- `RAG_LANGUAGE_BOOST` (default: `1.5`, range: 1.0–5.0): score multiplier for matching-language chunks
- `RAG_EMBEDDING_TIMEOUT` (default: `3.0` seconds): timeout for the embedding API call

#### Scenario: RAG disabled
- **WHEN** `RAG_ENABLED` is set to `false`
- **THEN** the agent SHALL skip all RAG retrieval and never query the knowledge base

#### Scenario: Missing GOOGLE_API_KEY with RAG enabled
- **WHEN** `RAG_ENABLED` is `true` and `GOOGLE_API_KEY` is not set
- **THEN** the agent SHALL fail to start with a validation error indicating the missing key

#### Scenario: GOOGLE_API_KEY not required when RAG disabled
- **WHEN** `RAG_ENABLED` is `false` and `GOOGLE_API_KEY` is not set
- **THEN** the agent SHALL start successfully without a validation error

### Requirement: Graceful degradation
The agent SHALL handle RAG failures gracefully. If embedding generation or database search fails, the agent SHALL log the error and proceed with the LLM call without knowledge base context. RAG failures SHALL NOT interrupt the voice or text pipeline.

#### Scenario: Database connection failure during search
- **WHEN** the PostgreSQL connection fails during hybrid search
- **THEN** the agent SHALL log the error and invoke the LLM without RAG context

#### Scenario: Embedding timeout
- **WHEN** the Gemini API does not respond within `RAG_EMBEDDING_TIMEOUT` seconds
- **THEN** the agent SHALL log a timeout warning and invoke the LLM without RAG context

#### Scenario: Malformed search results
- **WHEN** the database query returns unexpected data
- **THEN** the agent SHALL log the error and invoke the LLM without RAG context
