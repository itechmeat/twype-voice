## Why

The agent currently captures raw sentiment scores from Deepgram but does not interpret or act on them. The `messages` table already has `valence` and `arousal` columns, and the prompt builder includes an `emotion_prompt` layer slot — but nothing fills them. Without emotional adaptation, the agent responds with the same tone regardless of user distress, excitement, or disengagement, undermining the expert-companion experience that Twype targets.

## What Changes

- Introduce an Emotional Analyzer that maps Deepgram sentiment (fast signal) plus LLM-based text interpretation into Russell's Circumplex two-dimensional space (valence + arousal)
- Maintain a per-session emotional trend (sliding window of recent states) to distinguish momentary spikes from sustained shifts
- Classify the current state into one of four quadrants (high-arousal negative = panic, low-arousal negative = apathy, high-arousal positive = enthusiasm, low-arousal positive = calm) and select a tone/style adaptation strategy
- Inject the current emotional context into the LLM prompt dynamically per turn, replacing the static `emotion_prompt` layer with a template that includes real-time emotional data
- Persist `valence` and `arousal` on each user message for session trend analysis
- Publish emotional state updates to the client via data channel for future UI use

## Capabilities

### New Capabilities
- `emotional-analyzer`: Core Circumplex analysis engine — sentiment-to-valence/arousal mapping, LLM-based refinement, quadrant classification, sliding-window trend tracking, and per-turn tone adaptation strategy selection
- `emotional-state-publisher`: Data channel publishing of emotional state updates to the client (quadrant, valence, arousal) for downstream UI consumption

### Modified Capabilities
- `agent-transcript-persistence`: Persist computed `valence` and `arousal` values (from Emotional Analyzer) on user message records, in addition to the existing `sentiment_raw`
- `prompt-builder`: Support dynamic per-turn injection of emotional context into the `emotion_prompt` layer — the layer value becomes a template rendered with current emotional state (quadrant, valence, arousal, trend direction) rather than a static string
- `database-seed`: Add seed content for the `emotion_prompt` layer as a template with placeholders for emotional state variables

## Impact

- **Agent codebase** (`apps/agent/`): New `emotional_analyzer` module; modifications to the agent session lifecycle (analyze after each user utterance, inject before each LLM call)
- **Prompt system** (`apps/agent/src/prompt_builder.py`): Template rendering support for emotion_prompt layer
- **Persistence** (`apps/agent/src/persistence.py`): Pass valence/arousal to `save_transcript`
- **Data channel**: New message type `emotional_state` published after each analysis
- **Database**: No schema changes needed — `valence` and `arousal` columns already exist on `messages`
- **Dependencies**: No new external dependencies expected; LLM-based interpretation uses the existing LiteLLM pipeline
- **Seed data** (`scripts/seed.py`): Emotion prompt template content
