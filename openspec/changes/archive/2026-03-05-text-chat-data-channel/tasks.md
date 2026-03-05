## 1. Persistence mode parameter

- [x] 1.1 Add optional `mode` parameter (default `"voice"`) to `save_transcript` in `apps/agent/src/transcript.py`
- [x] 1.2 Add optional `mode` parameter (default `"voice"`) to `save_agent_response` in `apps/agent/src/transcript.py`
- [x] 1.3 Update tests for `save_transcript` and `save_agent_response` to cover `mode="text"`

## 2. Inbound data channel handler

- [x] 2.1 Add `receive_chat_message` handler in `apps/agent/src/datachannel.py`: parse JSON, validate `type=chat_message`, extract `text`, ignore empty/malformed/self-originated packets
- [x] 2.2 Add `publish_chat_response` function in `apps/agent/src/datachannel.py` for outbound `{"type": "chat_response", "text": ..., "is_final": ...}` messages
- [x] 2.3 Write tests for inbound parsing (valid, empty, malformed, unknown type, self-originated)
- [x] 2.4 Write tests for `publish_chat_response` output format

## 3. TTS suppression

- [x] 3.1 Add text-mode flag mechanism to `TwypeAgent` (e.g., `_text_mode_active` attribute)
- [x] 3.2 Override `tts_node` in `TwypeAgent` to return `None` when text-mode flag is set
- [x] 3.3 Write tests verifying TTS is skipped for text input and unaffected for voice input

## 4. Wire data channel handler into entrypoint

- [x] 4.1 Register `data_received` event listener on the room in `main.py`
- [x] 4.2 In the handler: parse message, set text-mode flag, call `generate_reply`, persist user message with `mode="text"`, persist assistant response with `mode="text"`
- [x] 4.3 Reset text-mode flag after response completes
- [x] 4.4 Send `chat_response` via data channel with `message_id` from persistence

## 5. Integration tests

- [x] 5.1 End-to-end test: send `chat_message` via data channel → receive `chat_response` with correct format
- [x] 5.2 Test: text message persisted with `mode="text"`, voice message still persisted with `mode="voice"`
- [x] 5.3 Test: TTS not invoked for text input, TTS invoked for voice input in same session
