## ADDED Requirements

### Requirement: Start session
The system SHALL create a new session and return a LiveKit access token when an authenticated user calls `POST /sessions/start`. The response SHALL include `session_id`, `room_name`, and `livekit_token`. The session record SHALL be persisted in the `sessions` table with status `active`.

#### Scenario: Successful session creation
- **WHEN** authenticated user sends `POST /sessions/start`
- **THEN** system creates a `sessions` row with `user_id` = current user, `status` = `active`, `room_name` = `session-{uuid}`, and returns 201 with `session_id`, `room_name`, `livekit_token`

#### Scenario: Unauthenticated request
- **WHEN** request to `POST /sessions/start` has no valid JWT
- **THEN** system returns 401 Unauthorized

### Requirement: List session history
The system SHALL return a paginated list of the current user's sessions when calling `GET /sessions/history`. Results SHALL be sorted by `started_at` descending. The endpoint SHALL accept `offset` (default 0) and `limit` (default 20, max 100) query parameters.

#### Scenario: User has sessions
- **WHEN** authenticated user sends `GET /sessions/history`
- **THEN** system returns 200 with a list of sessions belonging to the user, sorted by `started_at` desc, including `id`, `room_name`, `status`, `started_at`, `ended_at`

#### Scenario: Pagination
- **WHEN** authenticated user sends `GET /sessions/history?offset=10&limit=5`
- **THEN** system returns at most 5 sessions starting from offset 10, with a `total` count in the response

#### Scenario: No sessions
- **WHEN** authenticated user with no sessions sends `GET /sessions/history`
- **THEN** system returns 200 with an empty list and `total` = 0

#### Scenario: Limit exceeds maximum
- **WHEN** user sends `GET /sessions/history?limit=200`
- **THEN** system clamps `limit` to 100

### Requirement: Get session messages
The system SHALL return all messages for a given session when calling `GET /sessions/{id}/messages`. Only the session owner SHALL have access. Messages SHALL be sorted by `created_at` ascending.

#### Scenario: Owner requests messages
- **WHEN** authenticated user sends `GET /sessions/{id}/messages` for their own session
- **THEN** system returns 200 with a list of messages including `id`, `role`, `mode`, `content`, `created_at`

#### Scenario: Session not found or not owned
- **WHEN** authenticated user sends `GET /sessions/{id}/messages` for a session that does not exist or belongs to another user
- **THEN** system returns 404 Not Found

#### Scenario: Session has no messages
- **WHEN** authenticated user requests messages for a session with no messages
- **THEN** system returns 200 with an empty list

### Requirement: Sessions router registration
The sessions router SHALL be registered in the FastAPI application at the `/sessions` prefix with the `sessions` tag.

#### Scenario: Router is accessible
- **WHEN** the API starts
- **THEN** endpoints `/sessions/start`, `/sessions/history`, `/sessions/{id}/messages` are available and documented in OpenAPI schema
