## MODIFIED Requirements

### Requirement: Get session messages
The system SHALL return all messages for a given session when calling `GET /sessions/{id}/messages`. Only the session owner SHALL have access. Messages SHALL be sorted by `created_at` ascending. Each message item SHALL include `source_ids` (list of UUID strings or null) from the `messages.source_ids` column.

#### Scenario: Owner requests messages
- **WHEN** authenticated user sends `GET /sessions/{id}/messages` for their own session
- **THEN** system returns 200 with a list of messages including `id`, `role`, `mode`, `content`, `source_ids`, `created_at`

#### Scenario: Session not found or not owned
- **WHEN** authenticated user sends `GET /sessions/{id}/messages` for a session that does not exist or belongs to another user
- **THEN** system returns 404 Not Found

#### Scenario: Session has no messages
- **WHEN** authenticated user requests messages for a session with no messages
- **THEN** system returns 200 with an empty list

#### Scenario: Message with source IDs
- **WHEN** a message has `source_ids=["uuid-1", "uuid-2"]`
- **THEN** the message item SHALL include `source_ids: ["uuid-1", "uuid-2"]`

#### Scenario: Message without source IDs
- **WHEN** a message has `source_ids=null` (user message or assistant message without RAG references)
- **THEN** the message item SHALL include `source_ids: null`
