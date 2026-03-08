## ADDED Requirements

### Requirement: Unified message list
The system SHALL render a scrollable message list displaying all messages from the current session in chronological order. Each message SHALL show the content text and a visual distinction between user messages and agent messages (e.g., alignment or color).

#### Scenario: User voice message displayed
- **WHEN** a final voice transcript is received from the agent via data channel (`type: "transcript"`)
- **THEN** the message list SHALL display the transcript text as a user message

#### Scenario: User text message displayed
- **WHEN** the user sends a text message via the text input
- **THEN** the message list SHALL display the sent text as a user message immediately (optimistic)

#### Scenario: Agent plain response displayed
- **WHEN** a `chat_response` message with `is_final: true` is received via data channel
- **THEN** the message list SHALL display the response text as an agent message

#### Scenario: Agent structured response displayed
- **WHEN** a `structured_response` message with `is_final: true` is received via data channel
- **THEN** the message list SHALL display the structured items as an agent message with each item as a separate line or paragraph

### Requirement: Auto-scroll to latest message
The system SHALL automatically scroll the message list to the bottom when a new message is added, unless the user has manually scrolled up to review previous messages.

#### Scenario: New message while at bottom
- **WHEN** a new message is added and the user is scrolled to the bottom of the list
- **THEN** the list SHALL auto-scroll to show the new message

#### Scenario: New message while scrolled up
- **WHEN** a new message is added and the user has scrolled up
- **THEN** the list SHALL NOT auto-scroll and SHALL show an indicator that new messages are available

### Requirement: Interim transcript display
The system SHALL display interim (non-final) voice transcripts from the agent's STT in real time. Interim transcripts SHALL appear in a visually distinct style (e.g., lighter text, italic) and SHALL be replaced by the final transcript when it arrives.

#### Scenario: Interim transcript shown
- **WHEN** an interim transcript data channel message is received
- **THEN** the system SHALL display the interim text in a distinguished style at the bottom of the message list

#### Scenario: Interim replaced by final
- **WHEN** a final transcript arrives after interim transcripts
- **THEN** the interim display SHALL be replaced by the final message in the message list

#### Scenario: No interim when not speaking
- **WHEN** no interim transcript messages are being received
- **THEN** no interim transcript area SHALL be visible

### Requirement: Agent state indicator
The system SHALL display the current agent state as a visual indicator near the message feed. The states SHALL include: `listening` (agent is waiting for input), `thinking` (agent is processing/generating), `speaking` (agent is producing audio). The state SHALL be derived from the agent participant's attributes published by the LiveKit Agents SDK.

#### Scenario: Agent listening
- **WHEN** the agent participant's state attribute indicates "listening"
- **THEN** the system SHALL display a "listening" indicator

#### Scenario: Agent thinking
- **WHEN** the agent participant's state attribute indicates "thinking"
- **THEN** the system SHALL display a "thinking" indicator

#### Scenario: Agent speaking
- **WHEN** the agent participant's state attribute indicates "speaking"
- **THEN** the system SHALL display a "speaking" indicator

### Requirement: Message mode label
Each message in the feed SHALL display a mode indicator showing whether it originated from voice or text input. The mode SHALL be determined by the current input mode at the time the message was created.

#### Scenario: Voice message label
- **WHEN** a message originated from voice input
- **THEN** the message SHALL display a voice mode indicator (e.g., microphone icon or "voice" label)

#### Scenario: Text message label
- **WHEN** a message originated from text input
- **THEN** the message SHALL display a text mode indicator (e.g., keyboard icon or "text" label)

### Requirement: Structured response rendering
When a `structured_response` message is received, the system SHALL render each item in the `items` array as a separate block. Each item SHALL display its `text` content. Items with non-empty `chunk_ids` arrays SHALL display a source indicator placeholder (the full source attribution UI is deferred to S23).

#### Scenario: Items rendered as blocks
- **WHEN** a `structured_response` with 3 items is received
- **THEN** the message list SHALL render 3 distinct content blocks within one agent message

#### Scenario: Item with chunk_ids shows source placeholder
- **WHEN** an item has `chunk_ids: ["uuid-1", "uuid-2"]`
- **THEN** the item SHALL display a source indicator (e.g., a small icon or badge) that will be made interactive in S23

#### Scenario: Item without chunk_ids shows no source indicator
- **WHEN** an item has `chunk_ids: []`
- **THEN** no source indicator SHALL be displayed for that item
