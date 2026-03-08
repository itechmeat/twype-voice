## ADDED Requirements

### Requirement: Text input field
The system SHALL render a text input field at the bottom of the chat interface. The field SHALL accept multi-line text. The user SHALL be able to submit the message by pressing Enter (without Shift) or by clicking a send button.

#### Scenario: Submit via Enter key
- **WHEN** the user types text and presses Enter (without Shift held)
- **THEN** the system SHALL send the message and clear the input field

#### Scenario: New line via Shift+Enter
- **WHEN** the user presses Shift+Enter
- **THEN** the system SHALL insert a new line in the input field without sending

#### Scenario: Submit via send button
- **WHEN** the user clicks the send button
- **THEN** the system SHALL send the message and clear the input field

#### Scenario: Empty message prevented
- **WHEN** the user attempts to send an empty or whitespace-only message
- **THEN** the system SHALL NOT send the message

### Requirement: Send text via data channel
The system SHALL send text messages to the agent via LiveKit data channel using the format `{"type": "chat_message", "text": "<user text>"}`. The message SHALL be sent with reliable delivery.

#### Scenario: Message sent via data channel
- **WHEN** the user submits a text message
- **THEN** the system SHALL publish a JSON-encoded `chat_message` to the LiveKit room's data channel with `reliable: true`

#### Scenario: Message added to local feed
- **WHEN** the user submits a text message
- **THEN** the message SHALL immediately appear in the chat feed as a user message (optimistic update)

### Requirement: Input disabled when disconnected
The text input field and send button SHALL be disabled when the LiveKit room is not in a `connected` state.

#### Scenario: Disconnected state
- **WHEN** the LiveKit room connection state is not `connected`
- **THEN** the text input SHALL be disabled and the send button SHALL be non-interactive

#### Scenario: Connected state
- **WHEN** the LiveKit room connection state is `connected`
- **THEN** the text input SHALL be enabled and the send button SHALL be interactive

### Requirement: Mode switch indication on text send
When the user sends a text message while the current mode is voice, the interface SHALL visually indicate that the conversation is switching to text mode. No explicit mode toggle button is required — the mode switches implicitly based on the input type.

#### Scenario: Text sent during voice mode
- **WHEN** the user sends a text message while the microphone was active (voice mode)
- **THEN** the system SHALL display the text message with a text mode label in the chat feed
