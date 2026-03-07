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
