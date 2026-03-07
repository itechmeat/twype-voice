## Why

The agent handles sensitive expert topics (medicine, psychology) where users may express distress signals — suicidal ideation, self-harm intent, acute symptoms, or violence. Without a dedicated crisis detection and response mechanism, the agent could give a generic or even harmful answer in a life-threatening situation. The crisis prompt layer already exists but only provides soft guidance to the LLM; there is no hard override that guarantees a safe response regardless of context or RAG results. S19 introduces a deterministic safety net with the highest execution priority.

## What Changes

- **Crisis Detector module** in the agent: analyzes each user utterance (STT transcript or text message) for distress signals using keyword/pattern matching as a fast path and LLM classification as a refined path. Runs before the main LLM call.
- **Pipeline override**: when a crisis is detected, the normal LLM+RAG flow is bypassed. The agent produces a fixed-structure empathetic response: acknowledgment, non-judgment, recommendation for professional help, and locale-aware emergency contacts fetched from the database.
- **`crisis_contacts` database table + migration**: stores emergency service contacts and helpline numbers per language/locale (phone, URL, description). Seeded with initial data for Russian and English locales.
- **Crisis event logging**: each trigger is recorded in the `messages` table with a `crisis` flag for audit, monitoring, and post-session review.
- **Data channel notification**: the client is informed of a crisis event so the UI can render emergency contacts and visual indicators.
- **Agent settings**: feature toggle (`CRISIS_ENABLED`), detection sensitivity thresholds, contact fetch timeout.

## Capabilities

### New Capabilities
- `crisis-detector`: Utterance analysis for distress signals (keyword fast-path + LLM classification), crisis state management, pipeline override trigger, and crisis event logging.
- `crisis-contacts`: Database table schema, migration, seed data, and API endpoint for fetching locale-aware emergency contacts.

### Modified Capabilities
- `emotional-analyzer`: Add crisis severity signal — when the emotional analyzer detects sustained `distress` quadrant with falling valence trend, it provides an additional input to the crisis detector for improved sensitivity.
- `agent-llm-pipeline`: Add a pre-LLM hook point where the crisis detector can intercept and override the normal response flow.

## Impact

- **Agent** (`apps/agent/src/`): New `crisis.py` module. Changes to `agent.py` (pipeline override hook), `main.py` (crisis detector initialization), `settings.py` (new settings), `datachannel.py` (crisis event publisher).
- **API** (`apps/api/`): New `crisis_contacts` model, Alembic migration, seed data in `scripts/seed.py`. Optional: `GET /crisis-contacts` endpoint for client-side rendering.
- **Database**: New `crisis_contacts` table, new `is_crisis` boolean column on `messages` table.
- **Prompts**: The existing `crisis_prompt` layer remains as LLM guidance; the crisis detector adds a hard deterministic override on top of it.
- **Data channel protocol**: New `crisis_alert` message type with contact details and severity level.
