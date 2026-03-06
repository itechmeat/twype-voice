## Context

S13 built the knowledge ingestion pipeline: text extraction, semantic chunking, embedding generation (Gemini `gemini-embedding-001`, 1536 dims), and loading into `knowledge_chunks` with pgvector and tsvector indexes. The agent currently has no retrieval logic — the `rag_prompt` layer exists in the prompt system but never receives actual chunks.

The agent runs as a LiveKit Agent process. It connects to PostgreSQL via async SQLAlchemy (`apps/agent/src/db.py`), loads prompts at session start (`prompts.py`), and processes utterances through `TwypeAgent.llm_node()` in `agent.py`. The agent already depends on `twype-api` (workspace dependency), giving access to models and `knowledge_constants`.

The existing `EmbeddingClient` in `apps/api/src/knowledge_ingestion/embeddings.py` calls Gemini's `batchEmbedContents` with `RETRIEVAL_DOCUMENT` task type. Query-time embeddings need the same client but with `RETRIEVAL_QUERY` task type.

## Goals / Non-Goals

**Goals:**
- Retrieve relevant knowledge chunks on every LLM call using hybrid search (vector + full-text + metadata filters)
- Inject top-K chunks with source metadata into the LLM context so responses are grounded in the knowledge base
- Prioritize chunks in the user's detected language without excluding cross-language results
- Keep retrieval latency under 200ms (query embedding + DB search) to stay within the 800ms voice-to-voice target

**Non-Goals:**
- Dual-layer response formatting (S15)
- Source attribution API endpoints (S16)
- Re-ranking with a cross-encoder or LLM-based reranker
- Caching embeddings or search results across turns (can be added later)
- Modifying the knowledge ingestion pipeline or DB schema

## Decisions

### D1: Reuse `EmbeddingClient` from `twype-api` for query embeddings

The agent already depends on `twype-api` as a workspace package. Rather than duplicating embedding logic, import and use `EmbeddingClient` with `task_type=RETRIEVAL_QUERY` for query-time embeddings.

**Alternative considered:** Dedicated lightweight embedding function in agent. Rejected because maintaining two embedding implementations increases divergence risk and the existing client already handles batching, error handling, and dimension validation.

### D2: Single SQL query for hybrid search with RRF ranking

Combine vector similarity (pgvector `<=>` cosine distance) and full-text search (tsvector `ts_rank`) in a single SQL query using Reciprocal Rank Fusion (RRF) to merge the two ranking signals. This avoids two round-trips and lets PostgreSQL optimize the combined query.

The query structure:
1. CTE `vector_search`: `ORDER BY embedding <=> $query_embedding LIMIT 20`
2. CTE `text_search`: `WHERE search_vector @@ plainto_tsquery('simple', $query_text) ORDER BY ts_rank(...) LIMIT 20`
3. `UNION` + RRF score: `1/(k+rank_vector) + 1/(k+rank_text)` with k=60
4. Language boost: multiply score by a configurable factor (default 1.5) for chunks matching the user's language
5. `JOIN knowledge_sources` to fetch source metadata
6. `LIMIT $top_k`

**Alternative considered:** Application-side merging (two queries, merge in Python). Rejected for the extra round-trip and added complexity. PostgreSQL handles this efficiently with CTEs.

**Alternative considered:** Using LiteLLM for embeddings. Rejected because LiteLLM adds an extra hop and the ingestion pipeline already calls Gemini directly — consistency matters for vector similarity.

### D3: RAG module as `apps/agent/src/rag.py`

A single module (not a package) is sufficient for the current scope: one function to embed the query, one to search, one to format context. If the module grows beyond ~300 lines, it can be split into a package later.

**Alternative considered:** `apps/agent/src/rag/` package with separate files. Premature for the current scope of ~3 functions.

### D4: Context injection via `before_llm_cb` pattern in `llm_node`

Override `TwypeAgent.llm_node()` (already overridden for thinking sounds) to call the RAG engine before passing context to the LLM. The RAG results are appended as a system message at the end of the chat context, after the user's latest message. This keeps the RAG context close to the query and avoids modifying the prompt builder.

Format of the injected RAG context message:
```
[Knowledge Base Context]
The following excerpts are from verified sources. Use them to support your response.

Source: {title} by {author} ({source_type})
Section: {section} | Pages: {page_range}
---
{chunk content}

Source: ...
```

**Alternative considered:** Injecting RAG context into the system prompt via `build_instructions()`. Rejected because the system prompt is built once at session start and frozen as a config snapshot. RAG context must be dynamic per utterance.

### D5: `GOOGLE_API_KEY` passed to agent container

The agent container needs `GOOGLE_API_KEY` to generate query embeddings via the Gemini API. This is the same key already used by the API container for ingestion. Added as a required setting in `AgentSettings`.

### D6: Graceful degradation on RAG failure

If embedding generation or search fails, log the error and proceed without RAG context. The LLM still has the system prompt and conversation history — it answers from general knowledge. This prevents RAG infrastructure issues from breaking the entire voice pipeline.

### D7: Extract query text from chat context, not raw STT

Use the last user message from the LLM chat context (already cleaned and final) as the search query, rather than hooking into the STT transcript event. This works for both voice and text modes and ensures the query matches what the LLM sees.

## Risks / Trade-offs

**[Latency]** Embedding generation adds ~50-100ms per query (single text, Gemini API). Combined with DB search (~20-50ms), total RAG overhead is ~70-150ms. This is acceptable within the 800ms target, but network issues to Gemini could spike latency. → Mitigation: timeout on embedding call (3s), graceful degradation (D6).

**[Relevance]** RRF with fixed k=60 and language boost may not produce optimal ranking for all query types. → Mitigation: configurable weights and top-K via `AgentSettings`, allowing tuning without code changes.

**[Cost]** Every utterance triggers an embedding API call (~$0.00001 per query at current Gemini pricing). For 30 concurrent sessions with ~10 utterances per minute each, this is negligible (~$0.13/hour). → No mitigation needed.

**[Single query embedding]** Using only the latest utterance as the search query may miss context from multi-turn conversations. → Acceptable for MVP. Future improvement: concatenate last N utterances or use LLM-generated search query.
