## Why

S13 populated `knowledge_chunks` with embeddings (pgvector) and full-text search vectors (tsvector), but the agent has no retrieval logic — RAG chunks are never queried at runtime. Without hybrid search, the LLM answers from general knowledge only, losing the core value proposition of expert, source-backed responses. S14 closes this gap by adding a RAG Engine to the agent that retrieves relevant chunks on every utterance and injects them into the LLM context.

## What Changes

- Add a **RAG Engine** module in `apps/agent/src/rag/` that:
  - Converts user utterance text to an embedding via Gemini API (`gemini-embedding-001`, 1536 dimensions)
  - Executes hybrid search against PostgreSQL: cosine distance (pgvector) + full-text search (tsvector) + metadata filters (language, source_type)
  - Ranks and deduplicates results, prioritizing chunks in the user's language without excluding cross-language matches
  - Returns top-K (3–5, configurable) chunks with source metadata (chunk_id, source_type, title, author, section, page_range)
- Integrate RAG retrieval into the agent's **LLM context pipeline** — inject retrieved chunks before each LLM call in `llm_node`
- Format RAG context as structured text with source attribution metadata so the existing `rag_prompt` layer can guide the LLM's usage of sources
- Add agent settings for RAG configuration: top-K count, similarity threshold, embedding credentials, search weights

## Capabilities

### New Capabilities
- `rag-hybrid-search`: RAG Engine with query embedding, hybrid search (vector + full-text + metadata filters), ranking, and LLM context injection in the agent

### Modified Capabilities

## Impact

- **Agent codebase** (`apps/agent/`): new `src/rag/` module, modifications to `agent.py` (LLM context injection in `llm_node`), new settings in `settings.py`
- **Dependencies**: `google-genai` (or `httpx` for direct Gemini API calls) for query embedding in the agent container, `asyncpg`/`sqlalchemy` for search queries
- **Environment**: agent container needs `GOOGLE_API_KEY` for embedding generation (same key used by API container for ingestion)
- **Database**: read-only queries against existing `knowledge_chunks` and `knowledge_sources` tables; no schema changes
- **Existing prompt system**: no changes — `rag_prompt` layer already exists and instructs the LLM on source usage
