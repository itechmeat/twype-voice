## 1. Dependencies and configuration

- [x] 1.1 Add `livekit-plugins-noise-cancellation` to `apps/agent/pyproject.toml` and run `uv sync`
- [x] 1.2 Add new fields to `AgentSettings`: `TURN_DETECTION_MODE`, `MIN_ENDPOINTING_DELAY`, `MAX_ENDPOINTING_DELAY`, `PREEMPTIVE_GENERATION`, `NOISE_CANCELLATION_ENABLED`, `FALSE_INTERRUPTION_TIMEOUT`, `MIN_INTERRUPTION_DURATION`, `THINKING_SOUNDS_ENABLED`, `THINKING_SOUNDS_DELAY` with defaults and validators
- [x] 1.3 Add all new environment variables to `.env.example` with descriptive comments

## 2. Turn detection and endpointing

- [x] 2.1 Update `build_session()` in `agent.py`: replace `turn_detection="vad"` with `settings.TURN_DETECTION_MODE`, pass `min_endpointing_delay`, `max_endpointing_delay`, `preemptive_generation`, `false_interruption_timeout`, `resume_false_interruption=True`, `min_interruption_duration` from settings
- [x] 2.2 Update `build_session()` signature to accept new parameters from settings

## 3. Noise cancellation

- [x] 3.1 Add noise cancellation initialization in `prewarm()`: conditionally create noise cancellation instance based on `NOISE_CANCELLATION_ENABLED` and store in `proc.userdata`
- [x] 3.2 Wire noise cancellation into the agent pipeline in `entrypoint()` — apply to incoming audio before VAD/STT

## 4. Thinking sounds

- [x] 4.1 Create filler phrases mapping in `agent.py` with per-language phrases for `"ru"` and `"en"`, fallback to English
- [x] 4.2 Override `llm_node` in `TwypeAgent`: implement delay detection with `asyncio.wait_for`, yield filler text when LLM first token exceeds `THINKING_SOUNDS_DELAY`, then yield remaining LLM stream
- [x] 4.3 Pass `THINKING_SOUNDS_ENABLED` and `THINKING_SOUNDS_DELAY` to `TwypeAgent` so the override can check configuration

## 5. Tests

- [x] 5.1 Add unit tests for new `AgentSettings` fields: defaults, custom values, validation errors
- [x] 5.2 Add unit tests for `build_session()` verifying turn detection, endpointing, and interruption parameters are passed correctly
- [x] 5.3 Add unit tests for `TwypeAgent.llm_node` thinking sounds: filler generated on delay, no filler when fast, disabled when `THINKING_SOUNDS_ENABLED=False`
- [x] 5.4 Add unit test for noise cancellation conditional initialization in `prewarm()`

## 6. Documentation

- [x] 6.1 Update `docker/docker-compose.dev.yml` if noise cancellation requires additional config
- [ ] 6.2 Mark S09 as complete in `docs/plan.md`
