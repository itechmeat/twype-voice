## ADDED Requirements

### Requirement: Generate LiveKit access token
The system SHALL generate a LiveKit access token using the `livekit-api` SDK. The token SHALL be signed with `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` from environment variables. The token SHALL grant the following permissions: `room_join = True`, `room = <room_name>`, `can_publish = True`, `can_subscribe = True`, `can_publish_data = True`.

#### Scenario: Token generation with correct grants
- **WHEN** system generates a LiveKit token for a user and room
- **THEN** the token contains `VideoGrants` with `room_join`, `can_publish`, `can_subscribe`, `can_publish_data` all set to True, and `room` set to the session's `room_name`

#### Scenario: Token identity
- **WHEN** system generates a LiveKit token
- **THEN** the token identity SHALL be set to the user's UUID string

#### Scenario: Token TTL
- **WHEN** system generates a LiveKit token
- **THEN** the token SHALL have a TTL of 6 hours

### Requirement: LiveKit configuration from environment
The system SHALL read `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` from environment variables via Pydantic Settings. The application SHALL fail to start if these variables are missing.

#### Scenario: Variables present
- **WHEN** `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` are set in the environment
- **THEN** the token generation module initializes successfully

#### Scenario: Variables missing
- **WHEN** `LIVEKIT_API_KEY` or `LIVEKIT_API_SECRET` is not set
- **THEN** the application raises a validation error at startup

### Requirement: Token module isolation
The LiveKit token generation SHALL be implemented in a dedicated module (`src/sessions/livekit.py`) with a pure function signature accepting `identity`, `room_name`, `api_key`, `api_secret` parameters. This module SHALL NOT depend on FastAPI or database imports.

#### Scenario: Standalone usage
- **WHEN** the `create_livekit_token` function is called with valid parameters
- **THEN** it returns a JWT string without requiring FastAPI request context or database session
