## Why

The agent currently only listens via VAD — it detects speech segments but cannot transcribe them. STT is the next pipeline stage needed to convert detected speech into text for the LLM. Without STT, the voice pipeline is incomplete and no user utterances can be processed or stored.

## What Changes

- Add `livekit-plugins-deepgram` as a dependency to the agent
- Integrate Deepgram STT into the `AgentSession` pipeline (streaming mode with interim and final transcripts)
- Configure language support for Russian (`ru`) and English (`en`) via Deepgram's `language` parameter
- Extract sentiment score (`-1..1`) from Deepgram results and map it to the `sentiment_raw` field
- Save final user transcripts to the `messages` table (`role=user`, `mode=voice`, `content` = final transcript, `sentiment_raw` from Deepgram)
- Send interim transcripts to the client via LiveKit data channel for real-time display
- Add Deepgram-related settings (`DEEPGRAM_API_KEY`, `STT_LANGUAGE`, `STT_MODEL`) to agent configuration

## Capabilities

### New Capabilities
- `stt-deepgram`: Deepgram STT plugin integration — streaming recognition, language config, sentiment extraction, interim transcript delivery via data channel
- `agent-transcript-persistence`: Saving user voice transcripts and sentiment to the `messages` table from the agent process

### Modified Capabilities
- `agent-entrypoint`: The agent session must now include STT in its pipeline configuration alongside VAD

## Impact

- **Agent app** (`apps/agent/`): new STT plugin wiring, new DB write path for messages, data channel publishing
- **Dependencies**: `livekit-plugins-deepgram` added to `apps/agent/pyproject.toml`
- **Environment**: new required env var `DEEPGRAM_API_KEY`, optional `STT_LANGUAGE`, `STT_MODEL`
- **Database**: no schema changes — `messages` table already has `content`, `voice_transcript`, `sentiment_raw` columns
- **Docker**: Dockerfile.agent unchanged (no model download needed for Deepgram — it's a cloud API)
