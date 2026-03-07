## Context

The LiveKit Agents SDK provides built-in interruption infrastructure: `false_interruption_timeout`, `min_interruption_duration`, and `resume_false_interruption` are already configured in `AgentSession` (see `apps/agent/src/agent.py:105-159`). However, the application layer does not act on interruption events — the `on_user_state_changed` handler in `main.py` only resets the proactive silence timer when speech is detected, without cancelling LLM/TTS or notifying the client.

The LiveKit Agents SDK (`AgentSession`) internally handles the low-level mechanics: when `resume_false_interruption=True`, the SDK tracks whether TTS was playing, detects VAD speech, and can resume playback if no transcript arrives within `false_interruption_timeout`. The key gap is that **the application layer needs to hook into these events** to provide:
1. Proper cancellation of in-flight LLM generation (not just TTS audio)
2. Data channel notifications to the client
3. Logging and observability of interruption events

## Goals / Non-Goals

**Goals:**
- Immediate cancellation of active LLM token stream and TTS audio when a valid interruption is detected
- Graceful recovery from false interruptions — resume or regenerate a brief continuation
- Publish interruption lifecycle events over the LiveKit data channel for client consumption
- All interruption behavior configurable via environment variables (existing + new settings)

**Non-Goals:**
- Client-side UI handling of interruption events (deferred to S22)
- Changes to VAD sensitivity or STT provider configuration
- Custom interruption detection beyond what LiveKit SDK provides (no separate ML model)
- Partial replay of buffered TTS audio (SDK handles this internally via `resume_false_interruption`)

## Decisions

### 1. Rely on LiveKit SDK's built-in interruption mechanics

**Decision:** Use the SDK's `AgentSession` interruption handling as the foundation rather than building custom VAD-during-TTS detection.

**Rationale:** The SDK already tracks agent speaking state, detects overlapping user speech, and supports false interruption recovery. Duplicating this logic would be fragile and would diverge from SDK upgrades.

**Alternative considered:** Custom interruption detector monitoring VAD events against TTS playback state. Rejected — unnecessary complexity when the SDK provides this natively.

### 2. Hook into AgentSession events for application-level behavior

**Decision:** Subscribe to `agent_speech_interrupted` and related SDK events on `AgentSession` to trigger application-level actions (LLM cancellation, data channel publishing, logging).

**Rationale:** The SDK emits events when interruptions occur. The application layer should react to these events rather than reimplementing detection. This keeps the boundary clean: SDK handles detection, application handles business logic.

**Alternative considered:** Override `AgentSession` methods. Rejected — brittle coupling to SDK internals.

### 3. Data channel message format for interruption events

**Decision:** Publish JSON messages on the existing data channel with a `type` field distinguishing interruption events:
- `{"type": "interruption_started"}` — agent speech was interrupted by user
- `{"type": "interruption_resolved", "resumed": false}` — interruption led to new user input being processed
- `{"type": "interruption_false", "resumed": true}` — false interruption, agent resumes previous response

**Rationale:** Consistent with existing data channel message patterns (interim transcripts, mode switching). The client (S22) will use these to update UI state.

### 4. LLM cancellation via task/future cancellation

**Decision:** When a valid interruption is detected, cancel the active LLM generation task. The LiveKit SDK already stops TTS playback; the application must ensure the upstream LLM stream is also terminated to avoid wasted tokens and latency.

**Rationale:** Without explicit LLM cancellation, the model continues generating tokens that will never be spoken, wasting API credits and keeping the connection busy.

## Risks / Trade-offs

- **[SDK event availability]** The exact event names and payloads depend on the LiveKit Agents SDK version. If the SDK does not expose granular interruption events, we may need to track agent state manually.
  - *Mitigation:* Verify available events against the installed SDK version during implementation. Fall back to `user_state_changed` + agent state tracking if needed.

- **[False interruption sensitivity]** The 2.0s `FALSE_INTERRUPTION_TIMEOUT` may feel slow in fast-paced conversation or too aggressive in noisy environments.
  - *Mitigation:* Already configurable via environment variable. Document recommended ranges.

- **[Race condition: LLM cancellation vs. new generation]** If the user interrupts and immediately speaks, the cancellation of the old LLM task must complete before the new generation starts.
  - *Mitigation:* Use sequential event processing — the SDK's event loop ensures handlers run in order. Verify in tests.

- **[Resumed response coherence]** When resuming after a false interruption, the replayed/regenerated continuation may not feel natural.
  - *Mitigation:* The SDK's `resume_false_interruption=True` replays buffered TTS audio, which is the most natural option. Only if the buffer is exhausted do we need LLM regeneration of a brief continuation.
