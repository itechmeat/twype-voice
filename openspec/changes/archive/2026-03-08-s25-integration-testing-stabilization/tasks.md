## 1. Service Worker Update Prompt

- [x] 1.1 Update `vite.config.ts`: change `registerType` to `"prompt"`, remove `skipWaiting` and `clientsClaim` from workbox config
- [x] 1.2 Install `virtual:pwa-register/react` types if needed; update `main.tsx` to use `useRegisterSW` hook with `onNeedRefresh` and `onOfflineReady` callbacks instead of `registerSW({ immediate: true })`
- [x] 1.3 Create `UpdatePrompt` component: banner with "Update" and "Later" buttons, reappears on focus after dismissal
- [x] 1.4 Add unit test for `UpdatePrompt` component (render, click Update triggers reload, click Later dismisses)

## 2. Seed Data Finalization

- [x] 2.1 Add complete Russian prompt translations for all missing layers in `scripts/seed.py`: `system_prompt`, `voice_prompt`, `dual_layer_prompt`, `emotion_prompt`, `crisis_prompt`, `rag_prompt`, `language_prompt`, `proactive_prompt`
- [x] 2.2 Review and polish English prompt text for production quality (clarity, no placeholder language)
- [x] 2.3 Verify crisis contacts accuracy for both en/US and ru/RU locales
- [x] 2.4 Review TTS config values (voice_id, model_id, speed, expressiveness) for production readiness

## 3. E2E Test Infrastructure

- [x] 3.1 Create `tests/e2e/` directory with `conftest.py`: health check fixtures for all Docker Compose services, test user creation via API, authenticated client fixture
- [x] 3.2 Configure pytest markers: register `external` marker in `pyproject.toml`, add `pytest.ini` or config for `tests/e2e/`
- [x] 3.3 Create LiveKit room helper: utility to join a room via Python SDK, subscribe to agent, send/receive data channel messages

## 4. E2E Test Implementations

- [x] 4.1 `test_auth_flow.py`: register → verify (code from DB) → login → refresh token cycle
- [x] 4.2 `test_session_flow.py`: start session → join room → verify agent joins within 15s
- [x] 4.3 `test_text_chat.py`: send text via data channel → receive dual-layer response within 30s
- [x] 4.4 `test_source_attribution.py`: query matching seeded knowledge → verify `[N]` references → call sources endpoint
- [x] 4.5 `test_crisis_protocol.py`: send crisis phrase (en + ru) → verify crisis override response
- [x] 4.6 `test_bilingual.py`: send English message → English response; send Russian message → Russian response
- [x] 4.7 `test_proactive.py`: join room, stay silent 20s+ → verify proactive message received
- [x] 4.8 `test_session_history.py`: complete session with messages → verify history and messages endpoints

## 5. Load Testing

- [x] 5.1 Add `locust` to dev dependencies in root `pyproject.toml`
- [x] 5.2 Create `tests/load/livekit_user.py`: custom Locust User wrapping LiveKit SDK with timing instrumentation
- [x] 5.3 Create `tests/load/locustfile.py`: main load test with auth → session → text chat → end cycles for 30 concurrent users
- [x] 5.4 Create `tests/load/README.md`: run instructions, prerequisites, performance targets

## 6. Bug Fixes and Tuning

- [x] 6.1 Run full E2E suite, document discovered bugs and timeout issues
- [x] 6.2 Fix discovered bugs (scope TBD based on E2E results)
- [x] 6.3 Tune silence timer thresholds, turn detection timeouts, and agent join timeouts based on E2E observations
- [x] 6.4 Run load test baseline, document results and bottlenecks

## 7. Verification

- [x] 7.1 Run all existing unit tests (`pytest apps/api/tests/ apps/agent/tests/`, `bunx vitest` in apps/web) — confirm no regressions
- [x] 7.2 Run E2E test suite against Docker Compose stack — all non-external tests pass
- [x] 7.3 Run lint checks (`ruff check .`, `ruff format --check .`, `bunx eslint .`, `bunx prettier --check .`)
- [x] 7.4 Verify Service Worker update prompt works in production build (`bunx vite build` + serve)
