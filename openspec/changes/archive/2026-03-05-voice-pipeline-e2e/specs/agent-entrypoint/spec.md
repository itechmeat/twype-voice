## MODIFIED Requirements

### Requirement: Agent settings via environment
The agent SHALL load configuration from environment variables using a pydantic `BaseSettings` class. Settings SHALL include: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LOG_LEVEL` (default: `INFO`), `DEEPGRAM_API_KEY`, `STT_LANGUAGE` (default: `multi`), `STT_MODEL` (default: `nova-3`), `DATABASE_URL`, `LITELLM_URL`, `LITELLM_MASTER_KEY`, `LLM_MODEL` (default: `gemini-flash-lite`), `LLM_TEMPERATURE` (default: `0.7`), `LLM_MAX_TOKENS` (default: `512`), `TTS_PROVIDER` (default: `inworld`), `INWORLD_API_KEY`, `TTS_INWORLD_VOICE` (default: `Olivia`), `TTS_INWORLD_MODEL` (default: `inworld-tts-1.5-mini`), `TTS_SPEAKING_RATE` (default: `1.0`), `TTS_TEMPERATURE` (default: `1.0`), `ELEVENLABS_API_KEY` (optional), `TTS_ELEVENLABS_VOICE_ID` (default: `EXAVITQu4vr4xnSDxMaL`), `TTS_ELEVENLABS_MODEL` (default: `eleven_flash_v2_5`), `TURN_DETECTION_MODE` (default: `stt`), `MIN_ENDPOINTING_DELAY` (default: `0.5`), `MAX_ENDPOINTING_DELAY` (default: `3.0`), `PREEMPTIVE_GENERATION` (default: `True`), `NOISE_CANCELLATION_ENABLED` (default: `True`), `FALSE_INTERRUPTION_TIMEOUT` (default: `2.0`), `MIN_INTERRUPTION_DURATION` (default: `0.5`), `THINKING_SOUNDS_ENABLED` (default: `True`), `THINKING_SOUNDS_DELAY` (default: `1.5`).

#### Scenario: Settings loaded from environment
- **WHEN** the agent starts
- **THEN** settings are loaded from environment variables with documented defaults

#### Scenario: Missing required settings
- **WHEN** required environment variables (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `DEEPGRAM_API_KEY`, `DATABASE_URL`, `LITELLM_URL`, `LITELLM_MASTER_KEY`) are not set
- **THEN** the agent fails to start with a validation error

### Requirement: LLM in AgentSession pipeline
The `AgentSession` SHALL be constructed with VAD, STT, LLM, TTS, and pipeline configuration parameters: `turn_detection` from `TURN_DETECTION_MODE`, `min_endpointing_delay` from `MIN_ENDPOINTING_DELAY`, `max_endpointing_delay` from `MAX_ENDPOINTING_DELAY`, `preemptive_generation` from `PREEMPTIVE_GENERATION`, `false_interruption_timeout` from `FALSE_INTERRUPTION_TIMEOUT`, `min_interruption_duration` from `MIN_INTERRUPTION_DURATION`. When `NOISE_CANCELLATION_ENABLED` is `True`, noise cancellation SHALL be applied to incoming audio. All plugins and noise cancellation SHALL be prewarmed in the `prewarm` function.

#### Scenario: AgentSession includes full pipeline configuration
- **WHEN** the agent creates an `AgentSession` for a room
- **THEN** the session includes VAD, STT, LLM, TTS, and turn detection/endpointing/interruption parameters from settings

#### Scenario: LLM prewarmed at process start
- **WHEN** the agent process prewarms
- **THEN** the LLM plugin is initialized and stored in `proc.userdata`

#### Scenario: TTS prewarmed at process start
- **WHEN** the agent process prewarms
- **THEN** the TTS plugin is initialized and stored in `proc.userdata`

#### Scenario: Noise cancellation prewarmed at process start
- **WHEN** the agent process prewarms and `NOISE_CANCELLATION_ENABLED` is `True`
- **THEN** noise cancellation is initialized and stored in `proc.userdata`
