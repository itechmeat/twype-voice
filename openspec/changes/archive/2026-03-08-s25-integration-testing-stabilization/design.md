## Context

All 24 implementation stories (S01–S24) are complete. The system has:
- 35 Python test files (api + agent) running via pytest against a real test PostgreSQL
- 20 TypeScript test files (web) running via vitest with jsdom
- Unit/integration tests per feature, but no end-to-end tests across the full Docker Compose stack
- Service Worker with `skipWaiting` + `clientsClaim` that force-updates during active sessions, potentially disrupting LiveKit WebRTC connections

The Docker stack consists of 8 services: postgres, livekit, litellm, caddy, coturn, api, agent, web. All services have health checks. A `compose.yaml` (dev) and `compose.prod.yaml` (prod) exist.

Current test infrastructure:
- **API tests**: pytest + httpx ASGITransport against in-process FastAPI, real PostgreSQL via `testsupport` helper
- **Agent tests**: pytest with monkeypatched env vars, mocked external services (LiveKit, Deepgram, Inworld, LLM)
- **Web tests**: vitest + jsdom + @testing-library/react, mocked API calls

Seed data: `scripts/seed.py` seeds prompts (en + partial ru), crisis contacts (en + ru), TTS config, and sample knowledge chunks.

## Goals / Non-Goals

**Goals:**
- Verify all critical user flows work end-to-end across the full Docker Compose stack
- Validate bilingual support (Russian + English) in the voice pipeline and prompt system
- Verify crisis protocol triggers correctly and returns appropriate contacts
- Establish a load test baseline for 30 concurrent sessions
- Replace the force-updating Service Worker with a user-prompted update flow
- Finalize seed data quality for production readiness
- Fix bugs and tune timeouts discovered during integration testing

**Non-Goals:**
- Full browser automation E2E (Playwright/Cypress) — WebRTC audio testing in headless browsers is unreliable; we use API-level E2E instead
- Automated voice quality assessment — validated manually via LiveKit Agents Playground
- CI/CD pipeline changes — tests are designed to run locally against Docker Compose for now
- Performance optimization beyond identifying bottlenecks — tuning is a separate effort
- Adding new features or changing business logic

## Decisions

### D1. E2E test approach: API-level integration, not browser automation

**Decision:** E2E tests exercise the full stack via HTTP (httpx) and LiveKit SDK (livekit Python SDK) against running Docker containers, not via browser automation.

**Rationale:** WebRTC audio I/O in headless browsers is flaky and complex to set up. The LiveKit Python SDK can join rooms, publish/subscribe to tracks, and send data channel messages programmatically — covering the same paths without browser overhead.

**Alternatives considered:**
- Playwright with WebRTC mocking — fragile, doesn't test real media flow
- Manual-only testing — not repeatable, doesn't catch regressions

**Test architecture:**
```
tests/e2e/
├── conftest.py          # Docker Compose readiness checks, test user creation
├── test_auth_flow.py    # register → verify → login → refresh
├── test_session_flow.py # start session → join room → verify agent joins
├── test_text_chat.py    # send text via data channel → receive response
├── test_voice_flow.py   # publish audio → verify STT transcript + LLM response
├── test_source_attribution.py  # RAG query → verify sources endpoint
├── test_crisis_protocol.py     # send crisis text → verify override response + contacts
├── test_bilingual.py    # repeat key flows in Russian and English
└── test_proactive.py    # join room, stay silent → verify proactive utterance
```

Tests assume Docker Compose is already running (`docker compose up`). A `conftest.py` fixture verifies all health checks pass before tests start.

### D2. Load testing tool: Locust (Python)

**Decision:** Use Locust for load testing, targeting 30 concurrent simulated users.

**Rationale:**
- Pure Python — consistent with the rest of the backend stack
- Supports custom protocols via User classes — we can wrap LiveKit SDK calls
- Web UI for real-time monitoring during test runs
- Simple to write and extend

**Alternatives considered:**
- k6 (JavaScript/Go) — requires writing tests in JS, another language in the stack
- Artillery — Node-based, same concern
- Custom asyncio script — no monitoring UI, reinventing the wheel

**Load test structure:**
```
tests/load/
├── locustfile.py        # Main load test: auth + session + text chat cycles
├── livekit_user.py      # Custom Locust User for LiveKit room operations
└── README.md            # Instructions for running load tests
```

**What is measured:**
- API response times (p50, p95, p99) under load
- Session establishment time (room join latency)
- Agent response latency (text message round-trip via data channel)
- Error rate across all endpoints
- Resource utilization (Docker stats during test)

