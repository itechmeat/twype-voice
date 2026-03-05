## ADDED Requirements

### Requirement: Save config snapshot at session start
The agent SHALL save a snapshot of the loaded prompt layers to the `sessions.agent_config_snapshot` JSONB column when a session starts. The snapshot SHALL be a JSON object where keys are prompt layer keys and values are prompt layer texts. The snapshot SHALL also include a `_version` key mapping each layer key to its `version` from `agent_config`.

#### Scenario: Snapshot saved successfully
- **WHEN** the agent loads prompt layers and has a valid `db_session_id`
- **THEN** the agent SHALL UPDATE the `sessions` row with `agent_config_snapshot` containing the loaded layers and their versions

#### Scenario: Session ID not found
- **WHEN** the agent cannot resolve the session ID (db_session_id is None)
- **THEN** the snapshot SHALL NOT be saved and the agent SHALL log a warning

#### Scenario: Snapshot write fails
- **WHEN** the UPDATE query fails due to a database error
- **THEN** the agent SHALL log the error at ERROR level and continue operating with the loaded prompts (the session is not aborted)

### Requirement: Session uses frozen config
The agent SHALL use the prompt layers loaded at session start for the entire session duration. The agent SHALL NOT re-query `agent_config` during the session. The loaded instructions string is immutable once passed to `TwypeAgent`.

#### Scenario: Config changes during active session
- **WHEN** an administrator updates a prompt layer in `agent_config` while a session is active
- **THEN** the active session SHALL continue using the original prompt layers from session start

### Requirement: Snapshot includes metadata
The snapshot JSON SHALL include a `_meta` key with `snapshot_at` (ISO 8601 timestamp) indicating when the snapshot was taken.

#### Scenario: Snapshot metadata format
- **WHEN** a snapshot is saved
- **THEN** the `_meta.snapshot_at` value SHALL be a valid ISO 8601 datetime string
