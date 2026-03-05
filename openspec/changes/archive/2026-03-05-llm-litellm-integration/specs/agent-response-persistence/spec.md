## ADDED Requirements

### Requirement: Save agent responses to database
The agent SHALL save finalized LLM responses to the `messages` table in PostgreSQL. Each message record SHALL include: `session_id`, `role=assistant`, `mode=voice`, `content` (full response text).

#### Scenario: Agent response persisted
- **WHEN** the agent completes generating a response to the user
- **THEN** a new row is inserted into the `messages` table with `role=assistant`, `mode=voice`, and `content` set to the full response text

#### Scenario: Session ID associated with response
- **WHEN** the agent saves a response
- **THEN** the `session_id` on the message record matches the current LiveKit room's session

#### Scenario: Empty response not saved
- **WHEN** the agent generates an empty or whitespace-only response
- **THEN** no message record SHALL be inserted

### Requirement: Response capture via AgentSession event
The agent SHALL listen to the `agent_speech_committed` event on `AgentSession` to capture the complete agent response text. This event fires after the response has been finalized.

#### Scenario: Speech committed event triggers persistence
- **WHEN** the `agent_speech_committed` event fires with response text
- **THEN** the agent persists the response text to the database

#### Scenario: Persistence failure does not crash agent
- **WHEN** the database insert fails (connection error, constraint violation)
- **THEN** the agent logs the error at ERROR level and continues processing
