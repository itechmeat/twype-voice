## MODIFIED Requirements

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
