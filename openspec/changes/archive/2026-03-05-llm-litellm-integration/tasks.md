## 1. LiteLLM Proxy Configuration

- [x] 1.1 Add GPT-4.1-mini fallback model to `configs/litellm.yaml` with `fallbacks` router setting
- [x] 1.2 Verify LiteLLM health check works with both models configured

## 2. Agent Dependencies and Settings

- [x] 2.1 Add `livekit-plugins-openai` to `apps/agent/pyproject.toml` and run `uv lock`
- [x] 2.2 Add `LITELLM_URL`, `LITELLM_MASTER_KEY`, `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS` to `AgentSettings` in `settings.py`
- [x] 2.3 Update `.env.example` with new LLM-related variables (`LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`)

## 3. LLM Plugin and System Prompt

- [x] 3.1 Create `apps/agent/src/llm.py` — `build_llm(settings)` function that returns `openai.LLM` configured with `base_url`, `api_key`, `model`, `temperature`
- [x] 3.2 Create `apps/agent/src/prompts.py` — hardcoded system prompt constant defining agent persona, conversational tone, language matching, brief responses
- [x] 3.3 Update `TwypeAgent` in `agent.py` to use the system prompt from `prompts.py` as `instructions`

## 4. Pipeline Integration

- [x] 4.1 Add LLM to `build_session()` in `agent.py`: `AgentSession(vad=..., stt=..., llm=...)`
- [x] 4.2 Add LLM prewarming in `prewarm()` in `main.py` — build and store LLM in `proc.userdata`
- [x] 4.3 Wire prewarmed LLM into `build_session()` call in `build_entrypoint()`

## 5. Response Persistence

- [x] 5.1 Add `save_agent_response(session_id, text)` function to `transcript.py` — inserts `messages` row with `role=assistant`, `mode=voice`
- [x] 5.2 Register `conversation_item_added` event handler in `build_entrypoint()` — captures response text and calls persistence
- [x] 5.3 Publish finalized agent response via data channel (reuse `publish_transcript` with `role=assistant`)

## 6. Error Handling

- [x] 6.1 Configure LLM request timeout (15s) in `build_llm()`
- [x] 6.2 Add LLM error/timeout notification — send error message to user via data channel
- [x] 6.3 Verify agent continues processing after LLM failure (does not crash)

## 7. Tests

- [x] 7.1 Unit tests for `build_llm()` — correct `base_url`, `api_key`, model, temperature
- [x] 7.2 Unit tests for `AgentSettings` — new LLM fields validation, defaults, required fields
- [x] 7.3 Unit tests for `save_agent_response()` — persistence, empty text handling, DB failure resilience
- [x] 7.4 Unit test for system prompt — verify prompt is non-empty and used in `TwypeAgent`
