## ADDED Requirements

### Requirement: STT-based turn detection
The `AgentSession` SHALL use `turn_detection="stt"` mode, relying on Deepgram STT end-of-utterance signals for determining when the user has finished speaking. The mode SHALL be configurable via the `TURN_DETECTION_MODE` environment variable (default: `"stt"`).

#### Scenario: Default turn detection mode
- **WHEN** `TURN_DETECTION_MODE` is not set
- **THEN** the `AgentSession` uses `turn_detection="stt"`

#### Scenario: Custom turn detection mode
- **WHEN** `TURN_DETECTION_MODE` is set to `"vad"`
- **THEN** the `AgentSession` uses `turn_detection="vad"`

#### Scenario: Invalid turn detection mode
- **WHEN** `TURN_DETECTION_MODE` is set to an unsupported value
- **THEN** the agent fails to start with a validation error listing valid modes

### Requirement: Endpointing delay configuration
The `AgentSession` SHALL be configured with `min_endpointing_delay` and `max_endpointing_delay` parameters from environment variables. `MIN_ENDPOINTING_DELAY` (default: `0.5` seconds) controls the minimum pause before declaring end-of-turn. `MAX_ENDPOINTING_DELAY` (default: `3.0` seconds) acts as a safety timeout — the maximum wait before forcing end-of-turn.

#### Scenario: Default endpointing delays
- **WHEN** `MIN_ENDPOINTING_DELAY` and `MAX_ENDPOINTING_DELAY` are not set
- **THEN** the `AgentSession` uses `min_endpointing_delay=0.5` and `max_endpointing_delay=3.0`

#### Scenario: Custom endpointing delays
- **WHEN** `MIN_ENDPOINTING_DELAY=0.3` and `MAX_ENDPOINTING_DELAY=5.0`
- **THEN** the `AgentSession` uses the specified values

#### Scenario: Min endpointing delay validation
- **WHEN** `MIN_ENDPOINTING_DELAY` is set to a negative value
- **THEN** the agent fails to start with a validation error

### Requirement: Preemptive LLM generation
The `AgentSession` SHALL support preemptive generation mode via the `PREEMPTIVE_GENERATION` environment variable (default: `True`). When enabled, the LLM SHALL begin generating a response as soon as a user transcript is received, before end-of-turn is confirmed.

#### Scenario: Preemptive generation enabled by default
- **WHEN** `PREEMPTIVE_GENERATION` is not set
- **THEN** the `AgentSession` is configured with `preemptive_generation=True`

#### Scenario: Preemptive generation disabled
- **WHEN** `PREEMPTIVE_GENERATION=false`
- **THEN** the `AgentSession` is configured with `preemptive_generation=False` and LLM waits for confirmed end-of-turn

### Requirement: False interruption handling
The `AgentSession` SHALL be configured with `false_interruption_timeout` and `resume_false_interruption` parameters. `FALSE_INTERRUPTION_TIMEOUT` (default: `2.0` seconds) controls how long to wait before declaring an interruption as false. When a false interruption is detected, the agent SHALL resume its previous response if `resume_false_interruption` is `True`.

#### Scenario: False interruption detected and resumed
- **WHEN** the user briefly speaks during agent response but produces no recognized words within `FALSE_INTERRUPTION_TIMEOUT`
- **THEN** the agent resumes the interrupted response

#### Scenario: False interruption timeout disabled
- **WHEN** `FALSE_INTERRUPTION_TIMEOUT` is set to `0`
- **THEN** false interruption detection is disabled (timeout set to `None`)

### Requirement: Interruption duration threshold
The `AgentSession` SHALL be configured with `MIN_INTERRUPTION_DURATION` (default: `0.5` seconds). Speech shorter than this threshold SHALL NOT be treated as an interruption.

#### Scenario: Short noise does not interrupt
- **WHEN** a speech segment shorter than `MIN_INTERRUPTION_DURATION` is detected during agent response
- **THEN** the agent continues speaking without interruption

#### Scenario: Valid interruption exceeds threshold
- **WHEN** a speech segment longer than `MIN_INTERRUPTION_DURATION` is detected during agent response
- **THEN** the agent stops speaking and begins processing the new input

### Requirement: Noise cancellation
The agent SHALL apply noise cancellation to incoming audio using the `livekit-plugins-noise-cancellation` package. Noise cancellation SHALL be configurable via `NOISE_CANCELLATION_ENABLED` (default: `True`). The noise cancellation plugin SHALL be added as a dependency in `apps/agent/pyproject.toml`.

#### Scenario: Noise cancellation enabled by default
- **WHEN** `NOISE_CANCELLATION_ENABLED` is not set or is `True`
- **THEN** incoming audio is processed through noise cancellation before reaching VAD and STT

#### Scenario: Noise cancellation disabled
- **WHEN** `NOISE_CANCELLATION_ENABLED=false`
- **THEN** incoming audio passes directly to VAD and STT without noise cancellation

#### Scenario: Noise cancellation dependency
- **WHEN** agent dependencies are installed via `uv sync`
- **THEN** `livekit-plugins-noise-cancellation` is available

### Requirement: Turn detection settings in AgentSettings
The `AgentSettings` class SHALL include turn detection and pipeline configuration fields: `TURN_DETECTION_MODE` (Literal `"stt"`, `"vad"`, `"manual"`, default: `"stt"`), `MIN_ENDPOINTING_DELAY` (float, default: `0.5`, ge: `0.0`), `MAX_ENDPOINTING_DELAY` (float, default: `3.0`, gt: `0.0`), `PREEMPTIVE_GENERATION` (bool, default: `True`), `NOISE_CANCELLATION_ENABLED` (bool, default: `True`), `FALSE_INTERRUPTION_TIMEOUT` (float, default: `2.0`, ge: `0.0`), `MIN_INTERRUPTION_DURATION` (float, default: `0.5`, ge: `0.0`).

#### Scenario: All turn detection settings loaded with defaults
- **WHEN** no turn detection environment variables are set
- **THEN** settings use documented defaults: `TURN_DETECTION_MODE="stt"`, `MIN_ENDPOINTING_DELAY=0.5`, `MAX_ENDPOINTING_DELAY=3.0`, `PREEMPTIVE_GENERATION=True`, `NOISE_CANCELLATION_ENABLED=True`, `FALSE_INTERRUPTION_TIMEOUT=2.0`, `MIN_INTERRUPTION_DURATION=0.5`

#### Scenario: Settings documented in .env.example
- **WHEN** a developer copies `.env.example` to `.env`
- **THEN** all turn detection and pipeline variables are present with descriptive comments and defaults
