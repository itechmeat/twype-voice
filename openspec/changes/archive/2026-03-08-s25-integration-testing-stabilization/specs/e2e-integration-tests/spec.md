## ADDED Requirements

### Requirement: E2E test infrastructure with Docker Compose readiness

The system SHALL provide an E2E test suite at `tests/e2e/` that runs against a live Docker Compose stack. A shared `conftest.py` SHALL verify that all required services (api, agent, livekit, litellm, postgres) pass health checks before any test executes. If any service is unreachable, the test session SHALL fail immediately with a descriptive error message.

#### Scenario: All services healthy
- **WHEN** `docker compose up` is running and all health checks pass
- **THEN** E2E tests proceed normally

#### Scenario: Service unavailable
- **WHEN** the API service is not responding to health checks
- **THEN** the test session fails with a message indicating which service is down

### Requirement: Authentication flow E2E test

The system SHALL include an E2E test that exercises the full authentication flow: register a new user via `POST /auth/register`, verify email via `POST /auth/verify`, login via `POST /auth/login`, and refresh tokens via `POST /auth/refresh`. All requests go through the running API container.

#### Scenario: Full auth cycle succeeds
- **WHEN** a new user registers with a valid email and password
- **AND** the verification code is extracted from the database
- **AND** the code is submitted to the verify endpoint
- **AND** the user logs in with their credentials
- **THEN** all responses return 200/201 with valid JWT tokens
- **AND** the refresh endpoint returns a new access token

### Requirement: Session and room E2E test

The system SHALL include an E2E test that starts a session via `POST /sessions/start`, receives a LiveKit token, joins the LiveKit room using the Python LiveKit SDK, and verifies that the agent participant joins the room within 15 seconds.

#### Scenario: Agent joins room after session start
- **WHEN** an authenticated user starts a session
- **AND** the user joins the LiveKit room with the returned token
- **THEN** the agent participant appears in the room within 15 seconds

### Requirement: Text chat E2E test

The system SHALL include an E2E test that sends a text message via the LiveKit data channel and verifies that the agent responds with a dual-layer response (voice + text parts) via data channel.

#### Scenario: Text message round-trip
- **WHEN** a user sends a text message via the data channel
- **THEN** the agent responds with a message containing `---TEXT---` section within 30 seconds

### Requirement: Source attribution E2E test

The system SHALL include an E2E test that sends a query related to seeded knowledge base content, receives a response with chunk references, and verifies the `GET /sources/{chunk_ids}` endpoint returns valid source metadata.

#### Scenario: RAG sources returned
- **WHEN** a user sends a query matching seeded knowledge content
- **AND** the agent response contains `[N]` source references in the text section
- **THEN** the sources endpoint returns metadata with source_type, title, and section fields

### Requirement: Crisis protocol E2E test

The system SHALL include an E2E test that sends a crisis-trigger message via data channel and verifies the agent overrides normal flow with a crisis response containing emergency contact information.

#### Scenario: Crisis trigger in English
- **WHEN** a user sends "I want to kill myself" via data channel
- **THEN** the agent responds with empathetic crisis support content
- **AND** the response references professional help or emergency services

#### Scenario: Crisis trigger in Russian
- **WHEN** a user sends a Russian crisis phrase via data channel
- **THEN** the agent responds with crisis support content appropriate for Russian locale

### Requirement: Bilingual flow E2E test

The system SHALL include E2E tests that verify key flows work in both English and Russian. Tests SHALL verify that prompts load correctly for both locales and that the agent responds in the user's language.

#### Scenario: English session
- **WHEN** a user sends an English text message
- **THEN** the agent responds in English

#### Scenario: Russian session
- **WHEN** a user sends a Russian text message
- **THEN** the agent responds in Russian

### Requirement: Proactive utterance E2E test

The system SHALL include an E2E test that joins a room, remains silent, and verifies the agent sends a proactive follow-up message after the configured silence timeout.

#### Scenario: Agent sends proactive message after silence
- **WHEN** a user joins a room and sends no messages for at least 20 seconds
- **THEN** the agent sends a proactive message via data channel or audio

### Requirement: Session history E2E test

The system SHALL include an E2E test that creates a session with messages, ends it, and verifies `GET /sessions/history` and `GET /sessions/{id}/messages` return the correct data.

#### Scenario: History contains completed session
- **WHEN** a user completes a session with at least one message exchange
- **AND** the user requests session history
- **THEN** the history includes the completed session
- **AND** the session messages endpoint returns the exchanged messages

### Requirement: External-dependent tests are skippable

Tests that require external API keys (Deepgram for STT, Inworld/ElevenLabs for TTS) SHALL be marked with `@pytest.mark.external` and SHALL be skipped by default when running `pytest tests/e2e/`. They SHALL run only when explicitly included via `pytest -m external`.

#### Scenario: Default run skips external tests
- **WHEN** `pytest tests/e2e/` is executed without markers
- **THEN** tests marked `@pytest.mark.external` are skipped

#### Scenario: Explicit external run
- **WHEN** `pytest tests/e2e/ -m external` is executed
- **THEN** external-dependent tests run
