## ADDED Requirements

### Requirement: Pre-LLM crisis interception hook
The agent pipeline SHALL support a `before_llm_cb` callback that fires before each LLM call. The crisis detector SHALL be registered as this callback. When the callback returns a crisis override, the pipeline SHALL use the overridden LLM context (crisis prompt + contacts) instead of the normal context (system prompt + history + RAG). The override SHALL set a flag that causes downstream components (RAG injector, dual-layer parser) to skip processing for this turn.

#### Scenario: Crisis detector overrides LLM context
- **WHEN** the before_llm_cb detects a crisis in the current utterance
- **THEN** the LLM receives only the crisis response prompt with emergency contacts instead of the normal conversation context

#### Scenario: No crisis allows normal flow
- **WHEN** the before_llm_cb does not detect a crisis
- **THEN** the LLM receives the normal context (system prompt, conversation history, RAG results)

#### Scenario: RAG and dual-layer skipped on crisis override
- **WHEN** a crisis override is active for the current turn
- **THEN** RAG search is not performed and dual-layer response parsing is not applied

#### Scenario: Crisis override is per-turn
- **WHEN** a crisis override was active on the previous turn and the current turn is not a crisis
- **THEN** the pipeline resumes normal operation with full context
