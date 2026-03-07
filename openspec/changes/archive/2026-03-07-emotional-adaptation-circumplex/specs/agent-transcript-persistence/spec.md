## MODIFIED Requirements

### Requirement: Save user voice transcripts to database
The agent SHALL save final user transcripts to the `messages` table in PostgreSQL. Each message record SHALL include: `session_id`, `role=user`, `mode` (determined by the input source), `content` (final transcript text), `voice_transcript` (raw transcript for voice, NULL for text), `sentiment_raw` (Deepgram sentiment score or null), `valence` (float or null from emotional analysis), and `arousal` (float or null from emotional analysis). The `save_transcript` function SHALL accept optional `mode`, `valence`, and `arousal` parameters. The `mode` parameter defaults to `"voice"`.

#### Scenario: Final transcript persisted with emotional data
- **WHEN** a final transcript is received from STT and emotional analysis produces valence=-0.4 and arousal=0.7
- **THEN** the agent inserts a new row into the `messages` table with `role=user`, `mode=voice`, `content` set to the transcript text, `sentiment_raw` set to the extracted sentiment score, `valence=-0.4`, and `arousal=0.7`

#### Scenario: Final transcript persisted without emotional data
- **WHEN** a final transcript is received and emotional analysis is unavailable
- **THEN** the agent inserts a new row with `valence=NULL` and `arousal=NULL`

#### Scenario: Text message persisted via save_transcript
- **WHEN** `save_transcript` is called with `mode="text"` and optional valence/arousal
- **THEN** the agent inserts a new row into the `messages` table with `role=user`, `mode=text`, `voice_transcript=NULL`, and the provided valence/arousal values (or NULL if not provided)

#### Scenario: Session ID associated with message
- **WHEN** the agent saves a transcript
- **THEN** the `session_id` on the message record matches the current LiveKit room's session

#### Scenario: Empty transcript not saved
- **WHEN** a final transcript is received with empty or whitespace-only text
- **THEN** the agent SHALL NOT insert a message record
