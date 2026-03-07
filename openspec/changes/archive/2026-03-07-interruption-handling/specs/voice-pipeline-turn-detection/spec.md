## MODIFIED Requirements

### Requirement: False interruption handling
The `AgentSession` SHALL be configured with `false_interruption_timeout` and `resume_false_interruption` parameters. `FALSE_INTERRUPTION_TIMEOUT` (default: `2.0` seconds) controls how long to wait before declaring an interruption as false. When a false interruption is detected, the agent SHALL resume its previous response if `resume_false_interruption` is `True`. The application layer SHALL subscribe to interruption events emitted by `AgentSession` and execute the following on each interruption: cancel any in-flight LLM generation task, publish the corresponding data channel event (`interruption_started`, `interruption_resolved`, or `interruption_false`), and log the event.

#### Scenario: False interruption detected and resumed
- **WHEN** the user briefly speaks during agent response but produces no recognized words within `FALSE_INTERRUPTION_TIMEOUT`
- **THEN** the agent resumes the interrupted response and publishes `{"type": "interruption_false", "resumed": true}` on the data channel

#### Scenario: False interruption timeout disabled
- **WHEN** `FALSE_INTERRUPTION_TIMEOUT` is set to `0`
- **THEN** false interruption detection is disabled (timeout set to `None`) and any interruption is treated as valid

### Requirement: Interruption duration threshold
The `AgentSession` SHALL be configured with `MIN_INTERRUPTION_DURATION` (default: `0.5` seconds). Speech shorter than this threshold SHALL NOT be treated as an interruption. When speech exceeds this threshold during agent response, the system SHALL cancel the active LLM generation and TTS playback and publish an `interruption_started` data channel event.

#### Scenario: Short noise does not interrupt
- **WHEN** a speech segment shorter than `MIN_INTERRUPTION_DURATION` is detected during agent response
- **THEN** the agent continues speaking without interruption and no data channel event is published

#### Scenario: Valid interruption exceeds threshold
- **WHEN** a speech segment longer than `MIN_INTERRUPTION_DURATION` is detected during agent response
- **THEN** the agent stops speaking, cancels the active LLM generation, begins processing the new input, and publishes `{"type": "interruption_started"}` on the data channel
