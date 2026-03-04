## 1. Корневые файлы и monorepo-структура

- [x] 1.1 Создать структуру каталогов: `apps/api/src/`, `apps/agent/src/`, `apps/web/src/`, `packages/shared/`, `docker/`, `configs/caddy/`, `configs/coturn/`, `scripts/`
- [x] 1.2 Создать корневой `pyproject.toml` с uv workspace (members: `apps/api`, `apps/agent`), конфигурацией Ruff (target-version py313, line-length 100, правила из specs.md), dev-зависимостями (ruff, pytest, pytest-asyncio)
- [x] 1.3 Создать корневой `package.json` с bun workspace (member: `apps/web`)
- [x] 1.4 Создать `.env.example` со всеми переменными из specs.md раздел 11 (API, Agent, LiteLLM, coturn) с комментариями-описаниями
- [x] 1.5 Создать `.gitignore` (Python, Node.js, Docker, .env, IDE)
- [x] 1.6 Создать корневой `Makefile` с self-documenting help и таргетами: `help` (default), `install` (uv sync + bun install), `dev` (docker compose dev up), `up` (docker compose prod up -d), `down` (docker compose down), `logs` (docker compose logs -f), `lint` (ruff check + eslint), `format` (ruff format + prettier --write), `test` (pytest + vitest), `clean` (удаление кэшей и артефактов)

## 2. FastAPI stub (apps/api)

- [x] 2.1 Создать `apps/api/pyproject.toml` с зависимостями: fastapi, uvicorn, pydantic (минимальные версии из specs.md)
- [x] 2.2 Создать `apps/api/src/__init__.py` и `apps/api/src/main.py` с FastAPI app и эндпоинтом `GET /health` → `{"status": "ok"}`
- [x] 2.3 Проверить: `uv run ruff check apps/api/` и `uv run ruff format --check apps/api/` проходят без ошибок

## 3. LiveKit Agent stub (apps/agent)

- [x] 3.1 Создать `apps/agent/pyproject.toml` с зависимостями: livekit-agents, livekit-plugins-silero (минимальные версии из specs.md)
- [x] 3.2 Создать `apps/agent/src/__init__.py` и `apps/agent/src/main.py` с WorkerOptions, entrypoint, и stub-обработчиком job (логирует "agent started", подключается к комнате, без pipeline)
- [x] 3.3 Проверить: `uv run ruff check apps/agent/` проходит без ошибок

## 4. React PWA stub (apps/web)

- [x] 4.1 Scaffold Vite + React + TypeScript проект в `apps/web/` через `bun create vite` (или вручную): `package.json`, `vite.config.ts`, `tsconfig.json` (strict mode, noUncheckedIndexedAccess, exactOptionalPropertyTypes)
- [x] 4.2 Создать `apps/web/src/main.tsx` и `apps/web/src/App.tsx` с `<h1>Twype</h1>`
- [x] 4.3 Настроить ESLint 9 flat config (`eslint.config.js`) и Prettier (`.prettierrc`)
- [x] 4.4 Проверить: `bunx tsc --noEmit`, `bunx eslint .`, `bunx prettier --check .` проходят без ошибок

## 5. Конфигурации инфраструктурных сервисов

- [x] 5.1 Создать `configs/livekit.yaml`: dev API key/secret, порты, TURN-интеграция с coturn
- [x] 5.2 Создать `configs/litellm.yaml`: определение модели Gemini Flash-Lite (с плейсхолдером API key), health check endpoint
- [x] 5.3 Создать `configs/caddy/Caddyfile`: reverse proxy `/api/*` → `api:8000`, WebSocket proxy для LiveKit signaling → `livekit:7880`, localhost dev-режим
- [x] 5.4 Создать `configs/coturn/turnserver.conf`: listening-port 3478, TLS-порт 5349, relay-диапазон 49152-65535, credentials из env

## 6. Dockerfiles

- [x] 6.1 Создать `docker/Dockerfile.api`: base `ghcr.io/astral-sh/uv:python3.13-bookworm-slim`, target `dev` (volume-ready, uvicorn --reload), target `prod` (copy source, install deps, uvicorn)
- [x] 6.2 Создать `docker/Dockerfile.agent`: base `ghcr.io/astral-sh/uv:python3.13-bookworm-slim`, target `dev` (volume-ready, livekit agents dev), target `prod` (copy source)
- [x] 6.3 Создать `docker/Dockerfile.web`: target `dev` (oven/bun:slim, vite --host), target `prod` (oven/bun:slim build → nginx:alpine serve)

## 7. Docker Compose

- [x] 7.1 Создать `docker/docker-compose.yml` (production): 7 сервисов, сеть `twype-net`, volumes (pgdata, caddy-data, caddy-config), health checks, depends_on с service_healthy, порты по сетевой карте из architecture.md
- [x] 7.2 Создать `docker/docker-compose.dev.yml` (development): наследует инфраструктурные сервисы, переопределяет api/agent/web с volume-маунтами, hot-reload командами, дополнительный порт 5173 для web
- [x] 7.3 Проверить: `docker compose -f docker/docker-compose.dev.yml config` валидирует оба файла без ошибок

## 8. Интеграционная проверка

- [x] 8.1 Запустить `docker compose -f docker/docker-compose.dev.yml up`, убедиться: все 7 контейнеров в состоянии healthy
- [x] 8.2 Проверить: `curl localhost:5173` отдаёт React-страницу, `curl localhost/api/health` через Caddy возвращает `{"status": "ok"}`
- [x] 8.3 Проверить: изменение файла в `apps/api/src/` вызывает автоматический reload uvicorn
- [x] 8.4 Проверить: `make install` устанавливает все зависимости, `make lint` проходит без ошибок, `make help` выводит список команд
