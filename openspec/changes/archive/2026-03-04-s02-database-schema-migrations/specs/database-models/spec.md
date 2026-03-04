## ADDED Requirements

### Requirement: SQLAlchemy Base class with naming convention
The system SHALL provide a declarative Base class with `MetaData` naming convention that automatically generates index, foreign key, unique and check constraint names following the project conventions: `ix_{table}_{column}`, `fk_{table}_{column}_{ref_table}`, `uq_{table}_{column}`, `ck_{table}_{description}`.

#### Scenario: Auto-generated constraint names
- **WHEN** a model defines a foreign key column `user_id` referencing `users` table in the `sessions` table
- **THEN** the foreign key constraint SHALL be named `fk_sessions_user_id_users`

#### Scenario: Auto-generated index names
- **WHEN** a model defines an indexed column `email` in the `users` table
- **THEN** the index SHALL be named `ix_users_email`

### Requirement: Users model
The system SHALL define a `User` model mapped to the `users` table with columns: `id` (UUID, PK, default uuid4), `email` (String(255), unique, indexed), `password_hash` (String(255)), `is_verified` (bool, default false), `verification_code` (String(6), nullable), `verification_expires_at` (datetime, nullable), `preferences` (JSONB, nullable), `created_at` (datetime, server_default now), `updated_at` (datetime, server_default now, onupdate now). All columns SHALL use `Mapped[type]` annotations.

#### Scenario: Create unverified user
- **WHEN** a new User record is inserted with email and password_hash
- **THEN** `is_verified` SHALL default to `false`, `id` SHALL be auto-generated as UUID, `created_at` and `updated_at` SHALL be set to current timestamp

### Requirement: Sessions model
The system SHALL define a `Session` model mapped to the `sessions` table with columns: `id` (UUID, PK), `user_id` (UUID, FK to users.id), `room_name` (String(255)), `status` (String(20), default "active"), `agent_config_snapshot` (JSONB, nullable), `started_at` (datetime, server_default now), `ended_at` (datetime, nullable). Session SHALL have a relationship to User.

#### Scenario: Start new session
- **WHEN** a new Session record is inserted with user_id and room_name
- **THEN** `status` SHALL default to "active", `started_at` SHALL be set to current timestamp, `ended_at` SHALL be null

### Requirement: Messages model
The system SHALL define a `Message` model mapped to the `messages` table with columns: `id` (UUID, PK), `session_id` (UUID, FK to sessions.id), `role` (String(20), "user" or "assistant"), `mode` (String(10), "voice" or "text"), `content` (Text), `voice_transcript` (Text, nullable), `sentiment_raw` (Float, nullable), `valence` (Float, nullable), `arousal` (Float, nullable), `source_ids` (JSONB, nullable), `created_at` (datetime, server_default now). Message SHALL have a relationship to Session.

#### Scenario: Save voice message with emotional data
- **WHEN** a Message is inserted with role="user", mode="voice", sentiment_raw=-0.3, valence=-0.4, arousal=0.8
- **THEN** all emotional fields SHALL be persisted and retrievable

#### Scenario: Save text message without emotional data
- **WHEN** a Message is inserted with role="user", mode="text" and no emotional fields
- **THEN** sentiment_raw, valence, arousal SHALL be null

### Requirement: Knowledge Sources model
The system SHALL define a `KnowledgeSource` model mapped to the `knowledge_sources` table with columns: `id` (UUID, PK), `source_type` (String(20), one of: book, video, podcast, article, post), `title` (String(500)), `author` (String(255), nullable), `url` (String(2048), nullable), `language` (String(10)), `tags` (JSONB, nullable), `created_at` (datetime, server_default now).

#### Scenario: Create book source
- **WHEN** a KnowledgeSource is inserted with source_type="book", title, author, language="ru"
- **THEN** the record SHALL be persisted with all fields

### Requirement: Knowledge Chunks model
The system SHALL define a `KnowledgeChunk` model mapped to the `knowledge_chunks` table with columns: `id` (UUID, PK), `source_id` (UUID, FK to knowledge_sources.id), `content` (Text), `section` (String(500), nullable), `page_range` (String(50), nullable), `embedding` (Vector, nullable), `search_vector` (TSVector, nullable), `token_count` (Integer, nullable), `created_at` (datetime, server_default now). KnowledgeChunk SHALL have a relationship to KnowledgeSource.

#### Scenario: Store chunk with embedding
- **WHEN** a KnowledgeChunk is inserted with content, embedding vector and search_vector
- **THEN** the vector SHALL be stored in pgvector format and be queryable via cosine distance

### Requirement: Agent Config model
The system SHALL define an `AgentConfig` model mapped to the `agent_config` table with columns: `id` (UUID, PK), `key` (String(100), unique), `value` (Text), `version` (Integer, default 1), `is_active` (bool, default true), `created_at` (datetime, server_default now), `updated_at` (datetime, server_default now, onupdate now).

#### Scenario: Store system prompt
- **WHEN** an AgentConfig is inserted with key="system_prompt", value containing prompt text
- **THEN** the record SHALL be persisted and retrievable by key

#### Scenario: Version increment
- **WHEN** an existing AgentConfig record is updated
- **THEN** `version` SHALL reflect the new version number and `updated_at` SHALL be updated

### Requirement: TTS Config model
The system SHALL define a `TTSConfig` model mapped to the `tts_config` table with columns: `id` (UUID, PK), `voice_id` (String(255)), `model_id` (String(100)), `expressiveness` (Float, default 0.5), `speed` (Float, default 1.0), `language` (String(10)), `is_active` (bool, default true), `created_at` (datetime, server_default now).

#### Scenario: Create TTS config for Russian voice
- **WHEN** a TTSConfig is inserted with voice_id, model_id="inworld-tts-1.5-max", language="ru"
- **THEN** `expressiveness` SHALL default to 0.5 and `speed` SHALL default to 1.0

### Requirement: Async database session factory
The system SHALL provide an `async_sessionmaker` factory configured with asyncpg driver, suitable for use in both api and agent apps. The factory SHALL use the `DATABASE_URL` environment variable for connection.

#### Scenario: Create async session
- **WHEN** application code requests a database session
- **THEN** the factory SHALL return an `AsyncSession` bound to the configured PostgreSQL database
