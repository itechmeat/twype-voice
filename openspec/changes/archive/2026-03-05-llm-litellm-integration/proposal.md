## Why

The agent currently listens and transcribes speech but cannot respond. To close the voice pipeline loop (STT -> LLM -> TTS), the agent needs LLM integration for generating conversational responses. LiteLLM Proxy provides a provider-agnostic OpenAI-compatible gateway, enabling model switching without code changes.

## What Changes

- Configure LiteLLM Proxy with Gemini Flash-Lite as primary model and GPT-4.1-mini as fallback
- Add `livekit-plugins-openai` to the agent, connecting it to LiteLLM Proxy via OpenAI-compatible API
- Add LLM to the `AgentSession` pipeline so the agent generates streaming responses to user speech
- Provide a basic hardcoded system prompt (prompt DB loading deferred to S10)
- Handle LiteLLM unavailability: health check, timeouts, user-facing error message
- Save agent responses to the `messages` table with `role=assistant`, `mode=voice`

## Capabilities

### New Capabilities
- `litellm-proxy-config`: LiteLLM Proxy model configuration — primary model, fallback model, health checks, master key authentication
- `agent-llm-pipeline`: Agent LLM integration via `livekit-plugins-openai` connected to LiteLLM — streaming response generation, basic system prompt, timeout and error handling
- `agent-response-persistence`: Saving agent LLM responses to the `messages` table with role, mode, and content

### Modified Capabilities
- `agent-entrypoint`: Adding LLM to the `AgentSession` pipeline and wiring response persistence

## Impact

- **apps/agent/**: new dependency `livekit-plugins-openai`, new LLM pipeline configuration in agent session, response persistence logic
- **apps/agent/src/settings.py**: new env vars (`LITELLM_URL`, `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`)
- **configs/litellm.yaml**: add GPT-4.1-mini fallback model configuration
- **docker/**: agent container needs network access to `litellm` service
- **.env.example**: new variables for LiteLLM and LLM configuration
- **apps/agent/pyproject.toml**: add `livekit-plugins-openai` dependency
