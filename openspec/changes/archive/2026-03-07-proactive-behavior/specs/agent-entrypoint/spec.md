## MODIFIED Requirements

### Requirement: Agent settings via environment
The agent SHALL load configuration from environment variables using a pydantic `BaseSettings` class. Settings SHALL include all existing settings plus: `PROACTIVE_ENABLED` (bool, default: `True`), `PROACTIVE_SHORT_TIMEOUT` (float, default: `15.0`, ge=1.0), `PROACTIVE_LONG_TIMEOUT` (float, default: `45.0`, ge=1.0).

#### Scenario: Settings loaded from environment
- **WHEN** the agent starts
- **THEN** settings are loaded from environment variables with documented defaults, including proactive settings

#### Scenario: Missing required settings
- **WHEN** required environment variables (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `DEEPGRAM_API_KEY`, `DATABASE_URL`, `LITELLM_URL`, `LITELLM_MASTER_KEY`) are not set
- **THEN** the agent fails to start with a validation error

## ADDED Requirements

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
