## MODIFIED Requirements

### Requirement: LLM in AgentSession pipeline
The `AgentSession` SHALL be constructed with a TTS plugin in addition to VAD, STT, and LLM: `AgentSession(vad=..., stt=..., llm=..., tts=...)`. The TTS plugin SHALL be prewarmed alongside VAD, STT, and LLM in the `prewarm` function.

#### Scenario: AgentSession includes TTS
- **WHEN** the agent creates an `AgentSession` for a room
- **THEN** the session includes VAD, STT, LLM, and TTS plugins

#### Scenario: LLM prewarmed at process start
- **WHEN** the agent process prewarms
- **THEN** the LLM plugin is initialized and stored in `proc.userdata`

#### Scenario: TTS prewarmed at process start
- **WHEN** the agent process prewarms
- **THEN** the TTS plugin is initialized and stored in `proc.userdata`

### Requirement: Agent settings via environment
The agent SHALL load configuration from environment variables using a pydantic `BaseSettings` class. Settings SHALL include: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LOG_LEVEL` (default: `INFO`), `DEEPGRAM_API_KEY`, `STT_LANGUAGE` (default: `multi`), `STT_MODEL` (default: `nova-3`), `DATABASE_URL`, `LITELLM_URL`, `LITELLM_MASTER_KEY`, `LLM_MODEL` (default: `gemini-flash-lite`), `LLM_TEMPERATURE` (default: `0.7`), `LLM_MAX_TOKENS` (default: `512`), `TTS_PROVIDER` (default: `inworld`), `INWORLD_API_KEY`, `TTS_INWORLD_VOICE` (default: `Olivia`), `TTS_INWORLD_MODEL` (default: `inworld-tts-1.5-mini`), `TTS_SPEAKING_RATE` (default: `1.0`), `TTS_TEMPERATURE` (default: `1.0`), `ELEVENLABS_API_KEY` (optional), `TTS_ELEVENLABS_VOICE_ID` (default: `EXAVITQu4vr4xnSDxMaL`), `TTS_ELEVENLABS_MODEL` (default: `eleven_flash_v2_5`).

#### Scenario: Settings loaded from environment
- **WHEN** the agent starts
- **THEN** settings are loaded from environment variables with documented defaults

#### Scenario: Missing required settings
- **WHEN** required environment variables (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `DEEPGRAM_API_KEY`, `DATABASE_URL`, `LITELLM_URL`, `LITELLM_MASTER_KEY`) are not set
- **THEN** the agent fails to start with a validation error
