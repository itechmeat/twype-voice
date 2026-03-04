## ADDED Requirements

### Requirement: Seed script
The system SHALL provide a `scripts/seed.py` script that populates the database with initial development data. The script SHALL be idempotent — running it multiple times SHALL NOT create duplicate records (upsert by unique keys).

#### Scenario: Run seed on empty database
- **WHEN** `python scripts/seed.py` is run against a database with empty tables
- **THEN** test user, agent config records, and TTS config records SHALL be created

#### Scenario: Run seed on already seeded database
- **WHEN** `python scripts/seed.py` is run against a database that already contains seed data
- **THEN** existing records SHALL be updated (not duplicated) and no errors SHALL occur

### Requirement: Seed test user
The seed script SHALL create a test user with email `test@twype.local`, a known password hash, and `is_verified = true`.

#### Scenario: Test user creation
- **WHEN** seed script runs
- **THEN** a verified user with email `test@twype.local` SHALL exist in the `users` table

### Requirement: Seed agent config
The seed script SHALL create AgentConfig records for all prompt layers: `system_prompt`, `voice_prompt`, `dual_layer_prompt`, `emotion_prompt`, `crisis_prompt`, `rag_prompt`, `language_prompt`, `proactive_prompt`. Each record SHALL contain placeholder prompt text in Russian.

#### Scenario: Agent prompts seeded
- **WHEN** seed script runs
- **THEN** 8 AgentConfig records SHALL exist with `is_active = true`, one for each prompt layer

### Requirement: Seed TTS config
The seed script SHALL create a TTSConfig record for the default Inworld voice with Russian language.

#### Scenario: TTS config seeded
- **WHEN** seed script runs
- **THEN** a TTSConfig record SHALL exist with model_id containing "inworld", language="ru", and `is_active = true`
