## 1. Emotional Analyzer Module

- [x] 1.1 Create `apps/agent/src/emotional_analyzer.py` with `EmotionalState` and `EmotionalSnapshot` dataclasses
- [x] 1.2 Implement fast-path `estimate_circumplex(sentiment_raw, text)` function — valence from sentiment, arousal from text features
- [x] 1.3 Implement quadrant classification `classify_quadrant(valence, arousal)` with threshold-based logic and 5 categories
- [x] 1.4 Implement tone adaptation `get_tone_guidance(quadrant)` returning descriptive strings per quadrant
- [x] 1.5 Implement `EmotionalTrendTracker` class with sliding window deque, `add_snapshot()`, and `get_trends()` methods
- [x] 1.6 Implement async `refine_with_llm(text, fast_estimate, context_messages, trend, llm_settings)` function for LLM-based refinement
- [x] 1.7 Write unit tests for fast-path estimation, quadrant classification, trend tracking, and tone guidance

## 2. Prompt Builder Modifications

- [x] 2.1 Add `render_emotional_context(instructions, emotional_state)` function to `prompts.py` using `str.format_map()` with fallback on error
- [x] 2.2 Define neutral defaults dict for first-turn rendering when no EmotionalState is available
- [x] 2.3 Write unit tests for `render_emotional_context` — successful rendering, no placeholders, malformed template

## 3. Agent Integration

- [x] 3.1 Add `EmotionalTrendTracker` instance and current `EmotionalState` to `TwypeAgent.__init__`
- [x] 3.2 Integrate emotional analysis into transcript handling in `main.py` — call fast-path after each user utterance, fire LLM refinement async
- [x] 3.3 Consume LLM refinement result from previous turn before current turn's analysis
- [x] 3.4 Inject rendered emotional context into instructions in `TwypeAgent._build_mode_aware_chat_ctx()` before LLM call
- [x] 3.5 Add `EMOTION_LLM_MODEL` to `AgentSettings` in `settings.py` (optional, defaults to `LLM_MODEL`)

## 4. Transcript Persistence

- [x] 4.1 Add `valence` and `arousal` parameters to `save_transcript()` in `transcript.py`
- [x] 4.2 Pass computed valence/arousal from emotional analysis to `save_transcript()` calls in `main.py`
- [x] 4.3 Write unit tests for persistence with and without emotional data

## 5. Data Channel Publishing

- [x] 5.1 Add `publish_emotional_state(room, emotional_state, message_id)` function to `datachannel.py`
- [x] 5.2 Call `publish_emotional_state` after emotional analysis completes in `main.py` event handlers
- [x] 5.3 Write unit tests for emotional state message serialization and format

## 6. Seed Data

- [x] 6.1 Add `emotion_prompt` template entries (en + ru locales) to seed script with Circumplex placeholders
- [x] 6.2 Verify seed templates render correctly with `str.format_map()` and all six placeholder keys

## 7. Integration Verification

- [x] 7.1 Verify full pipeline: user speaks → sentiment extracted → fast-path analysis → emotional state published → tone-adapted LLM response
- [x] 7.2 Verify text mode: user sends text → emotional analysis (no sentiment_raw) → adapted response
- [x] 7.3 Verify LLM refinement runs async and result is consumed on next turn
- [x] 7.4 Verify trend tracking accumulates across multiple turns and produces correct rising/falling/stable signals
