## ADDED Requirements

### Requirement: Save user voice transcripts to database
The agent SHALL save final user transcripts to the `messages` table in PostgreSQL. Each message record SHALL include: `session_id`, `role=user`, `mode` (determined by the input source), `content` (final transcript text), `voice_transcript` (raw transcript for voice, NULL for text), and `sentiment_raw` (Deepgram sentiment score or null). The `save_transcript` function SHALL accept an optional `mode` parameter defaulting to `"voice"`.

#### Scenario: Final transcript persisted
- **WHEN** a final transcript is received from STT
- **THEN** the agent inserts a new row into the `messages` table with `role=user`, `mode=voice`, `content` set to the transcript text, and `sentiment_raw` set to the extracted sentiment score

#### Scenario: Text message persisted via save_transcript
- **WHEN** `save_transcript` is called with `mode="text"`
- **THEN** the agent inserts a new row into the `messages` table with `role=user`, `mode=text`, `voice_transcript=NULL`

#### Scenario: Session ID associated with message
- **WHEN** the agent saves a transcript
- **THEN** the `session_id` on the message record matches the current LiveKit room's session

#### Scenario: Empty transcript not saved
- **WHEN** a final transcript is received with empty or whitespace-only text
- **THEN** the agent SHALL NOT insert a message record

### Requirement: Save assistant responses to database
The `save_agent_response` function SHALL accept an optional `mode` parameter defaulting to `"voice"`. The saved message record SHALL use the provided mode value.

#### Scenario: Voice assistant response persisted
- **WHEN** `save_agent_response` is called without a `mode` parameter
- **THEN** the message is saved with `mode=voice`

#### Scenario: Text assistant response persisted
- **WHEN** `save_agent_response` is called with `mode="text"`
- **THEN** the message is saved with `mode=text`

### Requirement: Database connection from agent
The agent SHALL connect to PostgreSQL using `DATABASE_URL` from environment variables. The connection SHALL use async SQLAlchemy with the same models defined in the API app.

#### Scenario: DATABASE_URL configured
- **WHEN** `DATABASE_URL` is set in the agent's environment
- **THEN** the agent establishes an async connection pool to PostgreSQL

#### Scenario: DATABASE_URL not set
- **WHEN** `DATABASE_URL` is not set
- **THEN** the agent fails to start with a validation error

#### Scenario: Database write failure
- **WHEN** the agent fails to insert a message record (connection error, constraint violation)
- **THEN** the agent logs the error at ERROR level and continues processing (does not crash)


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
