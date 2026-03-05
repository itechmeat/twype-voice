## 1. Dependencies

- [x] 1.1 Add `livekit-plugins-inworld>=1.4.4` and `livekit-plugins-elevenlabs>=1.4.3` to `apps/agent/pyproject.toml` and run `uv lock`

## 2. Settings

- [x] 2.1 Add TTS fields to `AgentSettings` in `apps/agent/src/settings.py`: `TTS_PROVIDER`, `INWORLD_API_KEY`, `TTS_INWORLD_VOICE`, `TTS_INWORLD_MODEL`, `TTS_SPEAKING_RATE`, `TTS_TEMPERATURE`, `ELEVENLABS_API_KEY`, `TTS_ELEVENLABS_VOICE_ID`, `TTS_ELEVENLABS_MODEL`
- [x] 2.2 Update `.env.example` with all TTS-related environment variables and descriptive comments
- [x] 2.3 Add/update settings tests in `apps/agent/tests/test_settings.py`

## 3. TTS builder

- [x] 3.1 Create `apps/agent/src/tts.py` with `build_tts(settings, language=None)` factory function supporting Inworld and ElevenLabs providers with language-aware voice mapping
- [x] 3.2 Add unit tests in `apps/agent/tests/test_tts.py` for both providers and language selection

## 4. Pipeline integration

- [x] 4.1 Update `prewarm()` in `apps/agent/src/main.py` to build and store TTS in `proc.userdata`
- [x] 4.2 Update `build_session()` in `apps/agent/src/agent.py` to accept and pass `tts` to `AgentSession`
- [x] 4.3 Update `entrypoint()` in `apps/agent/src/main.py` to pass prewarmed TTS to `build_session()`

## 5. Verification

- [x] 5.1 Run `uv run ruff check apps/agent/` and `uv run ruff format apps/agent/` — fix any issues
- [x] 5.2 Run `uv run pytest apps/agent/tests/` — all tests pass
