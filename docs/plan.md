# MVP Implementation Plan

**Version:** 1.0
**Date:** March 2026

> Sequential list of stories for implementing the MVP voice AI agent. Each story builds on the results of the previous one. Product description — in [about.md](about.md), architecture — in [architecture.md](architecture.md), specifications — in [specs.md](specs.md).

---

- [x] **S01. Docker infrastructure and service stubs**
      Set up the monorepo project structure and Docker Compose with seven stub containers: `caddy`, `api`, `livekit`, `agent`, `litellm`, `postgres`, `coturn`. Each container starts and responds to health checks but contains no business logic. Configured: internal network `twype-net`, volumes, `.env.example`, configs (`livekit.yaml`, `litellm.yaml`, `Caddyfile`, `turnserver.conf`). Dev and production compose files. Root `pyproject.toml` (uv workspace) and `package.json` (bun workspace). Linting: ruff for Python, ESLint + Prettier for TypeScript.

- [x] **S02. Database schema and migrations**
      SQLAlchemy 2.0 models (async, Mapped columns): `users`, `sessions`, `messages`, `agent_configs`, `agent_prompts`, `knowledge_chunks`, `verification_codes`, `crisis_contacts`. pgvector extension. Alembic infrastructure in `apps/api/migrations/`. Initial migration, seed script with test data. Table and index naming conventions.

- [x] **S03. Authentication (registration, login, JWT)**
      FastAPI endpoints: `POST /auth/register`, `POST /auth/verify`, `POST /auth/login`, `POST /auth/refresh`. Registration with email + password, hashing via bcrypt/passlib, sending a 6-digit code via Resend, email verification. JWT tokens: access (15 min, HS256) + refresh (30 days). Middleware for Bearer token validation. Tests for all authentication endpoints.

