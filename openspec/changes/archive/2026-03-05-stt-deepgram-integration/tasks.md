## 1. Dependencies and Settings

- [x] 1.1 Add `livekit-plugins-deepgram` to `apps/agent/pyproject.toml` and run `uv lock`
- [x] 1.2 Add `DEEPGRAM_API_KEY`, `STT_LANGUAGE` (default: `multi`), `STT_MODEL` (default: `nova-3`), `DATABASE_URL` to `AgentSettings` in `apps/agent/src/settings.py`
- [x] 1.3 Update `.env.example` with new agent env vars (`DEEPGRAM_API_KEY`, `STT_LANGUAGE`, `STT_MODEL`)

## 2. STT Plugin Wiring

- [x] 2.1 Create `apps/agent/src/stt.py` — factory function `build_stt(settings)` that returns a configured `deepgram.STT` instance with model, language, and sentiment enabled
- [x] 2.2 Update `build_session()` in `apps/agent/src/agent.py` to accept and pass `stt` to `AgentSession`
- [x] 2.3 Update `build_entrypoint()` in `apps/agent/src/main.py` to build STT and pass it to `build_session()`

## 3. Database Persistence

- [x] 3.1 Create `apps/agent/src/db.py` — async SQLAlchemy engine/session factory using `DATABASE_URL` from settings
- [x] 3.2 Create `apps/agent/src/transcript.py` — `save_transcript(session_id, text, sentiment_raw)` function that inserts a `messages` row with `role=user`, `mode=voice`
- [x] 3.3 Wire transcript saving into the agent pipeline: on final transcript, call `save_transcript` (fire-and-forget with error logging, skip empty transcripts)

## 4. Data Channel Transcript Delivery

- [x] 4.1 Create `apps/agent/src/datachannel.py` — helper to publish JSON transcript messages via `room.local_participant.publish_data()` with the specified envelope format (`type`, `is_final`, `text`, `language`)
- [x] 4.2 Wire interim transcript events to publish lossy data channel messages
- [x] 4.3 Wire final transcript events to publish reliable data channel messages (include `message_id` and `sentiment_raw`)

## 5. Tests

- [x] 5.1 Unit test for `build_stt()` — verify Deepgram plugin is configured with correct model, language, sentiment flag
- [x] 5.2 Unit test for `save_transcript()` — verify message row is inserted with correct fields, empty transcripts skipped
- [x] 5.3 Unit test for data channel helper — verify JSON format, reliability flag for interim vs final
- [x] 5.4 Unit test for updated `AgentSettings` — verify new fields have correct defaults and required fields raise on missing
