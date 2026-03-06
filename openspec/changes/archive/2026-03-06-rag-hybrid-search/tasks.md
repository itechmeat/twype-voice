## 1. Agent settings and dependencies

- [x] 1.1 Add `GOOGLE_API_KEY` (conditionally required), `RAG_ENABLED` (default `true`), `RAG_TOP_K` (default `5`, range 1–10), `RAG_LANGUAGE_BOOST` (default `1.5`, range 1.0–5.0), `RAG_EMBEDDING_TIMEOUT` (default `3.0`) to `AgentSettings` in `apps/agent/src/settings.py` with conditional validation: `GOOGLE_API_KEY` required only when `RAG_ENABLED=true`
- [x] 1.2 Add `GOOGLE_API_KEY` to agent service in `compose.yaml` and `compose.prod.yaml`, sourced from root `.env`
- [x] 1.3 Add `GOOGLE_API_KEY` to `.env.example` with a placeholder

## 2. RAG module core

- [x] 2.1 Create `apps/agent/src/rag.py` with `RagEngine` class that accepts `AgentSettings` and `async_sessionmaker`; initializes `EmbeddingClient` (from `src.knowledge_ingestion.embeddings`) with `default_task_type=RETRIEVAL_QUERY` and configured timeout
- [x] 2.2 Implement `RagEngine.embed_query(text: str) -> list[float] | None` — generates a single query embedding via `EmbeddingClient`, returns `None` on error or empty input
- [x] 2.3 Implement the hybrid search SQL query as a `sa.text()` statement: two CTEs (`vector_search` with `<=>` cosine distance LIMIT 20, `text_search` with `plainto_tsquery` + `ts_rank` LIMIT 20), RRF merge with k=60, language boost multiplier, JOIN `knowledge_sources`, LIMIT `$top_k`
- [x] 2.4 Implement `RagEngine.search(query_text: str, language: str | None) -> list[RagChunk]` — calls `embed_query`, executes hybrid search SQL, returns dataclass list with fields: `chunk_id`, `content`, `source_type`, `title`, `author`, `section`, `page_range`, `score`
- [x] 2.5 Implement `format_rag_context(chunks: list[RagChunk]) -> str` — formats chunks into the structured text block for LLM injection per the design template

## 3. Agent integration

- [x] 3.1 Initialize `RagEngine` in `prewarm()` in `main.py` and store in `proc.userdata["rag_engine"]`; skip initialization when `RAG_ENABLED=false`
- [x] 3.2 Pass `rag_engine` (or `None`) to `TwypeAgent` constructor; add it as an instance attribute
- [x] 3.3 Modify `TwypeAgent.llm_node()` in `agent.py`: before calling `super().llm_node()`, extract the last user message text from `chat_ctx`, call `rag_engine.search()`, and if results are non-empty, append a system message with `format_rag_context()` to the chat context
- [x] 3.4 Extract user language from the last user message or fall back to the mode context / settings for the language parameter passed to `search()`

## 4. Tests

- [x] 4.1 Unit tests for `RagEngine.embed_query`: successful embedding, API error returns `None`, empty text returns `None`
- [x] 4.2 Unit tests for hybrid search SQL: mock DB with seed data, verify RRF ranking order, language boost effect, top-K limit, empty results
- [x] 4.3 Unit tests for `format_rag_context`: correct formatting with full metadata, partial metadata (missing author/section), empty list returns empty string
- [x] 4.4 Integration test for `llm_node` RAG injection: verify system message is appended to chat context when RAG returns results, verify no injection when RAG returns empty, verify graceful degradation on RAG error
- [x] 4.5 Unit tests for `AgentSettings` validation: `GOOGLE_API_KEY` required when `RAG_ENABLED=true`, not required when `RAG_ENABLED=false`, `RAG_TOP_K` range validation

## 5. Documentation and environment

- [x] 5.1 Add RAG settings (`GOOGLE_API_KEY`, `RAG_ENABLED`, `RAG_TOP_K`, `RAG_LANGUAGE_BOOST`, `RAG_EMBEDDING_TIMEOUT`) to the Agent env-var group in `.env.example` comments
