## Why

During a voice conversation the agent must feel responsive and natural. Currently, if a user starts speaking while the agent is still talking, the LiveKit SDK's low-level interruption infrastructure (`false_interruption_timeout`, `min_interruption_duration`) is configured but the application layer does not actively cancel in-flight LLM/TTS generation, recover from false interruptions, or notify the client. This makes the agent feel unresponsive — it keeps talking over the user instead of yielding the floor.

## What Changes

- Detect user speech that overlaps with agent TTS playback and immediately cancel the active LLM token stream and TTS audio output, switching the pipeline to receive new user input.
- Handle false interruptions: when VAD fires but STT produces no recognized words within the configured timeout, automatically resume the interrupted response — regenerate a brief continuation or replay the last 1-2 sentences.
- Publish interruption lifecycle events (`interruption_started`, `interruption_resolved`, `interruption_false`) over the LiveKit data channel so the client can update UI state (e.g., stop showing the agent's transcript, show a "listening" indicator).
- Make all interruption thresholds configurable via agent settings (already partially done in `settings.py`; extend as needed).

## Capabilities

### New Capabilities
- `interruption-handler`: Core interruption detection, LLM/TTS cancellation, false-interruption recovery, and data-channel event publishing.

### Modified Capabilities
- `voice-pipeline-turn-detection`: Existing spec covers turn-detection parameters (`false_interruption_timeout`, `min_interruption_duration`, `resume_false_interruption`). Requirements change: the spec must now define the expected application-level behavior when these thresholds trigger — cancellation semantics, recovery flow, and the contract between turn detection and the new interruption handler.

## Impact

- **Agent code** (`apps/agent/src/main.py`, `apps/agent/src/agent.py`): New event handlers for interruption detection; modifications to `generate_reply` flow to support cancellation and resumption.
- **Agent settings** (`apps/agent/src/settings.py`): Possible new settings for recovery behavior (e.g., max replay sentences, continuation prompt flag).
- **Agent tests**: New tests for interruption detection, cancellation, false-interruption recovery, and data-channel event publishing.
- **Client (future)**: Data-channel messages are defined now; the PWA will consume them in S22.
- **Dependencies**: No new external dependencies — relies on LiveKit Agents SDK built-in interruption support.
