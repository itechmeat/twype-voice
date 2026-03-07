## ADDED Requirements

### Requirement: Fast-path sentiment-to-Circumplex mapping
The Emotional Analyzer module SHALL provide a function that maps a Deepgram `sentiment_raw` score (-1..1) and user text into an initial Circumplex estimate (valence, arousal). Valence SHALL be derived directly from sentiment_raw. Arousal SHALL be estimated from text features: punctuation density (exclamation marks, question marks, ellipses), capitalization ratio, and average word length. Both values SHALL be clamped to the range [-1.0, 1.0].

#### Scenario: Negative sentiment with high-arousal text features
- **WHEN** sentiment_raw is -0.7 and the text contains multiple exclamation marks and capitalized words
- **THEN** the fast-path returns valence approximately -0.7 and arousal > 0.5

#### Scenario: Positive sentiment with calm text
- **WHEN** sentiment_raw is 0.5 and the text is lowercase with no exclamation marks
- **THEN** the fast-path returns valence approximately 0.5 and arousal < 0.3

#### Scenario: Sentiment unavailable
- **WHEN** sentiment_raw is None
- **THEN** the fast-path returns valence 0.0 and arousal estimated from text features only

#### Scenario: Empty text
- **WHEN** the text is empty or whitespace-only
- **THEN** the fast-path returns valence from sentiment_raw (or 0.0 if None) and arousal 0.0

### Requirement: LLM-based emotional refinement
The Emotional Analyzer SHALL provide an async function that sends a lightweight LLM request to refine the Circumplex estimate. The request SHALL include: the user's text, the fast-path estimate, the last 3-5 conversation messages for context, and the current trend. The LLM SHALL return a JSON object with `valence` (float) and `arousal` (float). The function SHALL use the same LiteLLM proxy endpoint as the main pipeline.

#### Scenario: LLM refines emotional estimate
- **WHEN** the refinement function is called with user text, fast-path estimate, and conversation context
- **THEN** it returns refined valence and arousal values as floats in [-1.0, 1.0]

#### Scenario: LLM refinement fails
- **WHEN** the LLM request times out or returns an error
- **THEN** the function returns None and logs the error at WARNING level

#### Scenario: LLM returns invalid JSON
- **WHEN** the LLM response cannot be parsed as valid JSON with valence and arousal fields
- **THEN** the function returns None and logs the parsing error at WARNING level

#### Scenario: LLM refinement model configuration
- **WHEN** the refinement function is called
- **THEN** it SHALL use the model specified by `EMOTION_LLM_MODEL` environment variable (default: same as `LLM_MODEL`)

### Requirement: Quadrant classification
The Emotional Analyzer SHALL classify a (valence, arousal) pair into one of five categories: `distress` (valence < -threshold, arousal >= threshold), `melancholy` (valence < -threshold, arousal < -threshold), `serenity` (valence >= threshold, arousal < -threshold), `excitement` (valence >= threshold, arousal >= threshold), or `neutral` (both dimensions within ±threshold of zero). The threshold SHALL default to 0.15.

#### Scenario: High arousal negative state
- **WHEN** valence is -0.6 and arousal is 0.7
- **THEN** the quadrant is classified as `distress`

#### Scenario: Low arousal negative state
- **WHEN** valence is -0.5 and arousal is -0.4
- **THEN** the quadrant is classified as `melancholy`

#### Scenario: Low arousal positive state
- **WHEN** valence is 0.4 and arousal is -0.3
- **THEN** the quadrant is classified as `serenity`

#### Scenario: High arousal positive state
- **WHEN** valence is 0.6 and arousal is 0.5
- **THEN** the quadrant is classified as `excitement`

#### Scenario: Neutral zone
- **WHEN** valence is 0.1 and arousal is -0.05
- **THEN** the quadrant is classified as `neutral`

### Requirement: Sliding window trend tracking
The Emotional Analyzer SHALL maintain a sliding window of the last N emotional snapshots (default N=10). Each snapshot SHALL contain valence, arousal, and timestamp. The analyzer SHALL compute trend direction for each dimension: `rising` (mean of recent half > mean of older half + threshold), `falling` (mean of recent half < mean of older half - threshold), or `stable`. The trend threshold SHALL default to 0.1. Additionally, the analyzer SHALL expose a `high_distress` signal that is set to `True` when the last 3 or more consecutive snapshots are in the `distress` quadrant AND the valence trend is `falling`.

#### Scenario: Rising valence trend
- **WHEN** the window contains 6+ snapshots and recent snapshots have consistently higher valence than older ones
- **THEN** the trend for valence is `rising`

#### Scenario: Stable trend with few snapshots
- **WHEN** the window contains fewer than 3 snapshots
- **THEN** both trend dimensions are `stable`

#### Scenario: Window eviction
- **WHEN** the window is full (N snapshots) and a new snapshot is added
- **THEN** the oldest snapshot is evicted and the trend is recomputed

#### Scenario: High distress signal activated
- **WHEN** the last 3 consecutive snapshots are in the `distress` quadrant and valence trend is `falling`
- **THEN** the `high_distress` property returns `True`

#### Scenario: High distress signal deactivated
- **WHEN** the most recent snapshot is not in the `distress` quadrant
- **THEN** the `high_distress` property returns `False`

### Requirement: Emotional state result structure
The Emotional Analyzer SHALL return an `EmotionalState` dataclass containing: `valence` (float), `arousal` (float), `quadrant` (string), `trend_valence` (string: rising/falling/stable), `trend_arousal` (string: rising/falling/stable), `sentiment_raw` (float or None), `is_refined` (bool indicating whether LLM refinement was applied).

#### Scenario: State with fast-path only
- **WHEN** LLM refinement has not yet completed
- **THEN** the EmotionalState has `is_refined=False` and values from the fast path

#### Scenario: State with LLM refinement
- **WHEN** LLM refinement completed successfully for the previous turn
- **THEN** the EmotionalState has `is_refined=True` and refined valence/arousal values blended with the current fast-path estimate

### Requirement: Tone adaptation strategy per quadrant
The Emotional Analyzer SHALL provide a function that returns a tone adaptation descriptor (string) for a given quadrant. The descriptors SHALL be: `distress` → "Calm, grounding, empathetic. Use short sentences. Acknowledge the difficulty.", `melancholy` → "Warm, gentle, encouraging. Offer structure and small steps.", `serenity` → "Supportive, steady, deepening. Match the calm pace.", `excitement` → "Enthusiastic, validating, channeling energy constructively.", `neutral` → "Balanced, attentive, responsive."

#### Scenario: Distress tone descriptor
- **WHEN** the quadrant is `distress`
- **THEN** the function returns the distress tone adaptation string

#### Scenario: Neutral tone descriptor
- **WHEN** the quadrant is `neutral`
- **THEN** the function returns the neutral tone adaptation string
