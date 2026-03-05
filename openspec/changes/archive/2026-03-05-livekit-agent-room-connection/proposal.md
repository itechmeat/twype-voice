## Why

The API can create sessions and generate LiveKit tokens (S04), but the agent container is a stub that only logs connection. To enable voice interaction, the agent must properly handle room lifecycle: accept jobs from LiveKit Server, connect as a participant, receive participant audio streams, and detect speech boundaries with Silero VAD. This is the foundation for STT/LLM/TTS pipeline in subsequent stories.

## What Changes

- Implement full job dispatching: agent registers with LiveKit Server and receives jobs on room creation events
- Add participant lifecycle handling: detect when a user joins, subscribe to their audio track
- Integrate Silero VAD plugin for real-time voice activity detection on incoming audio
- Add structured logging for room events (participant joined/left, speech started/ended)
- Add agent settings module for configuration (VAD thresholds, subscription mode)
- Set up the test infrastructure for the agent app (conftest, fixtures)
- Update Docker dev config to run the agent in development mode with proper environment

## Capabilities

### New Capabilities
- `agent-entrypoint`: Agent worker registration, job dispatching, room connection, and participant lifecycle management
- `agent-vad`: Silero VAD integration for voice activity detection on incoming audio streams

### Modified Capabilities

None.

## Impact

- **Code:** `apps/agent/src/` — new modules for worker setup, room handling, VAD pipeline
- **Dependencies:** `livekit-agents`, `livekit-plugins-silero` already in `pyproject.toml`; no new dependencies needed
- **Docker:** `docker/docker-compose.dev.yml` agent service may need env vars (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`)
- **Config:** `configs/livekit.yaml` may need webhook/agent-related settings verified
- **Tests:** New test directory `apps/agent/tests/` with unit tests for configuration and job dispatch logic
