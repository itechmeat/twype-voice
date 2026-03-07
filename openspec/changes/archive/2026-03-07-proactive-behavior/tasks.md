## 1. SilenceTimer Module

- [x] 1.1 Create `apps/agent/src/silence_timer.py` with `SilenceTimer` class — `__init__(short_timeout, long_timeout, on_short_timeout, on_long_timeout)`, internal `asyncio.Task`, `_fired` flag
- [x] 1.2 Implement `start()` method — creates async task that sleeps for `short_timeout`, fires short callback, sleeps for remaining `long_timeout - short_timeout`, fires long callback
- [x] 1.3 Implement `reset()` method — cancels current task, clears `_fired` flag, starts a new timer cycle
- [x] 1.4 Implement `stop()` method — cancels current task, prevents further callbacks, idempotent
- [x] 1.5 Implement single-fire guard — after either callback fires, set `_fired=True` for short stage; after long fires, block all further callbacks until `reset()`
- [x] 1.6 Write unit tests for `SilenceTimer`: short fires, long fires, reset cancels, stop cancels, single-fire guard, idempotent stop

## 2. Settings

- [x] 2.1 Add `PROACTIVE_ENABLED: bool = True`, `PROACTIVE_SHORT_TIMEOUT: float = Field(default=15.0, ge=1.0)`, `PROACTIVE_LONG_TIMEOUT: float = Field(default=45.0, ge=1.0)` to `AgentSettings` in `settings.py`

## 3. Data Channel

- [x] 3.1 Add `publish_proactive_nudge(room, proactive_type, message_id=None)` function to `datachannel.py` — publishes `{"type": "proactive_nudge", "proactive_type": ...}` with `reliable=True`
- [x] 3.2 Write unit tests for `publish_proactive_nudge` message serialization

## 4. Seed Data

- [x] 4.1 Update `proactive_prompt` in `scripts/seed.py` — replace static text with template containing `{proactive_type}` and `{emotional_context}` placeholders
- [x] 4.2 Verify template renders correctly with `str.format_map()` and both placeholder keys

## 5. Agent Integration

- [x] 5.1 Add `_build_emotional_context_summary()` helper in `main.py` — returns human-readable string from `agent.current_emotional_state` or `"neutral"`
- [x] 5.2 Add `_render_proactive_prompt(proactive_type)` helper in `main.py` — renders `proactive_prompt` layer with `{proactive_type}` and `{emotional_context}` via `str.format_map()`
- [x] 5.3 Add `_handle_short_timeout()` async callback in `main.py` — publishes proactive nudge, calls `session.generate_reply` with rendered proactive prompt and `proactive_type="follow_up"`
- [x] 5.4 Add `_handle_long_timeout()` async callback in `main.py` — publishes proactive nudge, calls `session.generate_reply` with rendered proactive prompt and `proactive_type="extended_silence"`
- [x] 5.5 Create `SilenceTimer` instance in `entrypoint()` when `PROACTIVE_ENABLED` is `True`, passing short/long callbacks and timeout settings
- [x] 5.6 Wire timer `reset()` into `handle_transcript_event` (all transcripts, including interim)
- [x] 5.7 Wire timer `reset()` into `handle_data_received_event` (after valid chat message received)
- [x] 5.8 Wire timer `reset()` into `on_user_state_changed` when `new_state == "speaking"`
- [x] 5.9 Wire timer `start()` (or `reset()`) into `on_agent_speech_committed` handler
- [x] 5.10 Wire timer `stop()` into `on_participant_disconnected` handler
- [x] 5.11 Guard: skip timer creation entirely when `PROACTIVE_ENABLED` is `False`

## 6. Integration Tests

- [x] 6.1 Write test: timer fires short callback after configured timeout in a mocked agent entrypoint
- [x] 6.2 Write test: timer resets on simulated user activity (transcript event)
- [x] 6.3 Write test: timer does not fire when `PROACTIVE_ENABLED=False`
- [x] 6.4 Write test: proactive nudge data channel message format verification
