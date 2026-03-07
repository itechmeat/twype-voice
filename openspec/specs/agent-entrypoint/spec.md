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
The agent SHALL load configuration from environment variables using a pydantic `BaseSettings` class. Settings SHALL include all existing settings plus: `PROACTIVE_ENABLED` (bool, default: `True`), `PROACTIVE_SHORT_TIMEOUT` (float, default: `15.0`, ge=1.0), `PROACTIVE_LONG_TIMEOUT` (float, default: `45.0`, ge=1.0).

#### Scenario: Settings loaded from environment
- **WHEN** the agent starts
- **THEN** settings are loaded from environment variables with documented defaults, including proactive settings

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

### Requirement: Silence timer lifecycle wiring
The agent entrypoint SHALL create a `SilenceTimer` instance when `PROACTIVE_ENABLED` is `True`. The timer SHALL be wired to the following events:
- `agent_speech_committed`: start or reset the timer
- `user_input_transcribed` (any, including interim): reset the timer
- `data_received` (valid chat message): reset the timer
- `user_state_changed` to `"speaking"`: reset the timer
- `participant_disconnected`: stop the timer

#### Scenario: Timer starts after agent speaks
- **WHEN** the agent finishes speaking (`agent_speech_committed` fires)
- **THEN** the silence timer starts (or resets if already running)

#### Scenario: Timer resets on user voice input
- **WHEN** the user starts speaking (interim transcript received)
- **THEN** the silence timer resets to zero

#### Scenario: Timer resets on text input
- **WHEN** the user sends a text message via data channel
- **THEN** the silence timer resets to zero

#### Scenario: Timer resets on VAD speech start
- **WHEN** `user_state_changed` fires with `new_state="speaking"`
- **THEN** the silence timer resets to zero

#### Scenario: Timer stops on participant disconnect
- **WHEN** the linked participant disconnects
- **THEN** the silence timer stops and no further proactive utterances fire

### Requirement: Proactive prompt rendering
The entrypoint SHALL render the `proactive_prompt` layer from the prompt bundle as a template using `str.format_map()` with `{proactive_type}` and `{emotional_context}` placeholders. The `proactive_type` SHALL be `"follow_up"` for short timeout and `"extended_silence"` for long timeout. The `emotional_context` SHALL be a human-readable summary of the current emotional state (quadrant + trend) or `"neutral"` if no emotional state is available.

#### Scenario: Proactive prompt rendered with emotional context
- **WHEN** the short timeout fires and the current emotional state is `distress` with `trend_valence=falling`
- **THEN** the rendered proactive prompt includes `proactive_type=follow_up` and an emotional context string describing the distress state

#### Scenario: Proactive prompt rendered without emotional state
- **WHEN** the short timeout fires and no emotional state is available
- **THEN** the rendered proactive prompt includes `proactive_type=follow_up` and `emotional_context="neutral"`
