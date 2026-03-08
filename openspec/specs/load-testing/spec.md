## ADDED Requirements

### Requirement: Locust load test for concurrent sessions

The system SHALL provide a Locust-based load test at `tests/load/locustfile.py` that simulates 30 concurrent users. Each simulated user SHALL authenticate, start a session, send text messages via the API (simulating data channel flow), and end the session.

#### Scenario: 30 concurrent users sustained for 5 minutes
- **WHEN** the load test runs with 30 users for 5 minutes
- **THEN** the aggregate error rate SHALL be below 5%
- **AND** p95 API response time SHALL be below 500ms for auth and session endpoints

### Requirement: Custom LiveKit load user

The system SHALL provide a custom Locust User class at `tests/load/livekit_user.py` that wraps LiveKit SDK operations (room join, data channel send/receive) as Locust tasks with proper timing instrumentation.

#### Scenario: LiveKit operations are instrumented
- **WHEN** a Locust user joins a room and sends a data channel message
- **THEN** the join time and message round-trip time are recorded as Locust request metrics

### Requirement: Load test documentation

The system SHALL provide a `tests/load/README.md` with instructions for running load tests, including prerequisites (Docker Compose running, Locust installed), command examples, and how to interpret results.

#### Scenario: README contains run instructions
- **WHEN** a developer reads `tests/load/README.md`
- **THEN** they find commands to start Locust in headless and web UI modes
- **AND** they find the expected performance targets
