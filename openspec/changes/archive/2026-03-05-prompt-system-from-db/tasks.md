## 1. Prompt Builder module

- [x] 1.1 Define `PROMPT_LAYER_ORDER` constant and `FALLBACK_SYSTEM_PROMPT` in `apps/agent/src/prompts.py`, remove the old `SYSTEM_PROMPT` constant
- [x] 1.2 Implement `load_prompt_layers(db_sessionmaker) -> dict[str, str]` — async function that SELECTs active rows from `agent_config` where key is in `PROMPT_LAYER_ORDER`
- [x] 1.3 Implement `build_instructions(layers: dict[str, str]) -> str` — assembles layers into a single string in `PROMPT_LAYER_ORDER` order, separated by double newlines
- [x] 1.4 Unit tests for `build_instructions`: all layers, partial layers, empty dict

## 2. Config snapshot

- [x] 2.1 Implement `save_config_snapshot(db_sessionmaker, session_id, layers) -> None` — async function that UPDATEs `sessions.agent_config_snapshot` with layers dict, versions, and `_meta.snapshot_at` timestamp
- [x] 2.2 Unit test for snapshot JSON structure (layers, `_version`, `_meta.snapshot_at`)

## 3. Entrypoint integration

- [x] 3.1 In `entrypoint()` (`main.py`): after `resolve_session_id()`, call `load_prompt_layers()` and `build_instructions()` with try/except fallback to `FALLBACK_SYSTEM_PROMPT`
- [x] 3.2 In `entrypoint()`: call `save_config_snapshot()` when `db_session_id` is not None
- [x] 3.3 Pass built instructions to `TwypeAgent(instructions=...)` instead of importing `SYSTEM_PROMPT`

## 4. Seed data update

- [x] 4.1 Replace placeholder prompt texts in `scripts/seed.py` `PROMPT_LAYERS` dict with meaningful Russian-language prompts for all 8 layers
- [x] 4.2 Verify seed script idempotency (existing tests or manual run)

## 5. Tests and verification

- [x] 5.1 Integration test: `load_prompt_layers` returns expected keys from a seeded database (or mock)
- [x] 5.2 Verify agent starts successfully with prompts from DB (manual or docker compose test)