**Target:** 30 concurrent users, 5-minute sustained load, <5% error rate, p95 API response <500ms.

### D3. Service Worker update strategy: prompt-based via `onNeedRefresh`

**Decision:** Replace `skipWaiting` + `clientsClaim` with `registerType: "prompt"` and an `onNeedRefresh` callback that shows a UI banner asking the user to reload.

**Rationale:** Force-updating the Service Worker during an active LiveKit WebRTC session disconnects the user. The prompt approach lets the user choose when to reload — ideally between sessions.

**Implementation:**
1. `vite.config.ts`: Change `registerType` to `"prompt"`, remove `skipWaiting` and `clientsClaim` from workbox config
2. `main.tsx`: Replace `registerSW({ immediate: true })` with `useRegisterSW` hook from `virtual:pwa-register/react` that provides `needRefresh` state and `updateServiceWorker()` function
3. New component `UpdatePrompt`: renders a non-intrusive banner when `needRefresh` is true, with "Update" and "Later" buttons
4. Banner appears at the top of the screen, does not block interaction
5. If user clicks "Update", call `updateServiceWorker(true)` which activates the waiting SW and reloads
6. If user clicks "Later", dismiss the banner; it reappears on next navigation or page focus

**Alternatives considered:**
- Keep `autoUpdate` but defer during active sessions — requires detecting LiveKit connection state in the SW registration logic, more complex
- Use `navigator.serviceWorker.controller.postMessage()` to coordinate — overengineered for MVP

### D4. Seed data finalization approach

**Decision:** Review and update `scripts/seed.py` in place. No structural changes needed.

**What changes:**
- Add missing Russian prompt translations (currently only `mode_voice_guidance` and `mode_text_guidance` exist for `ru`)
- Review English prompt quality for production (wording, clarity)
- Verify crisis contacts are accurate and up-to-date
- Ensure TTS config reflects final voice settings

### D5. Test location: separate `tests/e2e/` and `tests/load/` at repo root

**Decision:** E2E and load tests live at the repo root, not inside `apps/*/tests/`.

**Rationale:** These tests exercise the full stack across multiple apps. Placing them in any single app's test directory would be misleading. Root-level `tests/` makes the cross-cutting nature explicit.

**Alternatives considered:**
- Inside `apps/api/tests/e2e/` — confusing since tests also exercise agent and web
- New `apps/e2e/` app — unnecessary overhead for test-only code

## Risks / Trade-offs

**[E2E tests require running Docker Compose]** → Tests are designed to run against a live stack. A `conftest.py` fixture checks health endpoints and fails fast with a clear message if services are down. Document the prerequisite in `tests/e2e/README.md`.

**[E2E tests depend on external API keys (Deepgram, LLM, TTS)]** → Voice flow tests that need real STT/LLM/TTS are marked with `@pytest.mark.external` and skipped by default. Text-only flows work with LiteLLM proxy. Document which tests need which keys.

**[Locust load tests may hit rate limits on external providers]** → Load tests use text-only mode (data channel → LLM → data channel) to avoid Deepgram/TTS rate limits. Voice load testing is a non-goal for MVP.

**[Service Worker prompt may be ignored by users]** → Acceptable risk. The banner reappears on focus/navigation. Old SW continues to serve cached shell, which is functional. Critical API calls are NetworkFirst, so data freshness is maintained.

**[Bilingual test coverage is limited to prompt/response language, not STT accuracy]** → STT accuracy in different languages depends on Deepgram's models, not our code. We verify that the system passes the correct language setting and that prompts load for both locales.

## Migration Plan

1. **Service Worker change** is backward-compatible — old cached SW will be replaced naturally on next visit after deployment
2. **Seed data changes** are idempotent (upserts) — running `seed.py` again updates in place
3. **New test directories** (`tests/e2e/`, `tests/load/`) are additive, no existing tests affected
4. **Timeout/threshold tuning** changes are config-only and can be reverted via seed data

No rollback needed — all changes are safe to deploy incrementally.

## Open Questions

1. **Which external API keys are available for E2E testing?** — Determines whether voice flow E2E tests can run or must stay `@pytest.mark.external`-skipped
2. **What are the actual production voice/language settings for TTS?** — Need to finalize `seed_tts_config()` values (voice_id, model_id, speed, expressiveness)
3. **Should Russian prompts be full translations or adapted versions of English prompts?** — Currently `ru` locale only has mode guidance; full prompt set needs review
4. **Target VPS specs for load test baseline?** — 30 concurrent sessions on what hardware?
