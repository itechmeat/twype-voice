## ADDED Requirements

### Requirement: Save user voice transcripts to database
The agent SHALL save final user transcripts to the `messages` table in PostgreSQL. Each message record SHALL include: `session_id`, `role=user`, `mode=voice`, `content` (final transcript text), `voice_transcript` (raw transcript), and `sentiment_raw` (Deepgram sentiment score or null).

#### Scenario: Final transcript persisted
- **WHEN** a final transcript is received from STT
- **THEN** the agent inserts a new row into the `messages` table with `role=user`, `mode=voice`, `content` set to the transcript text, and `sentiment_raw` set to the extracted sentiment score

#### Scenario: Session ID associated with message
- **WHEN** the agent saves a transcript
- **THEN** the `session_id` on the message record matches the current LiveKit room's session

#### Scenario: Empty transcript not saved
- **WHEN** a final transcript is received with empty or whitespace-only text
- **THEN** the agent SHALL NOT insert a message record

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
