## ADDED Requirements

### Requirement: Load prompt layers from database
The agent SHALL load all active prompt layers from the `agent_config` table where `is_active = true` and `key` matches one of the known prompt layer keys: `system_prompt`, `voice_prompt`, `dual_layer_prompt`, `emotion_prompt`, `crisis_prompt`, `rag_prompt`, `language_prompt`, `proactive_prompt`. The function SHALL return a dictionary mapping key to value.

#### Scenario: All 8 prompt layers are active
- **WHEN** the agent loads prompt layers and all 8 keys exist in `agent_config` with `is_active = true`
- **THEN** the returned dictionary SHALL contain all 8 key-value pairs

#### Scenario: Some prompt layers are inactive
- **WHEN** the agent loads prompt layers and `proactive_prompt` has `is_active = false`
- **THEN** the returned dictionary SHALL contain only the 7 active layers, excluding `proactive_prompt`

#### Scenario: Database is unreachable
- **WHEN** the agent attempts to load prompt layers and the database connection fails
- **THEN** the function SHALL raise an exception (handled by the caller)

### Requirement: Build instructions from prompt layers
The agent SHALL assemble a single instructions string from loaded prompt layers in a fixed order: `system_prompt`, `voice_prompt`, `language_prompt`, `dual_layer_prompt`, `emotion_prompt`, `crisis_prompt`, `rag_prompt`, `proactive_prompt`. Each layer's value SHALL be separated by two newlines. Layers not present in the input dictionary SHALL be skipped.

#### Scenario: All layers present
- **WHEN** `build_instructions` is called with all 8 layers
- **THEN** the resulting string SHALL contain all 8 layer values separated by double newlines, in the defined order

#### Scenario: Only system_prompt present
- **WHEN** `build_instructions` is called with only `system_prompt` in the dictionary
- **THEN** the resulting string SHALL contain only the `system_prompt` value with no trailing separators

#### Scenario: Empty dictionary
- **WHEN** `build_instructions` is called with an empty dictionary
- **THEN** the resulting string SHALL be empty

### Requirement: Fixed layer ordering constant
The module SHALL define a `PROMPT_LAYER_ORDER` constant listing all 8 prompt layer keys in their assembly order. This constant SHALL be the single source of truth for layer ordering and for the set of known prompt layer keys.

#### Scenario: Layer order is consistent
- **WHEN** code references `PROMPT_LAYER_ORDER`
- **THEN** it SHALL return `["system_prompt", "voice_prompt", "language_prompt", "dual_layer_prompt", "emotion_prompt", "crisis_prompt", "rag_prompt", "proactive_prompt"]`

### Requirement: Fallback system prompt
The module SHALL define a `FALLBACK_SYSTEM_PROMPT` constant containing a basic system prompt text. This constant SHALL be used when prompt loading from the database fails.

#### Scenario: Fallback prompt content
- **WHEN** the fallback prompt is used
- **THEN** it SHALL instruct the agent to match the user's language, keep responses brief, and be helpful

### Requirement: Prompt layers injected into TwypeAgent
The `TwypeAgent` SHALL accept dynamic instructions built from database prompt layers instead of a hardcoded `SYSTEM_PROMPT` constant. The instructions string SHALL be passed via the `instructions` parameter in the constructor.

#### Scenario: Agent created with database-sourced instructions
- **WHEN** the entrypoint creates a `TwypeAgent` with instructions loaded from the database
- **THEN** the agent's `instructions` SHALL contain the assembled multi-layer prompt

#### Scenario: Agent created with fallback instructions
- **WHEN** prompt loading fails and the entrypoint falls back
- **THEN** the agent's `instructions` SHALL contain the `FALLBACK_SYSTEM_PROMPT`
