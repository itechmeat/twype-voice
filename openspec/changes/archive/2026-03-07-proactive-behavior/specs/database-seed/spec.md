## MODIFIED Requirements

### Requirement: Seed agent config
The seed script SHALL create AgentConfig records for all prompt layers: `system_prompt`, `voice_prompt`, `dual_layer_prompt`, `emotion_prompt`, `crisis_prompt`, `rag_prompt`, `language_prompt`, `proactive_prompt`. Each record SHALL contain a meaningful prompt text in English that reflects the layer's purpose. The `proactive_prompt` SHALL be a template string containing `{proactive_type}` and `{emotional_context}` placeholders. The template SHALL instruct the LLM to generate a brief, natural follow-up when `proactive_type` is `follow_up`, and a gentle, emotionally-aware check-in when `proactive_type` is `extended_silence`. The template SHALL reference the provided emotional context to adapt the tone.

#### Scenario: Agent prompts seeded with meaningful content
- **WHEN** seed script runs
- **THEN** 8 AgentConfig records SHALL exist with `is_active = true`, one for each prompt layer, each containing a substantive English-language prompt (not a placeholder)

#### Scenario: Proactive prompt contains template placeholders
- **WHEN** the `proactive_prompt` AgentConfig record is read
- **THEN** it SHALL contain `{proactive_type}` and `{emotional_context}` placeholder strings

#### Scenario: Proactive prompt template renders correctly
- **WHEN** the seeded `proactive_prompt` value is used with `str.format_map({"proactive_type": "follow_up", "emotional_context": "neutral"})`
- **THEN** rendering succeeds without errors and produces a coherent instruction string
