## MODIFIED Requirements

### Requirement: Build instructions from prompt layers
The agent SHALL assemble a single instructions string from loaded prompt layers in a fixed order: `system_prompt`, `voice_prompt`, `language_prompt`, `dual_layer_prompt`, `emotion_prompt`, `crisis_prompt`, `rag_prompt`, `proactive_prompt`. Each layer's value SHALL be separated by two newlines. Layers not present in the input dictionary SHALL be skipped. The `emotion_prompt` layer SHALL be treated as a template string supporting Python `str.format_map()` placeholders for dynamic emotional context injection at runtime. The `build_instructions` function itself does NOT perform template rendering — it assembles the raw template. Template rendering is performed separately per turn.

#### Scenario: All layers present
- **WHEN** `build_instructions` is called with all 8 layers
- **THEN** the resulting string SHALL contain all 8 layer values separated by double newlines, in the defined order

#### Scenario: Only system_prompt present
- **WHEN** `build_instructions` is called with only `system_prompt` in the dictionary
- **THEN** the resulting string SHALL contain only the `system_prompt` value with no trailing separators

#### Scenario: Empty dictionary
- **WHEN** `build_instructions` is called with an empty dictionary
- **THEN** the resulting string SHALL be empty

#### Scenario: Emotion prompt contains template placeholders
- **WHEN** `build_instructions` is called with an `emotion_prompt` containing `{quadrant}` and `{valence}` placeholders
- **THEN** the resulting string SHALL contain the raw template placeholders (not rendered)

## ADDED Requirements

### Requirement: Render emotional context into instructions
The prompt module SHALL provide a `render_emotional_context` function that takes the assembled instructions string and an `EmotionalState` object, and returns a new instructions string with all emotional template placeholders replaced by current values. The function SHALL replace: `{quadrant}`, `{valence}`, `{arousal}`, `{trend_valence}`, `{trend_arousal}`, `{tone_guidance}`. If the instructions contain no emotional placeholders, it SHALL return the original string unchanged.

#### Scenario: Successful template rendering
- **WHEN** `render_emotional_context` is called with instructions containing `{quadrant}` and an EmotionalState with quadrant="distress"
- **THEN** the returned string has `{quadrant}` replaced with "distress"

#### Scenario: All placeholders rendered
- **WHEN** instructions contain `{quadrant}`, `{valence}`, `{arousal}`, `{trend_valence}`, `{trend_arousal}`, `{tone_guidance}`
- **THEN** all six placeholders are replaced with corresponding EmotionalState values and tone guidance string

#### Scenario: No placeholders in instructions
- **WHEN** `render_emotional_context` is called with instructions that contain no curly-brace placeholders
- **THEN** the original string is returned unchanged

#### Scenario: Rendering failure
- **WHEN** template rendering raises a KeyError or ValueError (e.g., malformed template)
- **THEN** the function returns the original instructions string unchanged and logs a warning

### Requirement: Emotional context injection in mode-aware chat context
The `TwypeAgent` SHALL render emotional context into the instructions before building the mode-aware chat context for each LLM call. If no EmotionalState is available (first turn, analyzer not ready), the raw template placeholders SHALL be replaced with neutral defaults (quadrant="neutral", valence=0.0, arousal=0.0, trends="stable", tone_guidance for neutral).

#### Scenario: Emotional context injected before LLM call
- **WHEN** the agent builds the chat context for an LLM call and an EmotionalState is available
- **THEN** the system instructions contain the rendered emotional context with current valence, arousal, quadrant, and trends

#### Scenario: No emotional state available (first turn)
- **WHEN** the agent builds the chat context and no EmotionalState has been computed yet
- **THEN** the system instructions contain neutral defaults for all emotional placeholders
