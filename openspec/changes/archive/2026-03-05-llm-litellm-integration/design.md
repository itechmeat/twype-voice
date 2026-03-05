## Context

The agent pipeline currently runs VAD -> STT (Deepgram) and transcribes user speech, but produces no responses. The next step is connecting an LLM so the agent can generate streaming conversational replies. The infrastructure is already prepared: LiteLLM Proxy container exists in docker-compose with a health check, Gemini Flash-Lite is configured in `configs/litellm.yaml`, and `LITELLM_URL` is already passed to the agent container as an environment variable.

LiveKit Agents framework provides `AgentSession(llm=...)` which accepts any OpenAI-compatible LLM plugin. The `livekit-plugins-openai` package can target LiteLLM Proxy by overriding the `base_url`.

## Goals / Non-Goals

**Goals:**
- Agent generates streaming LLM responses to user speech via LiteLLM Proxy
- LiteLLM Proxy configured with Gemini Flash-Lite (primary) and GPT-4.1-mini (fallback)
- Basic hardcoded system prompt defines agent persona and behavior
- Agent responses persisted to `messages` table (`role=assistant`, `mode=voice`)
- Graceful handling of LLM unavailability (timeout, error message to user)

**Non-Goals:**
- Prompt loading from database (S10)
- TTS integration (S08) — LLM output is text-only for now
- RAG context injection (S14)
- Emotional adaptation (S17)
- Dual-layer response format (S15)

## Decisions

### D1: Use `livekit-plugins-openai` with `base_url` override

**Decision:** Use the official `livekit-plugins-openai` plugin, pointing it at LiteLLM Proxy via `base_url=settings.LITELLM_URL + "/v1"`.

**Alternatives considered:**
- Direct HTTP calls to LiteLLM — loses streaming integration with AgentSession pipeline, requires reimplementing frame routing.
- `litellm` Python SDK in-process — adds a heavy dependency, defeats the purpose of the proxy container, complicates model fallback configuration.

**Rationale:** The plugin integrates natively with `AgentSession(llm=...)`, handles streaming token delivery, and LiteLLM Proxy is already OpenAI-compatible. Model switching happens in `litellm.yaml` without agent code changes.

### D2: LiteLLM fallback via `model_list` router

**Decision:** Configure GPT-4.1-mini as a fallback model in `litellm.yaml` using the built-in router with `fallbacks` setting. The agent always requests model name `gemini-flash-lite` — LiteLLM handles failover transparently.

**Alternatives considered:**
- Agent-side fallback (catch error, retry with different model) — adds complexity to agent code, LiteLLM already provides this.
- No fallback — single point of failure on one provider.

**Rationale:** LiteLLM's router handles retries and fallback natively. The agent code stays simple — one model name, one endpoint.

### D3: Basic hardcoded system prompt

**Decision:** Define a minimal system prompt as a constant in a new `apps/agent/src/prompts.py` module. The prompt establishes the agent's role as a knowledgeable expert assistant, sets conversational tone, and instructs to respond in the user's language.

**Alternatives considered:**
- Prompt in environment variable — fragile for multi-line text, hard to version.
- Prompt in database now — premature, S10 is dedicated to this.

**Rationale:** A Python constant is simple, version-controlled, and easily replaceable when S10 introduces DB-based prompts. The module serves as a clear migration point.

### D4: Response persistence via `AgentSession` event

**Decision:** Listen to `agent_speech_committed` event on `AgentSession` to capture the full agent response text after it's been spoken. Persist to the `messages` table reusing the existing `transcript.py` pattern — same `save_transcript` function extended to accept `role` parameter, or a parallel `save_agent_response` function.

**Alternatives considered:**
- Intercept LLM stream tokens and accumulate — complex, error-prone, duplicates what AgentSession already tracks.
- Hook into TTS output — TTS doesn't exist yet (S08), and text accumulation is cleaner at LLM level.

**Rationale:** `AgentSession` emits events when the agent's speech content is finalized. This gives us the complete response text without manual stream accumulation. Fits the existing event-driven pattern in `main.py`.

### D5: LLM settings as environment variables

**Decision:** Add to `AgentSettings`: `LITELLM_URL` (required), `LLM_MODEL` (default: `gemini-flash-lite`), `LLM_TEMPERATURE` (default: `0.7`), `LLM_MAX_TOKENS` (default: `512`). The model name matches what's configured in `litellm.yaml`.

**Rationale:** Consistent with existing pattern (STT settings). Max tokens kept low for voice responses — brief conversational replies, not essays.

### D6: LLM unavailability handling

**Decision:** Set a request timeout (15s) on the OpenAI plugin. On timeout or connection error, the `AgentSession` error handling logs the failure. The agent uses its `Agent` subclass `on_error` or a session-level error handler to inform the user via data channel that the service is temporarily unavailable. No automatic retry at agent level — LiteLLM handles retries internally.

**Rationale:** LiteLLM Proxy already retries and falls back. If even the fallback fails, a 15s timeout prevents the pipeline from hanging indefinitely. The user gets feedback instead of silence.

## Risks / Trade-offs

- **[LiteLLM Proxy latency]** Adding a proxy hop adds ~5-20ms latency per request. → Acceptable for voice pipeline target of ~800ms total. The proxy runs on the same Docker network (near-zero network overhead).

- **[Gemini Flash-Lite streaming support]** Gemini models via LiteLLM may have different streaming behavior than native OpenAI. → LiteLLM normalizes the interface; `livekit-plugins-openai` handles standard SSE streaming. Test with actual API keys during development.

- **[Model name coupling]** Agent requests `gemini-flash-lite` which must match `model_name` in `litellm.yaml`. → Single source of truth in litellm config. Agent setting `LLM_MODEL` allows override without code change.

- **[No TTS yet]** LLM generates text responses but they won't be spoken until S08. → Responses are still delivered via data channel transcript events and persisted to DB. The pipeline is functional for text output.
