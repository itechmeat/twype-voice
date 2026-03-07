## ADDED Requirements

### Requirement: Publish structured response via data channel
The data channel module SHALL provide a `publish_structured_response` function that sends a message with `type: "structured_response"` containing an array of items, each with `text` (string) and `chunk_ids` (array of UUID strings). The message SHALL include `is_final` (boolean) and optionally `message_id` (string, included only when `is_final=true` and a message ID is provided).

#### Scenario: Structured response with chunk IDs
- **WHEN** `publish_structured_response` is called with 2 items, one referencing chunk UUIDs and one without
- **THEN** the data channel message SHALL be `{"type": "structured_response", "items": [{"text": "Point A", "chunk_ids": ["uuid1"]}, {"text": "Point B", "chunk_ids": []}], "is_final": true, "message_id": "msg-uuid"}`

#### Scenario: Structured response without message ID
- **WHEN** `publish_structured_response` is called with `is_final=true` but no `message_id`
- **THEN** the `message_id` field SHALL be omitted from the payload

#### Scenario: Reliable delivery for final messages
- **WHEN** `publish_structured_response` is called with `is_final=true`
- **THEN** the data SHALL be published with `reliable=True`

#### Scenario: Unreliable delivery for interim messages
- **WHEN** `publish_structured_response` is called with `is_final=false`
- **THEN** the data SHALL be published with `reliable=False`

### Requirement: Ignore structured_response in incoming message handler
The `receive_chat_message` function SHALL treat incoming `structured_response` type messages the same as `transcript` and `chat_response` — silently ignore them without logging a warning.

#### Scenario: Agent's own structured_response ignored
- **WHEN** the agent receives a data packet with `{"type": "structured_response", ...}`
- **THEN** the function SHALL return `None` without logging a warning