- [x] **S04. Session management and LiveKit token generation**
      FastAPI endpoints: `POST /sessions/start` (create session + generate LiveKit token with permissions), `GET /sessions/history` (list of user's past sessions), `GET /sessions/{id}/messages` (session message history). LiveKit token generation via `livekit-api` SDK with `can_publish`, `can_subscribe`, `can_publish_data` permissions. Session recording to the database.

- [x] **S05. LiveKit Agent: connecting to a room**
      Basic LiveKit Agent in `apps/agent/`: entry point `main.py`, connecting to LiveKit Server via SDK, receiving and dispatching jobs on room creation. The agent connects as a participant to the room and receives the audio stream. Silero VAD for speech detection. At this stage the agent only listens — no STT/LLM/TTS.

- [x] **S06. STT integration (Deepgram)**
      Connecting the `livekit-plugins-deepgram` plugin. Streaming speech recognition with interim and final transcripts. Support for Russian and English languages. Extracting sentiment score (-1..1) from Deepgram results. Saving user transcripts to the database (`messages`). Sending interim transcripts to the client via data channel.

- [x] **S07. LLM integration via LiteLLM Proxy**
      LiteLLM Proxy setup: configuring Gemini Flash-Lite as the primary model and GPT-4.1-mini as fallback. Connecting the OpenAI-compatible `livekit-plugins-openai` plugin to LiteLLM. Basic prompt context (hardcoded for now). Streaming response generation. LiteLLM health check and unavailability handling. Saving agent responses to the database.

- [x] **S08. TTS integration (Inworld)**
      Custom TTS plugin for Inworld AI in `apps/agent/src/plugins/`. Streaming speech synthesis from LLM response text. Support for Russian and English languages. Expressiveness and speed parameters. Fallback to ElevenLabs when Inworld is unavailable. The plugin is developed as a module suitable for a PR to the LiveKit Agents repository.

- [x] **S09. Voice pipeline end-to-end**
      Assembling the full voice pipeline: VAD -> Turn Detector -> STT -> LLM -> TTS -> WebRTC audio. Turn Detector setup (end-of-utterance detection): pause thresholds, safety timeout of 3 sec. Input noise suppression. End-to-end streaming between all components. Target voice-to-voice latency ~800 ms. Thinking sounds and TTS fillers during extended processing.

- [ ] **S10. Prompt system from the database**
      Loading all prompt layers from PostgreSQL during agent initialization: system prompt, voice mode prompt, dual-layer response prompt, emotional adaptation prompt, crisis protocol prompt, RAG context prompt, language adaptation prompt, proactive utterance prompt. Prompt Builder assembles the final LLM context. Config snapshot at session start — freezing the configuration version. Seed script with an initial set of prompts.

- [ ] **S11. Text chat via data channel**
      Data Channel Handler in the agent: receiving text messages from the client via LiveKit data channel. Routing text directly to the LLM (bypassing STT). Streaming the text response back via data channel. Saving text messages to the same `messages` table with a mode label. TTS is not invoked in text mode.

- [ ] **S12. Mode switching: voice <-> text**
      A single dialogue stream when switching between modes. The agent determines the current mode by the type of incoming data (audio track vs data channel). Context Manager maintains a shared history for both modes. When switching to text — the LLM generates detailed responses; when switching to voice — brief, conversational ones.

- [ ] **S13. RAG: knowledge base ingestion**
      Script `scripts/ingest.py`: extracting text from PDF, EPUB, DOCX, audio (transcription). Semantic chunking by meaningful blocks. Metadata enrichment (source_type, title, author, url, section, page_range, language, tags). Embedding generation via LiteLLM. Loading into PostgreSQL: vector column + metadata. Creating an HNSW index and tsvector for full-text search.

- [ ] **S14. RAG: hybrid search at query time**
      RAG Engine in the agent: converting the utterance to an embedding, hybrid search (cosine distance pgvector + tsvector full-text + metadata filters). Top-K (3-5) relevant fragments are included in the LLM context along with source metadata. Prioritizing fragments in the user's language without excluding cross-language results.

- [ ] **S15. Dual-layer response (voice + text)**
      The LLM generates a response in two parts following the dual-layer response prompt. Voice part: 2-5 sentences, conversational style, verbal references to sources. Text part: structured bullet points with chunk_ids arrays for each point. The agent sends both parts: voice part to TTS, text part via data channel. Responses not confirmed by the knowledge base are labeled as reasoning.

- [ ] **S16. Source attribution (API + client)**
      FastAPI endpoint `GET /sources/{chunk_ids}` — returns full metadata of RAG fragments (source_type, title, author, section, page_range, url). The client renders indicator icons (book, video, podcast, article) next to each bullet point. Popup on click: author, title, section, page/timecode, direct link.

- [ ] **S17. Emotional adaptation (Circumplex)**
      Emotional Analyzer: receiving sentiment score from Deepgram as a fast signal. LLM-based interpretation of the state in two-dimensional space (valence + arousal) based on text, sentiment, context, and trend. Adapting response tone and style by quadrant: panic, apathy, enthusiasm, calmness. Saving emotional data to the database for session trend analysis.

- [ ] **S18. Proactive behavior**
      Silence Timer in the agent: timer tracking silence after a response. On short timeout (15 sec) — a follow-up question based on context. On long timeout (45 sec) — a gentle utterance considering the emotional state. Phrases are generated by the LLM with a `proactive` / `extended_silence` flag, not hardcoded. The timer resets on any activity. No more than one proactive utterance per pause.

- [ ] **S19. Crisis protocol**
      Crisis Detector: analyzing utterances for distress signals (suicide, self-harm, acute symptoms, violence). On detection — pipeline override, fixed response protocol: empathy, non-judgment, recommendation for professional help, emergency service contacts. Contacts are determined by language/locale from the database (`crisis_contacts` table). Trigger logging. Highest priority — not overridden by context.

- [ ] **S20. Interruption handling**
      Interruption handling: upon detecting speech during the agent's response — immediate cancellation of current LLM + TTS generation, switching to receiving new input. Handling false interruptions: if no words are recognized after an interruption — regenerate a brief continuation or repeat the last 1-2 sentences. Configurable timeouts.

- [ ] **S21. PWA: authentication screens**
      React application in `apps/web/`: registration pages (email + password), verification (entering a 6-digit code), login. React Router for routing. TanStack Query for requests to FastAPI. JWT token storage, automatic refresh on 401. Redirect to login on refresh token expiration. Basic application layout.

- [ ] **S22. PWA: main chat interface**
      Connecting to LiveKit via Client SDK. Unified voice and text chat interface. Microphone control (AgentControlBar). Chat feed with transcripts (AgentChatTranscript). Audio visualization. Agent state indicator. Text input field. Switching between voice and text modes. Displaying interim transcripts in real time.

- [ ] **S23. PWA: source attribution and history**
      Rendering source indicator icons (book, video, podcast, article) next to bullet points in the text chat. Popup with detailed information on click (request to `GET /sources/{ids}`). Session history screen (request to `GET /sessions/history`). Viewing past dialogues (`GET /sessions/{id}/messages`).

- [ ] **S24. PWA as Progressive Web App**
      Service worker for offline shell. Web App Manifest (icons, theme, standalone display). Meta tags for mobile. Responsive layout for mobile and desktop browsers. Vite build optimization for production.

- [ ] **S25. Integration testing and stabilization**
      End-to-end verification of all user flows: registration -> login -> start session -> voice dialogue -> switch to text -> source attribution -> proactive utterance -> end. Testing in two languages (Russian, English). Crisis protocol verification. Load test for 30 concurrent sessions. Bug fixes, timeout and threshold tuning. Finalizing seed data and prompts.
