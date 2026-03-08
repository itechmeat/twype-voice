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
The seed script SHALL create AgentConfig records for all prompt layers: `system_prompt`, `voice_prompt`, `dual_layer_prompt`, `emotion_prompt`, `crisis_prompt`, `rag_prompt`, `language_prompt`, `proactive_prompt`. Each record SHALL contain a meaningful prompt text in English that reflects the layer's purpose. The `system_prompt` SHALL define the agent's identity, expertise domain, and core behavioral rules. The `voice_prompt` SHALL instruct the agent to respond concisely in 2-5 sentences for voice mode. The `language_prompt` SHALL instruct the agent to match the user's language. The `dual_layer_prompt` SHALL instruct the LLM to structure responses using `---VOICE---` and `---TEXT---` delimiters, with the voice part containing 2-5 conversational sentences and the text part containing bullet points with `[N]` source references. It SHALL include a concrete example demonstrating the expected format with both referenced and unreferenced bullet points. The `emotion_prompt` SHALL instruct the agent to adapt tone based on emotional signals. The `crisis_prompt` SHALL define the crisis detection and response protocol. The `rag_prompt` SHALL instruct the agent on using knowledge base sources with attribution. The `proactive_prompt` SHALL be a template string containing `{proactive_type}` and `{emotional_context}` placeholders. The template SHALL instruct the LLM to generate a brief, natural follow-up when `proactive_type` is `follow_up`, and a gentle, emotionally-aware check-in when `proactive_type` is `extended_silence`. The template SHALL reference the provided emotional context to adapt the tone.

#### Scenario: Agent prompts seeded with meaningful content
- **WHEN** seed script runs
- **THEN** 8 AgentConfig records SHALL exist with `is_active = true`, one for each prompt layer, each containing a substantive English-language prompt (not a placeholder)

#### Scenario: Proactive prompt contains template placeholders
- **WHEN** the `proactive_prompt` AgentConfig record is read
- **THEN** it SHALL contain `{proactive_type}` and `{emotional_context}` placeholder strings

#### Scenario: Proactive prompt template renders correctly
- **WHEN** the seeded `proactive_prompt` value is used with `str.format_map({"proactive_type": "follow_up", "emotional_context": "neutral"})`
- **THEN** rendering succeeds without errors and produces a coherent instruction string

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


## MODIFIED Requirements

### Requirement: Seed emotion_prompt as a template
The seed script SHALL insert an `emotion_prompt` entry into `agent_config` with a template string containing Circumplex emotional context placeholders. The template SHALL include `{quadrant}`, `{valence}`, `{arousal}`, `{trend_valence}`, `{trend_arousal}`, and `{tone_guidance}` placeholders. The template text SHALL instruct the LLM to adapt its response tone based on the user's current emotional state, describe the Circumplex quadrant system, and provide the current state values for reference. The seed SHALL be provided for at least `en` and `ru` locales.

#### Scenario: English emotion_prompt seed
- **WHEN** the seed script runs and inserts the `emotion_prompt` for locale `en`
- **THEN** the `agent_config` table contains an `emotion_prompt` row with English template text containing all six placeholders

#### Scenario: Russian emotion_prompt seed
- **WHEN** the seed script runs and inserts the `emotion_prompt` for locale `ru`
- **THEN** the `agent_config` table contains an `emotion_prompt` row with Russian template text containing all six placeholders

#### Scenario: Template placeholders are valid Python format strings
- **WHEN** the seeded `emotion_prompt` value is used with `str.format_map()` and a dict containing all six keys
- **THEN** rendering succeeds without errors

### Requirement: Complete Russian prompt translations

The seed script SHALL provide all prompt layers for the `ru` locale, not only `mode_voice_guidance` and `mode_text_guidance`. Missing translations SHALL be added for: `system_prompt`, `voice_prompt`, `dual_layer_prompt`, `emotion_prompt`, `crisis_prompt`, `rag_prompt`, `language_prompt`, `proactive_prompt`.

#### Scenario: All prompt layers seeded for Russian
- **WHEN** `scripts/seed.py` is executed
- **THEN** the `agent_configs` table contains entries for all prompt keys in the `ru` locale
- **AND** each Russian prompt is a meaningful adaptation (not a verbatim copy of the English text)

### Requirement: Production-quality English prompts

The seed script SHALL contain reviewed, production-quality English prompts. Prompts SHALL be clear, unambiguous, and free of placeholder or draft language.

#### Scenario: English prompts are complete
- **WHEN** `scripts/seed.py` is executed
- **THEN** all English prompt layers exist in `agent_configs`
- **AND** no prompt contains placeholder text like "TODO", "FIXME", or "TBD"

### Requirement: Crisis contacts accuracy

The seed script SHALL contain verified crisis contact information for both English (US) and Russian (RU) locales. Phone numbers and URLs SHALL be accurate.

#### Scenario: Crisis contacts are seeded for both locales
- **WHEN** `scripts/seed.py` is executed
- **THEN** `crisis_contacts` contains at least 3 entries per locale (en/US and ru/RU)
- **AND** each entry has a non-empty phone number and description
