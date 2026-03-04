## Why

Проект находится на стадии «архитектура и спецификации готовы, кода нет». Прежде чем реализовывать бизнес-логику (аутентификация, voice pipeline, RAG), необходимо развернуть скелет проекта: monorepo-структуру, Docker Compose с семью контейнерами-заглушками и конфигурации инфраструктурных сервисов. Без этого фундамента невозможно параллельно работать над API, агентом и фронтендом — каждая последующая стори (S02–S25) опирается на работающую Docker-среду.

## What Changes

- Создание monorepo-структуры: `apps/api/`, `apps/agent/`, `apps/web/`, `packages/shared/`, `docker/`, `configs/`, `scripts/`, корневые workspace-файлы
- Корневой `pyproject.toml` (uv workspace для `apps/api` + `apps/agent`) с конфигурацией Ruff
- Корневой `package.json` (bun workspace для `apps/web`)
- `apps/api/` — минимальное FastAPI-приложение: `main.py` с health-эндпоинтом, `pyproject.toml`
- `apps/agent/` — минимальный LiveKit Agent: `main.py`-заглушка, `pyproject.toml`
- `apps/web/` — Vite + React scaffold: `main.tsx`, `package.json`, `tsconfig.json`, ESLint flat config, Prettier
- `docker/docker-compose.yml` (production) и `docker/docker-compose.dev.yml` (development) с семью сервисами: `caddy`, `api`, `livekit`, `agent`, `litellm`, `postgres`, `coturn`
- Dockerfiles: `docker/Dockerfile.api`, `docker/Dockerfile.agent`, `docker/Dockerfile.web` (multi-stage, dev/prod targets)
- Конфигурации инфраструктурных сервисов: `configs/livekit.yaml`, `configs/litellm.yaml`, `configs/caddy/Caddyfile`, `configs/coturn/turnserver.conf`
- Внутренняя Docker-сеть `twype-net`, именованные volumes (`pgdata`, `caddy-data`, `caddy-config`)
- Health checks для всех контейнеров
- `.env.example` со всеми переменными окружения (без реальных секретов)
- `.gitignore` для Python, Node.js, Docker, .env
- Корневой `Makefile` с self-documenting help — единая точка входа для всех команд разработки (`make dev`, `make up`, `make lint`, `make test`, `make install` и др.)

## Capabilities

### New Capabilities

- `docker-stack`: Docker Compose оркестрация — определение семи контейнеров (caddy, api, livekit, agent, litellm, postgres, coturn), сетевая топология, volumes, health checks, порты, зависимости между сервисами. Dev- и production-конфигурации.
- `project-scaffold`: Monorepo-структура — каталоги apps/api, apps/agent, apps/web с минимальными заглушками приложений, корневые workspace-файлы (uv + bun), конфигурация линтинга (Ruff, ESLint, Prettier), Makefile как единая точка входа, шаблон переменных окружения.
- `infrastructure-configs`: Конфигурационные файлы инфраструктурных сервисов — LiveKit Server (livekit.yaml), LiteLLM Proxy (litellm.yaml), Caddy reverse proxy (Caddyfile), coturn TURN-сервер (turnserver.conf).

### Modified Capabilities

_(нет существующих capabilities)_

## Impact

- **Файловая структура**: создаётся с нуля (~30-40 файлов)
- **Зависимости**: Python-зависимости (FastAPI, uvicorn, livekit-agents, ruff, pytest), Node-зависимости через bun (React, Vite, TypeScript, ESLint, Prettier)
- **Инфраструктура**: требуется Docker Engine 27+ и Docker Compose 2.30+ на машине разработчика
- **Сетевая модель**: определяются порты и сетевые маршруты между контейнерами (внутренняя сеть + внешние порты)
- **Все последующие стори** (S02–S25) зависят от этой инфраструктуры
