## 1. ModeContext dataclass

- [x] 1.1 Create `ModeContext` dataclass in `apps/agent/src/agent.py` with `current_mode`, `previous_mode`, `switched_at` fields and a `switch_to(mode)` method
- [x] 1.2 Add `ModeContext` instance to `TwypeAgent.__init__`, default mode `"voice"`
- [x] 1.3 Remove `_TEXT_MODE_ACTIVE` ContextVar, `activate_text_mode()`, `reset_text_mode()` — replace `text_mode_active` property with `ModeContext.current_mode == "text"`
- [x] 1.4 Write unit tests for `ModeContext`: initial state, switch to text, switch back to voice, same-mode no-op

## 2. Prompt system: mode guidance keys

- [x] 2.1 Add `MODE_GUIDANCE_KEYS` constant to `apps/agent/src/prompts.py` with `["mode_voice_guidance", "mode_text_guidance"]`
- [x] 2.2 Update `load_prompt_bundle()` to include `MODE_GUIDANCE_KEYS` in the DB query alongside `PROMPT_LAYER_ORDER`
- [x] 2.3 Add fallback constants `FALLBACK_VOICE_GUIDANCE` and `FALLBACK_TEXT_GUIDANCE` in `prompts.py`
- [x] 2.4 Update seed script (`scripts/seed.py`) with `mode_voice_guidance` and `mode_text_guidance` rows for `en` and `ru` locales
- [x] 2.5 Write unit tests for `load_prompt_bundle()` returning mode guidance keys

## 3. Per-turn mode injection in llm_node

- [x] 3.1 Update `TwypeAgent.llm_node()` to clone `chat_ctx`, prepend mode guidance system message based on `ModeContext.current_mode`, and annotate user messages with `[voice]`/`[text]` prefixes
- [x] 3.2 Skip thinking sounds (filler phrases) when `ModeContext.current_mode == "text"`
- [x] 3.3 Write unit tests for `llm_node()`: voice guidance injected, text guidance injected, chat_ctx not mutated, no fillers in text mode

## 4. TTS suppression via ModeContext

- [x] 4.1 Update `TwypeAgent.tts_node()` to check `ModeContext.current_mode` instead of `ContextVar`
- [x] 4.2 Write unit tests for `tts_node()`: suppressed in text mode, active in voice mode

## 5. Wire ModeContext into entrypoint

- [x] 5.1 Update `handle_data_received_event` in `main.py`: call `agent.mode_context.switch_to("text")` before `generate_reply`, remove ContextVar token management
- [x] 5.2 Update `handle_transcript_event` in `main.py`: call `agent.mode_context.switch_to("voice")` on final transcript
- [x] 5.3 Update `_assistant_response_mode()` to read from `agent.mode_context.current_mode`
- [x] 5.4 Update `save_transcript` calls to use `mode=agent.mode_context.current_mode` instead of hardcoded strings
- [x] 5.5 Write integration tests for mode switching flow: text input -> text mode -> voice input -> voice mode

## 6. Update existing tests

- [x] 6.1 Update `test_agent_session.py` tests that reference `activate_text_mode`/`reset_text_mode` to use `ModeContext`
- [x] 6.2 Update `test_datachannel.py` if any tests depend on ContextVar mode tracking
- [x] 6.3 Update `test_thinking_sounds.py` to cover text-mode filler suppression
