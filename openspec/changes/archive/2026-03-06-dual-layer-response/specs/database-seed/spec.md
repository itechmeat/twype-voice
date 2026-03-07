## MODIFIED Requirements

### Requirement: Seed agent config
The seed script SHALL create AgentConfig records for all prompt layers: `system_prompt`, `voice_prompt`, `dual_layer_prompt`, `emotion_prompt`, `crisis_prompt`, `rag_prompt`, `language_prompt`, `proactive_prompt`. Each record SHALL contain a meaningful prompt text in Russian that reflects the layer's purpose. The `dual_layer_prompt` value SHALL instruct the LLM to structure responses using `---VOICE---` and `---TEXT---` delimiters, with the voice part containing 2-5 conversational sentences and the text part containing bullet points with `[N]` source references. It SHALL include a concrete example demonstrating the expected format with both referenced and unreferenced bullet points.

#### Scenario: Agent prompts seeded with meaningful content
- **WHEN** seed script runs
- **THEN** 8 AgentConfig records SHALL exist with `is_active = true`, one for each prompt layer, each containing a substantive Russian-language prompt (not a placeholder)

#### Scenario: Dual layer prompt contains format example
- **WHEN** the `dual_layer_prompt` AgentConfig record is read
- **THEN** it SHALL contain the `---VOICE---` and `---TEXT---` delimiters, `[N]` reference notation, and an example showing both sourced and reasoning bullet points
