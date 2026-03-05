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
The agent SHALL load configuration from environment variables using a pydantic `BaseSettings` class. Settings SHALL include: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and `LOG_LEVEL` (default: `INFO`).

#### Scenario: Settings loaded from environment
- **WHEN** the agent starts
- **THEN** settings are loaded from environment variables with documented defaults

#### Scenario: Missing required settings
- **WHEN** required environment variables (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`) are not set
- **THEN** the agent fails to start with a validation error

### Requirement: CLI entry point
The agent SHALL use `livekit-agents` CLI via `cli.run_app(WorkerOptions(...))` supporting `dev`, `start`, and `download-files` modes. The entry point SHALL be `apps/agent/src/main.py`.

#### Scenario: Dev mode
- **WHEN** the agent is started with `python src/main.py dev`
- **THEN** the agent runs with DEBUG logging and auto-reload

#### Scenario: Start mode
- **WHEN** the agent is started with `python src/main.py start`
- **THEN** the agent runs in production mode with INFO logging and graceful shutdown
