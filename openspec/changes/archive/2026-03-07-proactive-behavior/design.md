## Context

The agent currently operates reactively — it responds only when the user speaks or sends a text message. After the agent finishes a response, if the user goes silent the session stalls. The existing event-driven architecture in `main.py` already handles `user_input_transcribed`, `agent_speech_committed`, `data_received`, and `user_state_changed` events. The `proactive_prompt` layer is already defined in `PROMPT_LAYER_ORDER` and seeded (basic English text), but never used at runtime. The emotional state from S17 (`agent.current_emotional_state`) is available for tone adaptation.

LiveKit Agents `AgentSession` exposes `session.generate_reply(user_input=..., input_modality=...)` which can be called programmatically to trigger LLM generation without a real user message.

## Goals / Non-Goals

**Goals:**
- Implement a silence timer that fires after agent responses with two escalation stages
- Generate proactive utterances via LLM (not hardcoded) with context from conversation history and emotional state
- Ensure the timer resets on any user activity and fires at most once per silence period
- Publish a data channel signal so the client can distinguish proactive messages from regular responses

**Non-Goals:**
- Scheduling or cron-based reminders (this is per-session in-conversation only)
- Multi-utterance proactive sequences (exactly one utterance per silence period)
- Client-side UI changes (data channel message is sufficient for now)
- Persistence of proactive events to the database (may be added later)

## Decisions

### D1: Standalone `SilenceTimer` class with asyncio.Task-based scheduling

The timer is a self-contained class wrapping `asyncio.sleep` inside a managed task. On each reset, the running task is cancelled and a fresh one is created. This keeps timer logic isolated from the event handlers in `main.py`.

**Alternative considered:** Using a single `asyncio.Event` with a loop checking elapsed time. Rejected — more complex, harder to cancel cleanly, and provides no benefit over simple task cancellation.

### D2: Two-phase callback design

The `SilenceTimer` accepts two async callbacks: `on_short_timeout` and `on_long_timeout`. The timer task sleeps for `short_timeout` seconds, fires the short callback, then sleeps for `long_timeout - short_timeout` more seconds and fires the long callback. After firing long, the timer enters a "fired" state and will not fire again until explicitly reset.

This avoids separate timers and race conditions — a single sequential task handles both phases.

### D3: Proactive utterances via synthetic user message to `session.generate_reply`

To trigger LLM generation, inject a synthetic system-level message with a `proactive` flag. The message includes the proactive type (`follow_up` or `extended_silence`) and a snapshot of the current emotional context. The existing `proactive_prompt` seed template is rendered with `{proactive_type}` and `{emotional_context}` placeholders.

**Alternative considered:** Calling the LLM directly via httpx (bypassing the pipeline). Rejected — this would skip TTS, dual-layer parsing, and response persistence. Using `session.generate_reply` keeps the full pipeline intact.

### D4: Activity signals that reset the timer

The timer resets on:
- `user_input_transcribed` (any transcript, including interim)
- `data_received` (text chat message)
- `user_state_changed` to `"speaking"` (VAD speech start)

The timer starts (or restarts) on:
- `agent_speech_committed` (agent finished speaking)

The timer stops entirely on:
- Participant disconnect
- Session end

### D5: Single-fire guard per silence period

After firing either callback, the timer sets a `_fired` flag. While `_fired` is true, no further callbacks execute. The flag clears only on `reset()` (triggered by user activity). This guarantees at most one proactive utterance per silence period.

### D6: Data channel message type `proactive_nudge`

A new `publish_proactive_nudge(room, proactive_type, message_id)` function publishes `{"type": "proactive_nudge", "proactive_type": "follow_up"|"extended_silence"}` with `reliable=True`. This lets the client render proactive messages differently (e.g., dimmed, with an indicator).

### D7: Seed `proactive_prompt` update with template placeholders

The existing `proactive_prompt` seed text is a static instruction. Replace it with a template containing `{proactive_type}` and `{emotional_context}` placeholders so the LLM receives context about why it is speaking and the user's current emotional state. The prompt instructs the LLM to generate a brief, natural follow-up (for `follow_up`) or a gentle check-in (for `extended_silence`).

## Risks / Trade-offs

- **[Risk] Timer fires during TTS playback** → The timer starts on `agent_speech_committed`, which fires after speech is fully delivered. If there's a race with slow TTS, the worst case is a slightly early follow-up, which is acceptable.

- **[Risk] Proactive message triggers another proactive timer cycle** → The single-fire guard prevents this. After the proactive response completes, the timer does NOT auto-restart — only real user activity resets it.

- **[Risk] LLM latency on proactive generation** → The proactive utterance goes through the full pipeline (LLM → TTS → WebRTC). If the LLM is slow, the user might start speaking before the proactive message arrives. The timer reset on VAD speech_start will cancel the pending generation via interruption handling already built into AgentSession.

- **[Trade-off] No persistence of proactive events** → Proactive messages go through `save_agent_response` like normal responses (via `agent_speech_committed`). The `proactive_type` flag is not stored separately. Acceptable for MVP — can be added as a message metadata field later.
