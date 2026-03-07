## MODIFIED Requirements

### Requirement: Save agent responses to database
The agent SHALL save finalized LLM responses to the `messages` table in PostgreSQL. Each message record SHALL include: `session_id`, `role=assistant`, `mode` (current mode from ModeContext), `content` (full response text including both voice and text parts before delimiter removal). When a `DualLayerResult` is available, the `source_ids` field SHALL be populated with `all_chunk_ids` (deduplicated list of referenced RAG chunk UUIDs as strings). When no dual-layer result is available or `all_chunk_ids` is empty, `source_ids` SHALL be `NULL`.

#### Scenario: Agent response persisted with source IDs
- **WHEN** the agent completes a dual-layer response referencing RAG chunks [1] and [3] from a 4-chunk context
- **THEN** a new row is inserted into `messages` with `role=assistant`, `content` set to the full response text, and `source_ids` set to a JSON array containing the UUIDs of chunks 1 and 3

#### Scenario: Agent response persisted without source IDs
- **WHEN** the agent completes a response with no RAG chunk references (no text part or no [N] markers)
- **THEN** a new row is inserted into `messages` with `source_ids=NULL`

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

### Requirement: Pass dual-layer result to persistence layer
The agent SHALL make the latest `DualLayerResult` available to the response persistence handler so that `source_ids` can be extracted. The result SHALL be stored on the agent instance and reset per turn.

#### Scenario: Dual-layer result available at persistence time
- **WHEN** the LLM produces a dual-layer response and the speech committed event fires
- **THEN** the persistence handler SHALL read `all_chunk_ids` from the stored `DualLayerResult`

#### Scenario: No dual-layer result available
- **WHEN** the LLM produces a plain response (no delimiters) and the speech committed event fires
- **THEN** the persistence handler SHALL save with `source_ids=NULL`
