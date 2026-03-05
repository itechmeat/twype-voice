## MODIFIED Requirements

### Requirement: Agent settings via environment
The agent SHALL load configuration from environment variables using a pydantic `BaseSettings` class. Settings SHALL include: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LOG_LEVEL` (default: `INFO`), `DEEPGRAM_API_KEY`, `STT_LANGUAGE` (default: `multi`), `STT_MODEL` (default: `nova-3`), `DATABASE_URL`, `LITELLM_URL`, `LITELLM_MASTER_KEY`, `LLM_MODEL` (default: `gemini-flash-lite`), `LLM_TEMPERATURE` (default: `0.7`), and `LLM_MAX_TOKENS` (default: `512`).

#### Scenario: Settings loaded from environment
- **WHEN** the agent starts
- **THEN** settings are loaded from environment variables with documented defaults

#### Scenario: Missing required settings
- **WHEN** required environment variables (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `DEEPGRAM_API_KEY`, `DATABASE_URL`, `LITELLM_URL`, `LITELLM_MASTER_KEY`) are not set
- **THEN** the agent fails to start with a validation error

## ADDED Requirements

### Requirement: LLM in AgentSession pipeline
The `AgentSession` SHALL be constructed with an LLM plugin in addition to VAD and STT: `AgentSession(vad=..., stt=..., llm=...)`. The LLM plugin SHALL be prewarmed alongside VAD and STT in the `prewarm` function.

#### Scenario: AgentSession includes LLM
- **WHEN** the agent creates an `AgentSession` for a room
- **THEN** the session includes VAD, STT, and LLM plugins

#### Scenario: LLM prewarmed at process start
- **WHEN** the agent process prewarms
- **THEN** the LLM plugin is initialized and stored in `proc.userdata`

### Requirement: Agent response event handling
The agent entrypoint SHALL register a handler for the `agent_speech_committed` event on `AgentSession`. The handler SHALL trigger response persistence and data channel notification.

#### Scenario: Response event handler registered
- **WHEN** the `AgentSession` starts in a room
- **THEN** the `agent_speech_committed` event handler is registered

#### Scenario: Response event triggers persistence and notification
- **WHEN** the `agent_speech_committed` event fires
- **THEN** the agent persists the response to the database and publishes it via data channel
