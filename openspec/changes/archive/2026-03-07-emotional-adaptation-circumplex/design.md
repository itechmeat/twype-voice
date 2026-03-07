## Context

The agent already captures `sentiment_raw` (-1..1) from Deepgram on every final transcript and persists it to `messages.sentiment_raw`. The `messages` table has `valence` and `arousal` columns (Float, nullable) that are never populated. The prompt builder includes `emotion_prompt` in the layer order but treats it as a static string loaded at session start. The `llm_node()` override in `agent.py` already builds mode-aware context and injects RAG before every LLM call — this is the natural insertion point for emotional context.

The agent currently responds with the same tone regardless of user emotional state: a panicking user gets the same measured response as a calm one. S17 adds emotional awareness without changing the fundamental pipeline architecture.

## Goals / Non-Goals

**Goals:**
- Map raw sentiment + text analysis into two-dimensional Circumplex space (valence, arousal)
- Maintain per-session emotional trend via sliding window
- Classify emotional state into quadrants and adapt LLM tone dynamically per turn
- Persist valence/arousal on user messages for historical analysis
- Publish emotional state to the client for future UI consumption

**Non-Goals:**
- Training or fine-tuning any models — we use existing Deepgram sentiment + LLM interpretation
- UI rendering of emotional state (future PWA stories)
- Crisis detection (separate S19 story)
- Changing the voice pipeline flow (VAD → STT → LLM → TTS remains unchanged)
- Per-assistant-message emotional analysis (only user messages are analyzed)

## Decisions

### D1: Emotional Analyzer as a standalone module

**Decision:** Create `apps/agent/src/emotional_analyzer.py` as a pure-logic module with no I/O dependencies.

**Rationale:** The analyzer takes inputs (sentiment_raw, text, history) and returns outputs (valence, arousal, quadrant, trend). Keeping it stateless and I/O-free makes it testable and keeps the pipeline orchestration in `main.py` where it belongs.

**Alternatives considered:**
- Embedding analysis in `TwypeAgent` class → rejected: would bloat the already 500-line agent.py
- Creating an `EmotionalAnalyzer` service with DB access → rejected: overengineered, the persistence is already handled by `transcript.py`

### D2: Two-stage analysis — fast path + LLM refinement

**Decision:** Use a two-stage approach:
1. **Fast path (every turn):** Heuristic mapping from Deepgram `sentiment_raw` to initial valence estimate. Arousal estimated from text features (punctuation density, caps, word length, question marks). This runs synchronously with zero latency cost.
2. **LLM refinement (every turn, async):** A lightweight LLM call that interprets the user's text in context (last 3-5 messages, current sentiment, current trend) and returns structured JSON with refined valence/arousal scores. Uses the same LiteLLM proxy with a small, fast model.

**Rationale:** The fast path provides immediate values when LLM refinement isn't available or fails. The LLM call adds contextual understanding (sarcasm, implicit emotions) that pure sentiment can't capture.

**Alternatives considered:**
- LLM-only analysis → rejected: adds latency to every turn, and if LLM fails we have nothing
- Sentiment-only mapping → rejected: too crude, can't detect arousal or contextual emotions
- Separate emotion detection model → rejected: adds a new dependency, S17 scope is explicit about using existing LLM

### D3: LLM refinement runs in parallel with main LLM call

**Decision:** The emotional analysis LLM call fires asynchronously after the user transcript is received, in parallel with the main LLM response generation. The result is consumed before the *next* turn's LLM call (not the current one). The fast-path estimate is used for the current turn's prompt injection.

**Rationale:** This eliminates any added latency to the voice pipeline. The one-turn delay for LLM-refined values is acceptable because emotional states don't change drastically between adjacent turns, and the fast path covers the immediate signal.

**Alternatives considered:**
- Block on LLM analysis before main LLM call → rejected: adds 200-500ms latency per turn, violates the ~800ms target
- Skip LLM refinement entirely → rejected: loses contextual understanding that is the core value of this feature

### D4: Sliding window for trend tracking

**Decision:** Maintain a `deque(maxlen=10)` of `EmotionalSnapshot` objects (valence, arousal, timestamp) in `TwypeAgent`. The trend is computed as the direction of change: rising/falling/stable for each dimension over the window.

