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
The seed script SHALL create AgentConfig records for all prompt layers: `system_prompt`, `voice_prompt`, `dual_layer_prompt`, `emotion_prompt`, `crisis_prompt`, `rag_prompt`, `language_prompt`, `proactive_prompt`. Each record SHALL contain a meaningful prompt text in Russian that reflects the layer's purpose. The `system_prompt` SHALL define the agent's identity, expertise domain, and core behavioral rules. The `voice_prompt` SHALL instruct the agent to respond concisely in 2-5 sentences for voice mode. The `language_prompt` SHALL instruct the agent to match the user's language. The `dual_layer_prompt` SHALL instruct the LLM to structure responses using `---VOICE---` and `---TEXT---` delimiters, with the voice part containing 2-5 conversational sentences and the text part containing bullet points with `[N]` source references. It SHALL include a concrete example demonstrating the expected format with both referenced and unreferenced bullet points. The `emotion_prompt` SHALL instruct the agent to adapt tone based on emotional signals. The `crisis_prompt` SHALL define the crisis detection and response protocol. The `rag_prompt` SHALL instruct the agent on using knowledge base sources with attribution. The `proactive_prompt` SHALL instruct the agent on follow-up behavior during silence.

#### Scenario: Agent prompts seeded with meaningful content
- **WHEN** seed script runs
- **THEN** 8 AgentConfig records SHALL exist with `is_active = true`, one for each prompt layer, each containing a substantive Russian-language prompt (not a placeholder)

#### Scenario: System prompt content
- **WHEN** the `system_prompt` AgentConfig record is read
- **THEN** it SHALL contain the agent's name (Twype), its role as an expert assistant, and core behavioral rules

#### Scenario: Crisis prompt content
- **WHEN** the `crisis_prompt` AgentConfig record is read
- **THEN** it SHALL contain instructions to detect distress signals, respond with empathy, and recommend professional help

#### Scenario: Dual layer prompt contains format example
- **WHEN** the `dual_layer_prompt` AgentConfig record is read
- **THEN** it SHALL contain the `---VOICE---` and `---TEXT---` delimiters, `[N]` reference notation, and an example showing both sourced and reasoning bullet points

### Requirement: Seed TTS config
The seed script SHALL create a TTSConfig record for the default Inworld voice with Russian language.

#### Scenario: TTS config seeded
- **WHEN** seed script runs
- **THEN** a TTSConfig record SHALL exist with model_id containing "inworld", language="ru", and `is_active = true`

### Requirement: Seed sample knowledge source and chunks
The seed script SHALL create a sample `knowledge_sources` record and associated `knowledge_chunks` records with pre-computed embeddings for development and testing. The sample source SHALL be a short English-language article with at least 3 chunks containing substantive content.

#### Scenario: Knowledge source seeded
- **WHEN** `python scripts/seed.py` is run
- **THEN** a `knowledge_sources` record SHALL exist with `source_type='article'`, a meaningful title, `language='en'`, and `is_active` implied by presence

#### Scenario: Knowledge chunks seeded with embeddings
- **WHEN** `python scripts/seed.py` is run
- **THEN** at least 3 `knowledge_chunks` records SHALL exist for the sample source, each with non-empty `content`, a valid `embedding` vector of dimension 1536, and a populated `search_vector`

#### Scenario: Seed is idempotent for knowledge data
- **WHEN** `python scripts/seed.py` is run twice
- **THEN** the sample knowledge source and chunks SHALL not be duplicated
