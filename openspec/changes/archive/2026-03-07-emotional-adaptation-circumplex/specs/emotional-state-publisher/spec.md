## ADDED Requirements

### Requirement: Publish emotional state via data channel
The agent SHALL publish an `emotional_state` message to the LiveKit room data channel after each emotional analysis completes for a user utterance. The message SHALL use reliable delivery.

#### Scenario: Emotional state published after voice transcript
- **WHEN** a user voice transcript is analyzed and an EmotionalState is produced
- **THEN** the agent publishes a JSON message with `type: "emotional_state"` via data channel with reliable delivery

#### Scenario: Emotional state published after text message
- **WHEN** a user text message is analyzed and an EmotionalState is produced
- **THEN** the agent publishes a JSON message with `type: "emotional_state"` via data channel with reliable delivery

### Requirement: Emotional state message format
The published JSON message SHALL contain: `type` ("emotional_state"), `quadrant` (string), `valence` (float), `arousal` (float), `trend_valence` (string), `trend_arousal` (string), and `message_id` (string UUID of the user message that triggered the analysis).

#### Scenario: Message format validation
- **WHEN** an emotional state message is published
- **THEN** the JSON payload contains all required fields with correct types

#### Scenario: Message references the triggering user message
- **WHEN** the emotional analysis was triggered by a user message with id "abc-123"
- **THEN** the published message has `message_id: "abc-123"`

### Requirement: Emotional state not published when analysis is unavailable
The agent SHALL NOT publish an emotional state message when the emotional analyzer produces no result (e.g., empty transcript, analyzer disabled).

#### Scenario: Empty transcript skips emotional state
- **WHEN** the user transcript is empty and no emotional analysis is performed
- **THEN** no `emotional_state` message is published

### Requirement: Publish function in datachannel module
The `datachannel` module SHALL provide a `publish_emotional_state` function that accepts the LiveKit room, an `EmotionalState` object, and a `message_id`, serializes them to JSON, and publishes to the data channel.

#### Scenario: Function signature and serialization
- **WHEN** `publish_emotional_state` is called with a room, EmotionalState, and message_id
- **THEN** it publishes a JSON-encoded message with all EmotionalState fields plus the message_id
