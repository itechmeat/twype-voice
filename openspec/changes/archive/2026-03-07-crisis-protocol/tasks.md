## 1. Database Schema and Seed Data

- [x] 1.1 Create `CrisisContact` SQLAlchemy model in `apps/api/src/models/` with all columns (id, language, locale, contact_type, name, phone, url, description, priority, is_active, created_at, updated_at) and indexes
- [x] 1.2 Add `is_crisis` boolean column (default False) to the `Message` model
- [x] 1.3 Generate and apply Alembic migration for `crisis_contacts` table and `messages.is_crisis` column
- [x] 1.4 Add crisis contacts seed data to `scripts/seed.py` for Russian and English locales (3+ contacts each, idempotent upsert)
- [x] 1.5 Add crisis keyword patterns seed data to `agent_configs` table (categories: suicide, self_harm, acute_symptoms, violence; languages: ru, en)

## 2. Crisis Contacts API Endpoint

- [x] 2.1 Create `GET /crisis-contacts` endpoint in FastAPI with `language` query parameter, fallback to English, public access (no auth required)
- [x] 2.2 Write tests for the crisis contacts endpoint (by language, fallback, no auth)

## 3. Crisis Detector Module

- [x] 3.1 Create `apps/agent/src/crisis.py` with `CrisisDetector` class: initialization, keyword loading from agent_configs cache
- [x] 3.2 Implement Tier 1 keyword/pattern matching (case-insensitive, regex support, multi-language, categorized)
- [x] 3.3 Implement Tier 2 LLM classification (focused prompt, crisis/not_crisis + confidence, 3s timeout with fail-safe)
- [x] 3.4 Implement emotional distress signal integration (accept high_distress from EmotionalAnalyzer, lower threshold, trigger Tier 2 without keywords)
- [x] 3.5 Implement crisis response prompt builder (constrained prompt with empathy structure + locale contacts, no history, no RAG)
- [x] 3.6 Implement crisis data channel notification (`crisis_alert` event with category and contacts)
- [x] 3.7 Implement crisis event logging (is_crisis flag on messages, detection metadata: tier, category, confidence)
- [x] 3.8 Add `CRISIS_ENABLED` setting to `apps/agent/src/settings.py` (default: true)

## 4. Emotional Analyzer Modification

- [x] 4.1 Add `high_distress` property to `EmotionalTrendTracker`: True when 3+ consecutive distress snapshots with falling valence
- [x] 4.2 Write tests for high_distress signal (activation, deactivation, edge cases)

## 5. Pipeline Integration

- [x] 5.1 Register crisis detector as `before_llm_cb` in `agent.py` — intercept before LLM call, override context on crisis
- [x] 5.2 Add crisis override flag that skips RAG injection and dual-layer parsing for the current turn
- [x] 5.3 Initialize crisis detector in `main.py` at session start: load keywords, cache crisis contacts for session locale
- [x] 5.4 Add `publish_crisis_alert()` to `datachannel.py`

## 6. Testing

- [x] 6.1 Unit tests for Tier 1 keyword matching (hit, miss, multi-language, case-insensitive)
- [x] 6.2 Unit tests for Tier 2 LLM classification (confirm, reject, timeout fail-safe, ambiguous confidence)
- [x] 6.3 Unit tests for pipeline override (crisis context replaces normal context, RAG skipped, dual-layer skipped, resume after crisis)
- [x] 6.4 Unit tests for crisis contacts caching and fallback
- [x] 6.5 Integration test: full crisis flow from utterance through detection to crisis response delivery
