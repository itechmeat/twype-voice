## ADDED Requirements

### Requirement: Alembic infrastructure
The system SHALL have Alembic configured in `apps/api/migrations/` with `alembic.ini` and `env.py` supporting async SQLAlchemy (asyncpg). The Alembic `env.py` SHALL import all models to enable autogenerate. The `alembic.ini` SHALL read `sqlalchemy.url` from the `DATABASE_URL` environment variable.

#### Scenario: Generate migration from model changes
- **WHEN** a developer runs `alembic revision --autogenerate -m "description"`
- **THEN** Alembic SHALL detect model changes and generate a migration file in `apps/api/migrations/versions/`

### Requirement: pgvector extension
The initial migration SHALL enable the pgvector extension via `CREATE EXTENSION IF NOT EXISTS vector` before creating any tables that use vector columns.

#### Scenario: Fresh database setup
- **WHEN** `alembic upgrade head` is run against an empty database
- **THEN** the pgvector extension SHALL be enabled and all tables with vector columns SHALL be created successfully

### Requirement: Initial migration
The system SHALL include an initial migration that creates all tables defined in the models: `users`, `sessions`, `messages`, `knowledge_sources`, `knowledge_chunks`, `agent_config`, `tts_config`. The migration SHALL be forward-only (downgrade MAY raise NotImplementedError).

#### Scenario: Apply initial migration
- **WHEN** `alembic upgrade head` is run on an empty database
- **THEN** all 7 tables SHALL be created with correct columns, types, indexes, and foreign keys

#### Scenario: Downgrade policy
- **WHEN** `alembic downgrade` is attempted
- **THEN** the migration MAY raise NotImplementedError (forward-only policy for MVP)

### Requirement: Migration runs before API start
The API container entrypoint SHALL run `alembic upgrade head` before starting the application server, ensuring the database schema is always up to date.

#### Scenario: API container startup
- **WHEN** the api Docker container starts
- **THEN** migrations SHALL be applied before uvicorn begins accepting requests
