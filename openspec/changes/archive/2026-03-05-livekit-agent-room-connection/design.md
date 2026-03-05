## Context

The agent container (`apps/agent/`) currently has a minimal stub: `main.py` with a basic `entrypoint` function that logs and connects to a room. The `livekit-agents` and `livekit-plugins-silero` packages are already in `pyproject.toml`. Docker Compose dev config runs the agent with `uv run python src/main.py dev` and injects all required LiveKit env vars.

S04 (session management) creates rooms and generates LiveKit tokens on the API side. This story makes the agent actually useful — it must accept dispatched jobs, handle participant lifecycle, and run Silero VAD on incoming audio.

## Goals / Non-Goals

**Goals:**

- Agent registers with LiveKit Server and accepts jobs automatically on room creation
- Agent connects to the room, waits for the first human participant, and subscribes to their audio track
- Silero VAD processes incoming audio and detects speech start/end events
- Structured logging for all room lifecycle events (participant joined/left, speech activity)
- Configuration via settings module (VAD thresholds, logging level)
- Test infrastructure for `apps/agent/`

**Non-Goals:**

- No STT, LLM, or TTS processing — agent only listens (pipeline comes in S06-S09)
- No STT/LLM/TTS in the AgentSession — only VAD is configured; the full pipeline is assembled in S09
- No data channel handling (S11)
- No database writes from the agent (session recording is done by the API in S04)
- No explicit dispatch or agent naming — automatic dispatch is sufficient for MVP

## Decisions

### D1: Use `AgentSession` with VAD-only pipeline vs raw `JobContext`

**Decision:** Use `AgentSession` with only VAD configured (no STT/LLM/TTS).

**Rationale:** `AgentSession` is the standard orchestrator in livekit-agents. Starting with it now — even with only VAD — means S06-S09 will simply add pipeline components to the existing session rather than rewriting from `JobContext` to `AgentSession`. The session handles participant linking, audio subscription, and event emission automatically.

**Alternative considered:** Raw `JobContext` with manual `room.on("track_subscribed")` and direct Silero VAD calls. Simpler for this story but would require a rewrite when STT/LLM/TTS are added.

### D2: Automatic dispatch (default) vs explicit dispatch

**Decision:** Automatic dispatch (default behavior — no `agent_name` set).

**Rationale:** MVP has one agent type. Every room created by the API should get an agent. Explicit dispatch adds complexity with no benefit until multiple agent types exist.

### D3: Settings via pydantic-settings vs hardcoded

**Decision:** Use `pydantic-settings` with `BaseSettings` for agent configuration.

**Rationale:** Consistent with the API app pattern (FastAPI + pydantic). Reads from env vars with sensible defaults. Easy to override in Docker Compose or tests.

### D4: Project structure

**Decision:** Flat module structure under `apps/agent/src/`:

```
apps/agent/src/
  __init__.py
  main.py          # CLI entrypoint, WorkerOptions
  agent.py         # Agent subclass with on_enter, VAD event handlers
  settings.py      # AgentSettings(BaseSettings)
apps/agent/tests/
  __init__.py
  conftest.py      # Fixtures
  test_settings.py # Settings validation tests
```

**Rationale:** Minimal structure for current scope. Directories like `plugins/`, `prompts/`, `rag/` will be added in later stories when needed.

### D5: Silero VAD configuration

**Decision:** Use `livekit-plugins-silero` `SileroVAD` with default thresholds, exposed via settings for override.

Key defaults from the plugin:
- `min_speech_duration`: 0.05s
- `min_silence_duration`: 0.3s
- `activation_threshold`: 0.5

These are reasonable for most voice interactions. Settings will allow override via env vars if needed during testing.

### D6: download-files for Silero model

**Decision:** Run `livekit-agents download-files` in the Dockerfile build stage.

**Rationale:** Silero VAD requires a local ONNX model file. Downloading at build time avoids first-run latency and network dependencies at runtime.

## Risks / Trade-offs

- **[Risk] AgentSession with no STT/LLM/TTS may have undocumented behavior** → Mitigation: test with Agents Playground; if issues arise, fall back to raw JobContext for this story only.
- **[Risk] Silero model download in Docker build may fail in CI** → Mitigation: add retry logic or cache the model file in a Docker layer.
- **[Trade-off] No unit tests for VAD event handling** → VAD integration is tested manually via Agents Playground per project testing conventions (docs/specs.md section 9: "LiveKit Agent (voice pipeline) — tested manually via Agents Playground"). Unit tests cover settings and configuration only.

## Open Questions

- None — this is a well-scoped foundational story with clear boundaries.