**Rationale:** 10 turns covers roughly 2-5 minutes of conversation — enough to detect sustained emotional shifts vs momentary spikes. A deque naturally evicts old entries. No persistence needed — the trend is session-scoped and reconstructable from message history if needed.

**Alternatives considered:**
- Exponential moving average → rejected: harder to interpret, doesn't give clear "rising/falling" signal
- Full session history → rejected: unbounded memory, and distant history is less relevant

### D5: Dynamic emotion prompt injection via template rendering

**Decision:** The `emotion_prompt` layer in `agent_config` becomes a Python format-string template with placeholders: `{quadrant}`, `{valence}`, `{arousal}`, `{trend_valence}`, `{trend_arousal}`. Before each LLM call, the agent renders the template with current emotional state values and injects it as a system message alongside the mode guidance.

**Rationale:** This preserves the existing prompt layer architecture (loaded once, used many times) while enabling per-turn dynamic content. The template approach is simpler than rebuilding instructions every turn.

**Implementation:** In `TwypeAgent._build_mode_aware_chat_ctx()`, after injecting mode guidance, render and inject the emotional context. This parallels how mode guidance is already injected.

**Alternatives considered:**
- Rebuild full instructions string every turn → rejected: wasteful, most layers are static
- Add emotional context as a user-message annotation → rejected: pollutes conversation history, confuses the LLM
- Separate system message injection → this is essentially what we're doing, using the template from the DB

### D6: Quadrant classification with descriptive labels

**Decision:** Four quadrants mapped from the Circumplex model:
| Quadrant | Valence | Arousal | Label | Agent Tone |
|----------|---------|---------|-------|------------|
| Q1 | negative | high | distress | Calm, grounding, empathetic. Short sentences. |
| Q2 | negative | low | melancholy | Warm, gentle, encouraging. Offer structure. |
| Q3 | positive | low | serenity | Supportive, steady, deepening. Match pace. |
| Q4 | positive | high | excitement | Enthusiastic, validating, channeling energy. |

The neutral zone (both dimensions near zero, within ±0.15) defaults to a balanced, attentive tone.

**Rationale:** Four quadrants plus neutral covers the practical space. More granularity (8 octants, continuous mapping) adds complexity without proportional benefit for tone adaptation — the LLM can interpret the descriptive label effectively.

### D7: Data channel message type `emotional_state`

**Decision:** Publish a new `emotional_state` message type after each emotional analysis completes:
```json
{
  "type": "emotional_state",
  "quadrant": "distress",
  "valence": -0.6,
  "arousal": 0.8,
  "trend_valence": "falling",
  "trend_arousal": "stable",
  "message_id": "uuid"
}
```
Reliable delivery. Published once per user utterance, after analysis completes.

**Rationale:** Decouples emotional state from transcript messages. The client can choose to display or ignore it. Follows the existing pattern of typed JSON messages on the data channel.

## Risks / Trade-offs

**[LLM refinement adds cost]** → Each user turn triggers an additional small LLM call. Mitigation: use the cheapest/fastest model available via LiteLLM (e.g., `gemini-flash-lite`). The call is <100 tokens prompt + <50 tokens response. At scale this is negligible compared to the main LLM call.

**[Fast-path arousal estimation is imprecise]** → Text-feature heuristics (punctuation, caps) are crude. Mitigation: the fast path is only used for the current turn; the LLM refinement corrects it for the next turn. Over a few turns the system converges on accurate values.

**[One-turn delay for refined emotions]** → The LLM-refined valence/arousal lags by one turn. Mitigation: the fast path provides immediate estimates, and emotional states rarely flip between adjacent turns. The sliding window further smooths transitions.

**[Template rendering failure]** → If the emotion_prompt template has bad placeholders or the emotional state is missing. Mitigation: catch `KeyError`/`ValueError` in template rendering, fall back to the raw emotion_prompt string without substitution. Log warning.

**[Sentiment unavailable for some languages/models]** → Deepgram may not return sentiment for all configurations. Mitigation: already handled — `_extract_sentiment_raw()` returns None, fast path defaults to neutral (0.0, 0.0).
