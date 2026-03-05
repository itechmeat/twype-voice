## ADDED Requirements

### Requirement: ModeContext tracks current input mode
The agent SHALL maintain a `ModeContext` object on the `TwypeAgent` instance that holds the current input mode (`"voice"` or `"text"`), the previous mode, and the timestamp of the last mode switch. The default mode at session start SHALL be `"voice"`.

#### Scenario: Initial mode is voice
- **WHEN** a new `TwypeAgent` is created
- **THEN** `ModeContext.current_mode` SHALL be `"voice"`, `previous_mode` SHALL be `"voice"`, and `switched_at` SHALL be the creation time

#### Scenario: Mode switches to text on text input
- **WHEN** a text message arrives via data channel while `current_mode` is `"voice"`
- **THEN** `ModeContext` SHALL update to `current_mode="text"`, `previous_mode="voice"`, and `switched_at` to the current time

#### Scenario: Mode switches back to voice on speech input
- **WHEN** a final voice transcript is received while `current_mode` is `"text"`
- **THEN** `ModeContext` SHALL update to `current_mode="voice"`, `previous_mode="text"`, and `switched_at` to the current time

#### Scenario: Same-mode input does not update previous_mode
- **WHEN** a text message arrives while `current_mode` is already `"text"`
- **THEN** `previous_mode` SHALL remain unchanged and `switched_at` SHALL NOT be updated

### Requirement: LLM receives mode-specific guidance per turn
The `llm_node()` override SHALL prepend a system-role message to `chat_ctx` before invoking the LLM. The message content SHALL be the `mode_voice_guidance` text when `current_mode` is `"voice"` or the `mode_text_guidance` text when `current_mode` is `"text"`. The guidance text SHALL be loaded from the prompt bundle at session start.

#### Scenario: Voice mode guidance injected
- **WHEN** `llm_node()` runs with `ModeContext.current_mode="voice"`
- **THEN** a system message with the `mode_voice_guidance` content SHALL be prepended to `chat_ctx`

#### Scenario: Text mode guidance injected
- **WHEN** `llm_node()` runs with `ModeContext.current_mode="text"`
- **THEN** a system message with the `mode_text_guidance` content SHALL be prepended to `chat_ctx`

#### Scenario: Fallback guidance when DB keys are missing
- **WHEN** `mode_voice_guidance` or `mode_text_guidance` is not present in the prompt bundle
- **THEN** the agent SHALL use a hardcoded English fallback guidance string

#### Scenario: chat_ctx is not mutated in place
- **WHEN** `llm_node()` prepends the mode guidance message
- **THEN** it SHALL operate on a copy of `chat_ctx`, not mutate the original

### Requirement: Mode markers annotate conversation history
The `llm_node()` override SHALL prefix each user message in `chat_ctx` with a mode label (`[voice]` or `[text]`) so the LLM can see which messages came from which mode. The label SHALL be prepended to the message content text.

#### Scenario: Voice message labeled
- **WHEN** `chat_ctx` contains a user message that was received via voice
- **THEN** the message content sent to the LLM SHALL start with `[voice] `

#### Scenario: Text message labeled
- **WHEN** `chat_ctx` contains a user message that was received via text
- **THEN** the message content sent to the LLM SHALL start with `[text] `

#### Scenario: Assistant messages are not labeled
- **WHEN** `chat_ctx` contains an assistant message
- **THEN** the message content SHALL NOT be prefixed with any mode label

### Requirement: TTS suppression uses ModeContext
The `TwypeAgent.tts_node()` SHALL check `ModeContext.current_mode` instead of the `ContextVar[bool]` to decide whether to suppress TTS. When `current_mode` is `"text"`, TTS SHALL be suppressed and the response SHALL be streamed via the chat response publisher.

#### Scenario: TTS suppressed in text mode
- **WHEN** `tts_node()` is called with `ModeContext.current_mode="text"`
- **THEN** TTS SHALL NOT be invoked and the text chunks SHALL be published via data channel

#### Scenario: TTS active in voice mode
- **WHEN** `tts_node()` is called with `ModeContext.current_mode="voice"`
- **THEN** TTS SHALL process normally, producing audio output

### Requirement: Thinking sounds suppressed in text mode
The `llm_node()` filler phrase logic SHALL check `ModeContext.current_mode` and skip emitting thinking sounds when in text mode, since there is no audio output channel.

#### Scenario: No filler phrase in text mode
- **WHEN** the LLM response is slow and `ModeContext.current_mode="text"`
- **THEN** no filler phrase SHALL be yielded

#### Scenario: Filler phrase emitted in voice mode
- **WHEN** the LLM response is slow and `ModeContext.current_mode="voice"` and thinking sounds are enabled
- **THEN** a filler phrase SHALL be yielded as before

### Requirement: Mode value sourced from ModeContext for persistence
All calls to `save_transcript()` and `save_agent_response()` SHALL derive the `mode` parameter from `ModeContext.current_mode` instead of hardcoded string literals.

#### Scenario: Text message persisted with mode from ModeContext
- **WHEN** a text message is received and `ModeContext.current_mode` is `"text"`
- **THEN** `save_transcript()` SHALL be called with `mode="text"`

#### Scenario: Voice transcript persisted with mode from ModeContext
- **WHEN** a voice transcript is finalized and `ModeContext.current_mode` is `"voice"`
- **THEN** `save_transcript()` SHALL be called with `mode="voice"`

#### Scenario: Assistant response mode matches input mode
- **WHEN** an assistant response is generated
- **THEN** `save_agent_response()` SHALL be called with the `mode` value from `ModeContext.current_mode` at the time the response handler runs

### Requirement: Concurrent voice and text input handling
Voice and text inputs SHALL be processed concurrently without an exclusive mode lock. The `ModeContext` SHALL update on each input arrival. The `text_reply_lock` SHALL remain to serialize text reply streaming only. Voice pipeline processing SHALL NOT be gated by any additional lock.

#### Scenario: Text arrives during voice processing
- **WHEN** a text message arrives while the voice pipeline is processing a speech utterance
- **THEN** both inputs SHALL be processed; `ModeContext` SHALL reflect `"text"` as the most recent mode

#### Scenario: Voice arrives during text processing
- **WHEN** a voice transcript finalizes while a text reply is being generated
- **THEN** the voice transcript SHALL be processed normally; `ModeContext` SHALL reflect `"voice"` as the most recent mode

#### Scenario: Text replies remain serialized
- **WHEN** two text messages arrive in rapid succession
- **THEN** the second text reply SHALL wait for the first to complete (via `text_reply_lock`)
