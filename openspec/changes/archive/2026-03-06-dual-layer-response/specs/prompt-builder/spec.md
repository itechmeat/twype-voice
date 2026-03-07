## MODIFIED Requirements

### Requirement: Seed agent config
The seed script SHALL create AgentConfig records for all prompt layers: `system_prompt`, `voice_prompt`, `dual_layer_prompt`, `emotion_prompt`, `crisis_prompt`, `rag_prompt`, `language_prompt`, `proactive_prompt`. Each record SHALL contain a meaningful prompt text in Russian that reflects the layer's purpose. The `system_prompt` SHALL define the agent's identity, expertise domain, and core behavioral rules. The `voice_prompt` SHALL instruct the agent to respond concisely in 2-5 sentences for voice mode. The `language_prompt` SHALL instruct the agent to match the user's language. The `dual_layer_prompt` SHALL instruct the agent to produce structured dual-layer output using `---VOICE---` and `---TEXT---` delimiters: a voice part (2-5 conversational sentences) followed by a text part (bullet points with `[N]` source references matching RAG context order). It SHALL include a concrete example of the expected format. It SHALL instruct the agent to omit `[N]` markers for reasoning points not backed by sources. The `emotion_prompt` SHALL instruct the agent to adapt tone based on emotional signals. The `crisis_prompt` SHALL define the crisis detection and response protocol. The `rag_prompt` SHALL instruct the agent on using knowledge base sources with attribution. The `proactive_prompt` SHALL instruct the agent on follow-up behavior during silence.

#### Scenario: Agent prompts seeded with meaningful content
- **WHEN** seed script runs
- **THEN** 8 AgentConfig records SHALL exist with `is_active = true`, one for each prompt layer, each containing a substantive Russian-language prompt (not a placeholder)

#### Scenario: System prompt content
- **WHEN** the `system_prompt` AgentConfig record is read
- **THEN** it SHALL contain the agent's name (Twype), its role as an expert assistant, and core behavioral rules

#### Scenario: Crisis prompt content
- **WHEN** the `crisis_prompt` AgentConfig record is read
- **THEN** it SHALL contain instructions to detect distress signals, respond with empathy, and recommend professional help

#### Scenario: Dual layer prompt includes delimiter format
- **WHEN** the `dual_layer_prompt` AgentConfig record is read
- **THEN** it SHALL contain the delimiter tokens `---VOICE---` and `---TEXT---`, instructions for source references using `[N]` notation, and an example of the expected output format
