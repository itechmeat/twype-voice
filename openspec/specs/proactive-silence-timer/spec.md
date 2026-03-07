## ADDED Requirements

### Requirement: SilenceTimer class with two-stage escalation
The agent SHALL provide a `SilenceTimer` class in `apps/agent/src/silence_timer.py` that manages an async timer with two escalation stages. The timer SHALL accept `short_timeout` (float, seconds), `long_timeout` (float, seconds), and two async callbacks: `on_short_timeout` and `on_long_timeout`. The timer SHALL be started via `start()`, reset via `reset()`, and stopped via `stop()`. The timer SHALL use a single `asyncio.Task` internally.

#### Scenario: Timer fires short callback after short timeout
- **WHEN** the timer is started and no activity occurs for `short_timeout` seconds
- **THEN** the `on_short_timeout` callback is invoked exactly once

#### Scenario: Timer fires long callback after long timeout
- **WHEN** the timer is started and no activity occurs for `long_timeout` seconds
- **THEN** the `on_long_timeout` callback is invoked exactly once, after `on_short_timeout` has already fired

#### Scenario: Timer reset cancels pending callbacks
- **WHEN** the timer is running and `reset()` is called before `short_timeout` elapses
- **THEN** the pending timer task is cancelled and a new timer cycle begins from zero

#### Scenario: Timer reset after short callback but before long
- **WHEN** `on_short_timeout` has fired but `on_long_timeout` has not, and `reset()` is called
- **THEN** the long callback is cancelled and a new timer cycle begins from zero

### Requirement: Single-fire guard per silence period
The timer SHALL fire at most one proactive utterance per silence period. After either callback fires successfully, the timer SHALL enter a "fired" state. While in the fired state, the timer SHALL NOT fire any further callbacks. The fired state SHALL clear only when `reset()` is called.

#### Scenario: No duplicate proactive utterances
- **WHEN** the short callback has fired and the timer remains running
- **THEN** only the long callback may fire next; no second short callback occurs

#### Scenario: Guard prevents callbacks after long timeout fired
- **WHEN** both short and long callbacks have fired
- **THEN** no further callbacks execute until `reset()` is called

#### Scenario: Reset clears the fired guard
- **WHEN** the timer is in a "fired" state and `reset()` is called
- **THEN** the fired state clears and the timer begins a fresh cycle

### Requirement: Timer stop on lifecycle events
The timer SHALL expose a `stop()` method that cancels any pending timer task and prevents further callbacks. After `stop()`, the timer SHALL NOT fire any callbacks until `start()` is called again.

#### Scenario: Stop cancels all pending callbacks
- **WHEN** `stop()` is called while the timer is running
- **THEN** no callbacks fire and the internal task is cancelled

#### Scenario: Stop is idempotent
- **WHEN** `stop()` is called on an already stopped timer
- **THEN** no error occurs

### Requirement: Proactive utterance generation via LLM
When a silence timeout fires, the agent SHALL generate a proactive utterance by calling `session.generate_reply` with a synthetic user message. The message SHALL include the proactive type (`follow_up` for short timeout, `extended_silence` for long timeout). The rendered `proactive_prompt` template SHALL be injected as additional context. The utterance SHALL go through the full agent pipeline (LLM -> TTS -> WebRTC for voice mode, LLM -> data channel for text mode).

#### Scenario: Short timeout generates follow-up question
- **WHEN** the short timeout fires during a voice session
- **THEN** the agent generates a context-aware follow-up question via the LLM pipeline and speaks it to the user

#### Scenario: Long timeout generates gentle nudge with emotional context
- **WHEN** the long timeout fires and the user's emotional state is `melancholy`
- **THEN** the agent generates a warm, gentle check-in utterance adapted to the emotional state

#### Scenario: Proactive utterance in text mode
- **WHEN** the short timeout fires during a text session
- **THEN** the agent generates a follow-up question and sends it via the data channel (not TTS)

### Requirement: Data channel proactive nudge notification
The agent SHALL publish a `proactive_nudge` data channel message when a proactive utterance is initiated. The message SHALL contain `{"type": "proactive_nudge", "proactive_type": "follow_up"|"extended_silence"}` and SHALL be sent with `reliable=True`.

#### Scenario: Proactive nudge published on short timeout
- **WHEN** the short timeout fires and a proactive utterance is initiated
- **THEN** a `proactive_nudge` message with `proactive_type="follow_up"` is published via the data channel

#### Scenario: Proactive nudge published on long timeout
- **WHEN** the long timeout fires and a proactive utterance is initiated
- **THEN** a `proactive_nudge` message with `proactive_type="extended_silence"` is published via the data channel

### Requirement: Configurable timeouts via settings
The agent settings SHALL include `PROACTIVE_ENABLED` (bool, default `True`), `PROACTIVE_SHORT_TIMEOUT` (float, default `15.0`, seconds), and `PROACTIVE_LONG_TIMEOUT` (float, default `45.0`, seconds). When `PROACTIVE_ENABLED` is `False`, no silence timer SHALL be created.

#### Scenario: Default proactive settings
- **WHEN** the agent starts without proactive-related environment variables
- **THEN** `PROACTIVE_ENABLED` is `True`, `PROACTIVE_SHORT_TIMEOUT` is `15.0`, and `PROACTIVE_LONG_TIMEOUT` is `45.0`

#### Scenario: Proactive disabled
- **WHEN** `PROACTIVE_ENABLED=false` is set in the environment
- **THEN** no silence timer is created and no proactive behavior occurs

#### Scenario: Custom timeouts
- **WHEN** `PROACTIVE_SHORT_TIMEOUT=10` and `PROACTIVE_LONG_TIMEOUT=30` are set
- **THEN** the timer uses 10 and 30 seconds respectively
