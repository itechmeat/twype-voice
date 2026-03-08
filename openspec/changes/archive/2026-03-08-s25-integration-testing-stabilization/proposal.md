## Why

All 24 implementation stories (S01–S24) are complete. The system has unit tests per feature but lacks end-to-end verification of full user flows across all containers. Before declaring MVP-ready, we need to validate that every critical path works when all services run together, fix discovered issues, tune thresholds, and improve the Service Worker update strategy to avoid disrupting active LiveKit sessions.

## What Changes

- Add end-to-end integration tests covering the complete user journey: registration → login → start session → voice dialogue → text switch → source attribution → proactive utterance → session end
- Add bilingual test coverage (Russian and English) across the voice pipeline and prompt system
- Add crisis protocol end-to-end verification (trigger detection → pipeline override → emergency contacts)
- Add a load test scenario for 30 concurrent sessions to identify bottlenecks
- Fix bugs, tune timeouts and thresholds discovered during integration testing
- Improve Service Worker update strategy: replace `skipWaiting` + `clientsClaim` with `onNeedRefresh` callback to prompt the user instead of force-updating during active LiveKit sessions
- Finalize seed data and prompts for production readiness

## Capabilities

### New Capabilities
- `e2e-integration-tests`: End-to-end test suite covering full user flows across all Docker containers, bilingual scenarios, and crisis protocol verification
- `load-testing`: Load test configuration and scripts for verifying system behavior under 30 concurrent sessions
- `sw-update-prompt`: Service Worker update strategy using `onNeedRefresh` callback instead of force-updating, prompting users to reload when a new version is available

### Modified Capabilities
- `pwa-service-worker`: Replace `skipWaiting` + `clientsClaim` with user-prompted update flow to avoid disrupting active LiveKit WebRTC sessions
- `database-seed`: Finalize seed data and prompts for production readiness — review and update agent configs, prompts, and crisis contacts

## Impact

- **All containers**: E2E tests exercise the full Docker Compose stack (api, agent, web, livekit, litellm, postgres, caddy, coturn)
- **apps/web**: Service Worker update strategy change in `vite.config.ts` and new update prompt UI component
- **apps/api + apps/agent**: Potential timeout/threshold tuning based on integration test findings
- **scripts/seed.py**: Updated seed data for production-quality prompts and configurations
- **CI/CD**: New test targets for e2e and load tests (can be run separately from unit tests)
- **Dependencies**: May need a load testing tool (e.g., `locust` for Python or `k6`)
