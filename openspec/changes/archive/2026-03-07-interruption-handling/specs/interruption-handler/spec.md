## ADDED Requirements

### Requirement: Interruption detection and LLM/TTS cancellation
When the user begins speaking while the agent is actively generating or playing a response, the system SHALL immediately cancel the in-flight LLM token stream and stop TTS audio output. The pipeline SHALL then switch to receiving and processing the new user input.

#### Scenario: User interrupts during agent TTS playback
- **WHEN** the agent is playing TTS audio and the user speaks for longer than `MIN_INTERRUPTION_DURATION`
- **THEN** the agent stops TTS playback and cancels the active LLM generation task within 200ms of interruption detection

#### Scenario: User interrupts during LLM streaming (before TTS starts)
- **WHEN** the agent is streaming LLM tokens but TTS has not yet begun playback and the user speaks for longer than `MIN_INTERRUPTION_DURATION`
- **THEN** the agent cancels the LLM generation task and does not start TTS for the cancelled response

#### Scenario: Pipeline switches to new input after interruption
- **WHEN** a valid interruption cancels the agent's response
- **THEN** the agent processes the user's new speech through the full pipeline (STT -> LLM -> TTS) as a new turn

### Requirement: False interruption recovery
When VAD detects speech during the agent's response but STT produces no recognized words within `FALSE_INTERRUPTION_TIMEOUT`, the system SHALL treat this as a false interruption and resume the agent's previous response.

#### Scenario: No words recognized after interruption
- **WHEN** the user triggers an interruption (speech >= `MIN_INTERRUPTION_DURATION`) but STT produces no final transcript within `FALSE_INTERRUPTION_TIMEOUT` (default: 2.0s)
- **THEN** the agent resumes its interrupted response from the point where it was cut off

#### Scenario: Resume uses buffered TTS audio
- **WHEN** a false interruption is detected and the TTS buffer still contains unplayed audio
- **THEN** the agent replays the buffered TTS audio without re-invoking the LLM

#### Scenario: Resume regenerates continuation when buffer is exhausted
- **WHEN** a false interruption is detected but the TTS buffer has been fully flushed
- **THEN** the agent sends a continuation prompt to the LLM requesting a brief completion (1-2 sentences) of the interrupted response and plays the resulting TTS audio

### Requirement: Interruption lifecycle events on data channel
The system SHALL publish JSON messages over the LiveKit data channel to notify the client about interruption state changes.

#### Scenario: Interruption started event
- **WHEN** a valid interruption is detected (user speech cancels agent response)
- **THEN** the system publishes `{"type": "interruption_started"}` on the data channel

#### Scenario: Interruption resolved with new input
- **WHEN** an interruption is followed by a recognized user transcript (real interruption)
- **THEN** the system publishes `{"type": "interruption_resolved", "resumed": false}` on the data channel

#### Scenario: False interruption event
- **WHEN** a false interruption is detected and the agent resumes its previous response
- **THEN** the system publishes `{"type": "interruption_false", "resumed": true}` on the data channel

### Requirement: Interruption logging and observability
The system SHALL log all interruption events at appropriate log levels for debugging and monitoring.

#### Scenario: Interruption events are logged
- **WHEN** any interruption event occurs (started, resolved, or false)
- **THEN** the system logs the event at INFO level with room ID, participant ID, and event type

#### Scenario: LLM cancellation is logged
- **WHEN** an LLM generation task is cancelled due to interruption
- **THEN** the system logs at DEBUG level including the number of tokens generated before cancellation
