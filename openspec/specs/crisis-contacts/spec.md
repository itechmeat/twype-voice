## ADDED Requirements

### Requirement: Crisis contacts database table
The system SHALL provide a `crisis_contacts` table with columns: `id` (UUID, primary key), `language` (varchar, ISO 639-1 code), `locale` (varchar, optional, e.g., "RU", "US"), `contact_type` (varchar: `emergency_services`, `suicide_hotline`, `crisis_helpline`, `domestic_violence`), `name` (varchar, contact name/organization), `phone` (varchar, nullable), `url` (varchar, nullable), `description` (text), `priority` (integer, for display ordering), `is_active` (boolean, default true), `created_at` (timestamptz), `updated_at` (timestamptz). Index naming SHALL follow the project convention: `ix_crisis_contacts_{column}`.

#### Scenario: Table created via migration
- **WHEN** the Alembic migration runs
- **THEN** the `crisis_contacts` table is created with all specified columns and indexes on `language` and `contact_type`

#### Scenario: Composite index for locale lookup
- **WHEN** the migration runs
- **THEN** a composite index `ix_crisis_contacts_language_locale` is created on (`language`, `locale`)

### Requirement: Crisis contacts seed data
The seed script SHALL populate `crisis_contacts` with initial data for Russian and English locales. Russian contacts SHALL include at minimum: emergency services (112), psychological crisis helpline (8-800-2000-122), and a suicide prevention hotline. English contacts SHALL include at minimum: emergency services (911), National Suicide Prevention Lifeline (988), and Crisis Text Line (text HOME to 741741).

#### Scenario: Russian contacts seeded
- **WHEN** the seed script runs
- **THEN** at least 3 active Russian-language crisis contacts exist in the database

#### Scenario: English contacts seeded
- **WHEN** the seed script runs
- **THEN** at least 3 active English-language crisis contacts exist in the database

#### Scenario: Seed is idempotent
- **WHEN** the seed script runs multiple times
- **THEN** contacts are upserted (no duplicates created)

### Requirement: Crisis contacts session-level caching
The agent SHALL fetch active crisis contacts for the session's language at session start and cache them in memory. The cache SHALL be used during crisis events without additional database queries.

#### Scenario: Contacts cached on session start
- **WHEN** a new agent session starts with language `ru`
- **THEN** all active Russian crisis contacts are fetched from the database and cached

#### Scenario: Cached contacts used during crisis
- **WHEN** a crisis event is triggered during a session
- **THEN** emergency contacts are retrieved from the session cache (no database query)

#### Scenario: Fallback to English contacts
- **WHEN** no crisis contacts exist for the session's language
- **THEN** the agent falls back to English (`en`) contacts

### Requirement: Crisis contacts API endpoint
The API SHALL provide a `GET /crisis-contacts` endpoint that returns active crisis contacts filtered by language query parameter. The endpoint SHALL NOT require authentication (emergency information must be publicly accessible).

#### Scenario: Fetch contacts by language
- **WHEN** a GET request is made to `/crisis-contacts?language=ru`
- **THEN** the response contains all active Russian crisis contacts ordered by priority

#### Scenario: No contacts for language
- **WHEN** a GET request is made to `/crisis-contacts?language=fr` and no French contacts exist
- **THEN** the response contains English contacts as fallback

#### Scenario: Endpoint is public
- **WHEN** a GET request is made to `/crisis-contacts` without an Authorization header
- **THEN** the request succeeds (no 401/403)
