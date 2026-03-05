## Context

Voice pipeline (S09) and text chat (S11) are fully operational as independent paths within the same `AgentSession`. Text messages arrive via LiveKit data channel and route to the LLM with TTS suppressed; voice messages flow through VAD -> STT -> LLM -> TTS. Both paths persist to the shared `messages` table with a `mode` column.

Current mode tracking uses a `ContextVar[bool]` (`_TEXT_MODE_ACTIVE`) scoped per async task. This is sufficient for output routing (TTS vs data channel) but invisible to the LLM — it generates responses in the same style regardless of input mode. The `text_reply_lock` serializes text replies but does not coordinate with concurrent voice input.

Key constraints:
- LiveKit Agents SDK manages the voice pipeline lifecycle — we override `tts_node()` and `llm_node()` but cannot intercept `generate_reply()` internals.
- `build_instructions()` assembles prompts once at session start; there is no per-turn dynamic injection point.
- The `AgentSession` does not expose a hook to modify the system prompt between turns.

## Goals / Non-Goals

**Goals:**
- LLM awareness of input mode so it adapts response format (brief/conversational for voice, detailed/structured for text).
- Unified mode state tracked in a single object, replacing scattered `ContextVar` usage.
- Safe concurrent handling when voice and text inputs overlap.
- Mode context visible in conversation history sent to the LLM.

**Non-Goals:**
- Explicit mode switching UI/API — mode is determined implicitly by input type (audio track vs data channel), not by a client command.
- Persisting mode switch events as separate database records — the `mode` column on `messages` is sufficient.
- Changing the prompt loading architecture (still loaded once at session start from DB).
- Dual-layer response splitting (S15) — text-mode responses are plain detailed text, not structured voice+text pairs.

## Decisions

### D1: ModeContext dataclass as single source of truth

**Decision:** Create a `ModeContext` dataclass that holds `current_mode`, `previous_mode`, and `switched_at` timestamp. A single instance lives on the `TwypeAgent` and is mutated on every input event.

**Alternatives considered:**
- Keep `ContextVar[bool]` — rejected because it provides no history, no timestamp, and is invisible outside the async task that set it.
- Store mode in `AgentSession` custom data — rejected because `AgentSession` is a framework object and should not carry domain state.

**Rationale:** A plain dataclass on the agent is simple, testable, and accessible from all event handlers without async context scoping issues. The `previous_mode` field enables the LLM to see that a switch just happened.

### D2: Per-turn mode injection via `llm_node()` override

**Decision:** Override `llm_node()` to prepend a mode context message to `chat_ctx` before calling `super().llm_node()`. The injected message is a system-role entry like: `"[Current input mode: text. Provide detailed, structured responses.]"` or `"[Current input mode: voice. Keep responses brief and conversational.]"`.

**Alternatives considered:**
- Modify `build_instructions()` to include a mode placeholder and re-set `agent.instructions` per turn — rejected because mutating `instructions` is not thread-safe and the SDK may cache it.
- Add a new prompt layer `mode_prompt` to the DB and load it — rejected because the mode changes per turn, not per session. DB-loaded prompts are static for the session.
- Use `input_modality` parameter on `generate_reply()` — rejected because LiveKit SDK does not forward this to the LLM system prompt.

**Rationale:** `llm_node()` is already overridden for thinking sounds. Prepending a context message to `chat_ctx` is the least invasive approach — it does not alter stored instructions, works per-turn, and the SDK passes `chat_ctx` through to the LLM.

### D3: Mode guidance text from DB prompt layers, not hardcoded

**Decision:** Add a `mode_voice_guidance` and `mode_text_guidance` key to `agent_config` (same mechanism as existing prompt layers). The `llm_node()` override selects the appropriate guidance based on `ModeContext.current_mode` and injects it. If no guidance is configured, a sensible English fallback is used in code.

**Alternatives considered:**
- Hardcode mode instructions in Python — rejected because it violates the "config in DB, not code" principle established in S10.
- Add a single `mode_prompt` template with a `{mode}` placeholder — rejected because voice and text guidance have fundamentally different content and length.

**Rationale:** Consistent with the existing prompt architecture. Two separate keys allow independent localization and versioning per mode. The seed script provides default values.

### D4: Concurrent input — last-writer-wins with mode switch

**Decision:** No exclusive lock between voice and text. Both inputs proceed through their pipelines concurrently. `ModeContext` updates atomically on each input arrival (voice transcript finalized or text message received). The `llm_node()` reads the mode at the moment it runs, so each response matches the most recent input mode.

**Alternatives considered:**
- Exclusive mode lock (acquiring lock cancels the other pipeline) — rejected because it adds complexity and may cause audio glitches if voice is interrupted by a text message.
- Queue-based serialization of all inputs — rejected because it adds latency to voice responses.

**Rationale:** Race conditions are unlikely in practice (users rarely speak and type simultaneously). The worst case is a brief voice response generated with text-mode guidance or vice versa — an acceptable trade-off for simplicity. The `text_reply_lock` remains to serialize text replies specifically (prevents interleaved streaming chunks).

### D5: Mode markers in conversation history

**Decision:** When `llm_node()` prepends the mode context message, it also annotates the last N user messages in `chat_ctx` with mode labels (e.g., `[voice]` or `[text]` prefix). This gives the LLM visibility into the conversation flow across mode switches.

**Alternatives considered:**
- No history annotation — rejected because the LLM loses context about how the conversation flowed between modes.
- Separate system messages for each mode switch — rejected because it inflates context length with meta-messages.

**Rationale:** Lightweight prefix on existing messages is minimal overhead and gives the LLM enough signal to understand mode transitions without adding new messages to the context.

## Risks / Trade-offs

**[Race condition in concurrent voice+text]** The last-writer-wins approach means a response may occasionally use the wrong mode guidance if voice and text overlap within milliseconds.
-> Mitigation: Acceptable for MVP. Monitor via logging. Future: add a short debounce (100ms) before mode switch takes effect.

**[chat_ctx mutation in llm_node]** Prepending messages to `chat_ctx` modifies the context object. If the SDK caches or reuses it across turns, this could cause message duplication.
-> Mitigation: Clone `chat_ctx` before modification. Verify SDK behavior in tests.

**[DB seed dependency]** Mode guidance keys (`mode_voice_guidance`, `mode_text_guidance`) must exist in `agent_config` for the feature to work.
-> Mitigation: Code fallback if keys are missing. Seed script updated in the same PR.

**[Thinking sounds in text mode]** The `llm_node()` currently emits filler phrases for slow LLM responses. In text mode, fillers should be suppressed since there is no audio output.
-> Mitigation: Check `ModeContext.current_mode` before emitting fillers. Skip if text mode.
