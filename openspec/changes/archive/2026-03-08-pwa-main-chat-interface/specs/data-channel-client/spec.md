## ADDED Requirements

### Requirement: Data channel message dispatcher
The system SHALL provide a `useDataChannel` hook that listens to the LiveKit room's `RoomEvent.DataReceived` event, parses incoming data as JSON, and dispatches messages by their `type` field to registered handler callbacks.

#### Scenario: Known message type dispatched
- **WHEN** a data channel message with `type: "chat_response"` is received
- **THEN** the dispatcher SHALL call the registered handler for `chat_response` with the parsed message

#### Scenario: Unknown message type ignored
- **WHEN** a data channel message with an unrecognized `type` is received
- **THEN** the dispatcher SHALL ignore it without errors

#### Scenario: Malformed JSON ignored
- **WHEN** a data channel message that is not valid JSON is received
- **THEN** the dispatcher SHALL log a warning and ignore the message

#### Scenario: Own messages ignored
- **WHEN** a data channel message originates from the local participant
- **THEN** the dispatcher SHALL NOT process it

### Requirement: Handle chat_response messages
The system SHALL handle incoming `chat_response` messages. Interim chunks (`is_final: false`) SHALL update a streaming response indicator. The final message (`is_final: true`) SHALL be added to the message list as a complete agent message.

#### Scenario: Interim chat_response received
- **WHEN** a `chat_response` with `is_final: false` is received
- **THEN** the system SHALL display the partial text in a streaming indicator area

#### Scenario: Final chat_response received
- **WHEN** a `chat_response` with `is_final: true` is received
- **THEN** the system SHALL add the complete text as an agent message to the chat feed and clear the streaming indicator

### Requirement: Handle structured_response messages
The system SHALL handle incoming `structured_response` messages. The final message (`is_final: true`) SHALL be added to the message list as a structured agent message containing an array of items with `text` and `chunk_ids`.

#### Scenario: Final structured_response received
- **WHEN** a `structured_response` with `is_final: true` is received
- **THEN** the system SHALL add the structured items as an agent message to the chat feed

#### Scenario: Interim structured_response received
- **WHEN** a `structured_response` with `is_final: false` is received
- **THEN** the system SHALL display a streaming indicator for the structured response

### Requirement: Handle transcript messages
The system SHALL handle incoming `transcript` messages from the agent's STT pipeline. These represent the user's speech as recognized by the agent. The system SHALL distinguish between interim and final transcripts.

#### Scenario: Interim transcript received
- **WHEN** a transcript message with `is_final: false` is received
- **THEN** the system SHALL update the interim transcript display area

#### Scenario: Final transcript received
- **WHEN** a transcript message with `is_final: true` is received
- **THEN** the system SHALL add the transcript as a finalized user voice message in the chat feed

### Requirement: Handle emotional_state messages
The system SHALL receive `emotional_state` messages and store the latest state in component state. The emotional state SHALL NOT be rendered in S22 but SHALL be available for future use.

#### Scenario: Emotional state received
- **WHEN** an `emotional_state` message is received
- **THEN** the system SHALL store the quadrant, valence, and arousal values in state

#### Scenario: Emotional state not rendered
- **WHEN** an emotional state is stored
- **THEN** no UI element SHALL render the emotional state in this story

### Requirement: Send data channel messages
The system SHALL provide a `useSendDataChannel` hook that returns a `send(type, payload)` function. The function SHALL serialize the message as JSON and publish it to the LiveKit room's data channel with reliable delivery.

#### Scenario: Send chat_message
- **WHEN** `send("chat_message", { text: "Hello" })` is called
- **THEN** the system SHALL publish `{"type": "chat_message", "text": "Hello"}` to the data channel with reliable delivery

#### Scenario: Send when disconnected
- **WHEN** `send` is called while the room is not connected
- **THEN** the function SHALL not throw but SHALL log a warning and discard the message
