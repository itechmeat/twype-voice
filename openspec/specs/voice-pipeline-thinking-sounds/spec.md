## ADDED Requirements

### Requirement: Thinking sounds on LLM delay
The `TwypeAgent` SHALL override the `llm_node` method to detect LLM response delay and yield filler text before the actual LLM response stream. When the first LLM token takes longer than `THINKING_SOUNDS_DELAY` seconds, the agent SHALL yield a short filler phrase that passes through the TTS pipeline for natural vocalization.

#### Scenario: LLM responds within delay threshold
- **WHEN** the LLM produces its first token within `THINKING_SOUNDS_DELAY` seconds
- **THEN** no filler text is generated, and the LLM response streams normally

#### Scenario: LLM response delayed beyond threshold
- **WHEN** the LLM first token takes longer than `THINKING_SOUNDS_DELAY` seconds
- **THEN** a filler phrase is yielded to TTS before the LLM response begins streaming

#### Scenario: Filler stops when LLM responds
- **WHEN** a filler phrase has been yielded and the LLM begins streaming
- **THEN** the LLM response stream continues normally after the filler, with no overlap

### Requirement: Language-adaptive filler phrases
Filler phrases SHALL be selected based on the current session language. The agent SHALL maintain a mapping of filler phrases per language (at minimum `"ru"` and `"en"`). Filler phrases SHALL sound natural in conversational speech.

#### Scenario: Russian filler phrase
- **WHEN** the session language is `"ru"` and LLM delay exceeds threshold
- **THEN** the filler phrase is in Russian (e.g., "Хм, дайте подумать...")

#### Scenario: English filler phrase
- **WHEN** the session language is `"en"` and LLM delay exceeds threshold
- **THEN** the filler phrase is in English (e.g., "Hmm, let me think...")

#### Scenario: Unknown language falls back to English
- **WHEN** the session language is not in the filler phrase mapping
- **THEN** the English filler phrase is used

### Requirement: Thinking sounds configuration
The `AgentSettings` class SHALL include thinking sounds configuration: `THINKING_SOUNDS_ENABLED` (bool, default: `True`) and `THINKING_SOUNDS_DELAY` (float, default: `1.5`, gt: `0.0`).

#### Scenario: Thinking sounds enabled by default
- **WHEN** `THINKING_SOUNDS_ENABLED` is not set
- **THEN** thinking sounds are active with a delay threshold of 1.5 seconds

#### Scenario: Thinking sounds disabled
- **WHEN** `THINKING_SOUNDS_ENABLED=false`
- **THEN** `llm_node` passes through to the default LLM behavior without filler generation

#### Scenario: Custom delay threshold
- **WHEN** `THINKING_SOUNDS_DELAY=2.0`
- **THEN** filler phrases are generated only when LLM first token takes longer than 2.0 seconds

#### Scenario: Settings documented in .env.example
- **WHEN** a developer copies `.env.example` to `.env`
- **THEN** `THINKING_SOUNDS_ENABLED` and `THINKING_SOUNDS_DELAY` are present with descriptive comments
