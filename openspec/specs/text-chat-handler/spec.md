## ADDED Requirements

### Requirement: Receive text messages via data channel
The agent SHALL listen for incoming reliable data packets on the LiveKit room's `data_received` event. The agent SHALL parse each packet as JSON and process messages with `{"type": "chat_message", "text": "<user text>"}` format. Messages with empty or whitespace-only `text` SHALL be ignored. Malformed or unrecognized message types SHALL be logged at WARNING level and ignored.

#### Scenario: Valid text message received
- **WHEN** the client sends a reliable data packet with `{"type": "chat_message", "text": "Hello"}`
- **THEN** the agent parses the JSON and routes the text `"Hello"` to the LLM

#### Scenario: Empty text message ignored
- **WHEN** the client sends `{"type": "chat_message", "text": "   "}`
- **THEN** the agent ignores the message and does not invoke the LLM

#### Scenario: Malformed JSON ignored
- **WHEN** the client sends a data packet that is not valid JSON
- **THEN** the agent logs a WARNING and ignores the packet

#### Scenario: Unknown message type ignored
- **WHEN** the client sends `{"type": "unknown_type", "text": "test"}`
- **THEN** the agent ignores the message without error

#### Scenario: Agent's own packets ignored
- **WHEN** a data packet originates from the agent's own local participant
- **THEN** the agent SHALL NOT process it

### Requirement: Route text to LLM bypassing STT
The agent SHALL send received text messages directly to the LLM via `AgentSession.generate_reply(user_input=text)`, bypassing the STT pipeline entirely. Before calling `generate_reply`, the handler SHALL update `ModeContext` to `"text"` mode. The text message SHALL appear in the same conversation context as voice messages.

#### Scenario: Text routed to LLM
- **WHEN** a valid `chat_message` is received
- **THEN** the agent updates `ModeContext.current_mode` to `"text"` and calls `generate_reply` with the user's text, and the LLM generates a response using the full conversation history (including prior voice messages)

#### Scenario: ModeContext reset not needed after text reply
- **WHEN** a text reply completes
- **THEN** `ModeContext.current_mode` SHALL remain `"text"` until the next voice input arrives (no explicit reset)

#### Scenario: LLM error during text response
- **WHEN** the LLM fails to generate a response for a text message
- **THEN** the agent logs the error at ERROR level and sends an error notification via data channel

### Requirement: Stream text response via data channel
The agent SHALL send the LLM response back to the client via data channel using the format `{"type": "chat_response", "text": "<chunk>", "is_final": false}` for interim chunks and `{"type": "chat_response", "text": "<full text>", "is_final": true, "message_id": "<uuid>"}` for the final response. The `message_id` field SHALL be included in the final message only when the response was successfully persisted to the database.

#### Scenario: Final response delivered
- **WHEN** the LLM completes a response to a text message
- **THEN** the agent sends a data packet with `type=chat_response`, `is_final=true`, the full response text, and the `message_id` from persistence

#### Scenario: Response without persistence
- **WHEN** the LLM completes a response but database persistence fails
- **THEN** the agent sends the final `chat_response` without a `message_id` field

### Requirement: Suppress TTS for text-mode responses
The agent SHALL NOT invoke TTS for responses generated from text input. When a response is triggered by a `chat_message`, the `TwypeAgent.tts_node` SHALL check `ModeContext.current_mode` (instead of the `ContextVar[bool]`) and return `None` when the mode is `"text"` to skip speech synthesis.

#### Scenario: No audio output for text response
- **WHEN** a text message triggers an LLM response
- **THEN** no audio is synthesized or sent to the WebRTC audio track

#### Scenario: Voice pipeline unaffected
- **WHEN** a voice input triggers an LLM response (normal voice flow)
- **THEN** TTS operates normally, producing audio output

### Requirement: Persist text messages with mode label
The agent SHALL save user text messages to the `messages` table with `role='user'`, `mode='text'`, and `content` set to the message text. The `mode` value SHALL be read from `ModeContext.current_mode` instead of a hardcoded `"text"` string. The `voice_transcript` field SHALL be `NULL` for text messages. The `sentiment_raw` field SHALL be `NULL` (no Deepgram analysis for text input). Assistant responses to text messages SHALL be saved with `role='assistant'`, `mode='text'`.

#### Scenario: User text message persisted
- **WHEN** a valid `chat_message` is received and the session ID is resolved
- **THEN** a row is inserted into `messages` with `role='user'`, `mode='text'`, `content=<text>`, `voice_transcript=NULL`, `sentiment_raw=NULL`

#### Scenario: Assistant text response persisted
- **WHEN** the LLM generates a response to a text message
- **THEN** a row is inserted into `messages` with `role='assistant'`, `mode='text'`, `content=<response text>`

#### Scenario: Persistence failure does not block response
- **WHEN** database persistence fails for a text message
- **THEN** the agent logs the error and continues delivering the response via data channel

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
