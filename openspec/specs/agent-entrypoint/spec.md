## ADDED Requirements

### Requirement: Agent worker registration
The agent process SHALL register with LiveKit Server using `WorkerOptions` and credentials from environment variables (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`). The agent SHALL use automatic dispatch (no `agent_name` set) so that every new room receives an agent.

#### Scenario: Agent starts and registers with LiveKit Server
- **WHEN** the agent process starts with `dev` or `start` CLI mode
- **THEN** the agent registers with LiveKit Server and logs a confirmation message

#### Scenario: Agent fails to connect to LiveKit Server
- **WHEN** LiveKit Server is unreachable or credentials are invalid
- **THEN** the agent process SHALL exit with a non-zero exit code and log the error

### Requirement: Job acceptance and room connection
The agent SHALL accept job requests from LiveKit Server and connect to the assigned room as a participant. The agent SHALL subscribe to audio tracks only (`AutoSubscribe.AUDIO_ONLY`).

#### Scenario: New room created triggers job dispatch
- **WHEN** a new LiveKit room is created (via API session start)
- **THEN** the agent accepts the job and connects to the room as a participant

#### Scenario: Agent subscribes to audio only
- **WHEN** the agent connects to a room
- **THEN** the agent subscribes to audio tracks only, not video

### Requirement: Participant lifecycle handling
The agent SHALL wait for the first human participant to join the room. The agent SHALL use `AgentSession` to manage participant linking and audio subscription automatically.

#### Scenario: Human participant joins the room
- **WHEN** a human participant connects to the room
- **THEN** the agent links to that participant and begins receiving their audio stream

#### Scenario: Participant disconnects
- **WHEN** the linked participant disconnects from the room
- **THEN** the agent logs the disconnection event

### Requirement: Structured logging
The agent SHALL log room lifecycle events using Python's `logging` module with the logger name `twype-agent`. Events SHALL include: job accepted, room connected, participant joined, participant left, agent shutdown.

#### Scenario: Lifecycle events are logged
- **WHEN** a room lifecycle event occurs (job accept, connect, participant join/leave, shutdown)
- **THEN** the event is logged at INFO level with the room name and participant identity

### Requirement: Agent settings via environment
The agent SHALL load configuration from environment variables using a pydantic `BaseSettings` class. Settings SHALL include: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LOG_LEVEL` (default: `INFO`), `DEEPGRAM_API_KEY`, `STT_LANGUAGE` (default: `multi`), `STT_MODEL` (default: `nova-3`), `DATABASE_URL`, `LITELLM_URL`, `LITELLM_MASTER_KEY`, `LLM_MODEL` (default: `gemini-flash-lite`), `LLM_TEMPERATURE` (default: `0.7`), `LLM_MAX_TOKENS` (default: `512`), `TTS_PROVIDER` (default: `inworld`), `INWORLD_API_KEY`, `TTS_INWORLD_VOICE` (default: `Olivia`), `TTS_INWORLD_MODEL` (default: `inworld-tts-1.5-mini`), `TTS_SPEAKING_RATE` (default: `1.0`), `TTS_TEMPERATURE` (default: `1.0`), `ELEVENLABS_API_KEY` (optional), `TTS_ELEVENLABS_VOICE_ID` (default: `EXAVITQu4vr4xnSDxMaL`), `TTS_ELEVENLABS_MODEL` (default: `eleven_flash_v2_5`), `TURN_DETECTION_MODE` (default: `stt`), `MIN_ENDPOINTING_DELAY` (default: `0.5`), `MAX_ENDPOINTING_DELAY` (default: `3.0`), `PREEMPTIVE_GENERATION` (default: `True`), `NOISE_CANCELLATION_ENABLED` (default: `True`), `FALSE_INTERRUPTION_TIMEOUT` (default: `2.0`), `MIN_INTERRUPTION_DURATION` (default: `0.5`), `THINKING_SOUNDS_ENABLED` (default: `True`), `THINKING_SOUNDS_DELAY` (default: `1.5`).

#### Scenario: Settings loaded from environment
- **WHEN** the agent starts
- **THEN** settings are loaded from environment variables with documented defaults

#### Scenario: Missing required settings
- **WHEN** required environment variables (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `DEEPGRAM_API_KEY`, `DATABASE_URL`, `LITELLM_URL`, `LITELLM_MASTER_KEY`) are not set
- **THEN** the agent fails to start with a validation error

### Requirement: CLI entry point
The agent SHALL use `livekit-agents` CLI via `cli.run_app(WorkerOptions(...))` supporting `dev`, `start`, and `download-files` modes. The entry point SHALL be `apps/agent/src/main.py`.

#### Scenario: Dev mode
- **WHEN** the agent is started with `python src/main.py dev`
- **THEN** the agent runs with DEBUG logging and auto-reload

#### Scenario: Start mode
- **WHEN** the agent is started with `python src/main.py start`
- **THEN** the agent runs in production mode with INFO logging and graceful shutdown

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

### Requirement: Agent response event handling
The agent entrypoint SHALL register a handler for the `conversation_item_added` event on `AgentSession`. The handler SHALL trigger response persistence and data channel notification.

#### Scenario: Response event handler registered
- **WHEN** the `AgentSession` starts in a room
- **THEN** the `conversation_item_added` event handler is registered

#### Scenario: Response event triggers persistence and notification
- **WHEN** the `conversation_item_added` event fires with an assistant message
- **THEN** the agent persists the response to the database and publishes it via data channel
