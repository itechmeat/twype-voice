## MODIFIED Requirements

### Requirement: Suppress TTS for text-mode responses
The agent SHALL NOT invoke TTS for responses generated from text input. When a response is triggered by a `chat_message`, the `TwypeAgent.tts_node` SHALL check `ModeContext.current_mode` (instead of the `ContextVar[bool]`) and return `None` when the mode is `"text"` to skip speech synthesis.

#### Scenario: No audio output for text response
- **WHEN** a text message triggers an LLM response
- **THEN** no audio is synthesized or sent to the WebRTC audio track

#### Scenario: Voice pipeline unaffected
- **WHEN** a voice input triggers an LLM response (normal voice flow)
- **THEN** TTS operates normally, producing audio output

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
