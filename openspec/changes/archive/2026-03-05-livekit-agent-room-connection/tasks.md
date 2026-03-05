## 1. Settings and Configuration

- [x] 1.1 Create `apps/agent/src/settings.py` with `AgentSettings(BaseSettings)`: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LOG_LEVEL` (default: `INFO`), `VAD_ACTIVATION_THRESHOLD` (default: `0.5`), `VAD_MIN_SPEECH_DURATION` (default: `0.05`), `VAD_MIN_SILENCE_DURATION` (default: `0.3`)
- [x] 1.2 Add `pydantic-settings` to `apps/agent/pyproject.toml` dependencies

## 2. Agent Implementation

- [x] 2.1 Create `apps/agent/src/agent.py` with `TwypeAgent(Agent)` subclass: configure `AgentSession` with Silero VAD only (no STT/LLM/TTS), implement `on_enter` hook with participant lifecycle logging
- [x] 2.2 Update `apps/agent/src/main.py`: import settings and agent, configure `WorkerOptions` with `entrypoint_fnc` that creates `AgentSession` with `TwypeAgent` and Silero VAD, calls `session.start()` with the room and participant
- [x] 2.3 Add VAD event logging: subscribe to speech start/end events on the session, log at DEBUG level with participant identity

## 3. Docker Build

- [x] 3.1 Update `docker/Dockerfile.agent` to run `livekit-agents download-files` in the build stage so Silero ONNX model is cached in the image

## 4. Tests

- [x] 4.1 Create `apps/agent/tests/conftest.py` with basic fixtures
- [x] 4.2 Create `apps/agent/tests/test_settings.py`: test default values, test override via env vars, test validation error on missing required fields
