## ADDED Requirements

### Requirement: Tier 1 keyword-based crisis detection
The Crisis Detector module SHALL analyze every user utterance (both voice transcripts and text messages) against a configurable set of distress signal patterns. The patterns SHALL be organized by category: `suicide` (suicidal ideation, self-harm intent), `self_harm` (cutting, overdose, injury), `acute_symptoms` (psychotic episodes, severe panic, dissociation), `violence` (threats to others, domestic violence). The keyword lists SHALL be loaded from `agent_configs` at session start and cached. Matching SHALL be case-insensitive and support both exact phrases and regex patterns. The detector SHALL support Russian and English keyword sets.

#### Scenario: Keyword match triggers Tier 2
- **WHEN** a user utterance contains a distress keyword (e.g., "I want to kill myself")
- **THEN** the detector flags the utterance as a Tier 1 match and invokes Tier 2 LLM classification

#### Scenario: No keyword match in benign utterance
- **WHEN** a user utterance contains no distress keywords (e.g., "Tell me about sleep hygiene")
- **THEN** the detector returns no crisis signal and processing continues normally

#### Scenario: Multi-language keyword matching
- **WHEN** a user utterance contains a distress keyword in Russian (e.g., "хочу умереть")
- **THEN** the detector flags the utterance as a Tier 1 match regardless of the session's primary language setting

#### Scenario: Keywords loaded from agent_configs
- **WHEN** the crisis detector initializes at session start
- **THEN** it loads keyword patterns from the `agent_configs` table keyed by `crisis_keywords_{language}`

### Requirement: Tier 2 LLM-based crisis classification
The Crisis Detector SHALL invoke an LLM classifier when Tier 1 produces a match or when the emotional analyzer signals high distress. The classifier SHALL receive only the current utterance and a focused system prompt asking it to classify the utterance as `crisis` or `not_crisis` with a `confidence` score (0.0-1.0). The classifier SHALL use the same LiteLLM proxy endpoint. Conversation history SHALL NOT be included in the classification context to avoid bias.

#### Scenario: LLM confirms crisis
- **WHEN** the Tier 2 classifier returns `crisis` with confidence >= 0.7
- **THEN** the detector confirms a crisis event and triggers the pipeline override

#### Scenario: LLM rejects false positive
- **WHEN** the Tier 2 classifier returns `not_crisis` for a Tier 1 keyword match (e.g., "this homework is killing me")
- **THEN** the detector does not trigger a crisis event and processing continues normally

#### Scenario: LLM classifier times out
- **WHEN** the LLM classification request does not complete within 3 seconds
- **THEN** the detector SHALL treat the utterance as a confirmed crisis (fail-safe) and trigger the pipeline override

#### Scenario: LLM classifier returns ambiguous result
- **WHEN** the Tier 2 classifier returns `crisis` with confidence between 0.5 and 0.7
- **THEN** the detector SHALL treat the utterance as a confirmed crisis (err on the side of safety)

### Requirement: Emotional distress signal integration
The Crisis Detector SHALL accept a `high_distress` signal from the Emotional Analyzer. When the emotional analyzer reports 3 or more consecutive snapshots in the `distress` quadrant with a `falling` valence trend, the crisis detector SHALL lower its Tier 1 matching sensitivity (broader pattern matching) and SHALL invoke Tier 2 LLM classification even without a keyword match on the next utterance.

#### Scenario: Sustained distress triggers proactive classification
- **WHEN** the emotional analyzer has recorded 3+ consecutive `distress` quadrant snapshots with falling valence trend and the user sends a new utterance without crisis keywords
- **THEN** the crisis detector invokes Tier 2 LLM classification on that utterance

#### Scenario: Distress signal resets after non-distress state
- **WHEN** the emotional analyzer reports a non-distress quadrant after a period of sustained distress
- **THEN** the crisis detector returns to normal sensitivity (standard keyword matching threshold)

### Requirement: Pipeline override on confirmed crisis
When a crisis is confirmed, the Crisis Detector SHALL override the normal agent pipeline. The override SHALL: (1) replace the LLM system prompt with a constrained crisis response prompt, (2) exclude all RAG context from the LLM call, (3) exclude conversation history from the LLM call, (4) include locale-specific emergency contacts in the prompt, (5) skip dual-layer response parsing (voice-only response). The crisis response prompt SHALL enforce a fixed structure: empathetic acknowledgment, non-judgmental validation, recommendation for professional help, and emergency contact information.

#### Scenario: Crisis override produces empathetic response
- **WHEN** a crisis is confirmed for a user speaking in Russian
- **THEN** the LLM receives only the crisis prompt with Russian emergency contacts and generates an empathetic response following the mandated structure

#### Scenario: RAG context excluded during crisis
- **WHEN** a crisis override is active
- **THEN** no RAG search is performed and no knowledge base content is included in the LLM context

#### Scenario: Dual-layer parsing skipped during crisis
- **WHEN** a crisis override is active
- **THEN** the response is sent entirely to TTS (voice mode) or as plain text (text mode), without dual-layer structured/voice split

#### Scenario: Normal pipeline resumes after crisis response
- **WHEN** a crisis response has been delivered and the user sends a new utterance
- **THEN** the new utterance is processed through the crisis detector again; if no crisis is detected, normal pipeline resumes

### Requirement: Crisis event logging
The Crisis Detector SHALL log every confirmed crisis event. The triggering user message and the agent's crisis response SHALL be saved to the `messages` table with `is_crisis=True`. The log SHALL include the detection tier (1 or 2), the matched category, and the LLM classifier confidence score if available.

#### Scenario: Crisis messages flagged in database
- **WHEN** a crisis event is confirmed
- **THEN** the user's triggering message is saved with `is_crisis=True` and the agent's crisis response is also saved with `is_crisis=True`

#### Scenario: Crisis metadata logged
- **WHEN** a crisis event is confirmed via Tier 2 with confidence 0.85 in category `suicide`
- **THEN** the log entry includes `detection_tier=2`, `crisis_category=suicide`, `confidence=0.85`

### Requirement: Crisis data channel notification
The Crisis Detector SHALL publish a `crisis_alert` event via the data channel when a crisis is confirmed. The event SHALL include: `crisis_category` (string), `contacts` (array of emergency contact objects with name, phone, url, description), and `session_language` (string).

#### Scenario: Client receives crisis alert with contacts
- **WHEN** a crisis is confirmed for a session with locale `ru`
- **THEN** a `crisis_alert` data channel event is published containing Russian emergency contacts

#### Scenario: Crisis alert includes category
- **WHEN** a crisis is detected in the `self_harm` category
- **THEN** the `crisis_alert` event includes `crisis_category: "self_harm"`

### Requirement: Crisis detection feature toggle
The Crisis Detector SHALL be enabled or disabled via the `CRISIS_ENABLED` environment variable (default: `true`). When disabled, no utterance analysis is performed and the pipeline operates without crisis interception.

#### Scenario: Crisis detection disabled
- **WHEN** `CRISIS_ENABLED` is set to `false`
- **THEN** no keyword matching or LLM classification is performed on utterances

#### Scenario: Crisis detection enabled by default
- **WHEN** `CRISIS_ENABLED` is not set
- **THEN** the crisis detector is active and processes all utterances
