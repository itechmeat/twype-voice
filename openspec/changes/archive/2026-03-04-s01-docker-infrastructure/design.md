## Context

Проект Twype — greenfield monorepo без единого файла кода. Архитектура определена в `docs/architecture.md`: 7 Docker-контейнеров на одном VPS, три кастомных приложения (api, agent, web) и четыре инфраструктурных сервиса (livekit, litellm, postgres с pgvector, caddy, coturn). Технические спецификации зафиксированы в `docs/specs.md` — минимальные версии, структура каталогов, coding conventions.

Задача S01 — создать работающий скелет: все контейнеры стартуют, отвечают health check, но не содержат бизнес-логики. Это фундамент для всех последующих сторей.

## Goals / Non-Goals

**Goals:**

- Все 7 контейнеров стартуют через `docker compose up` (dev и prod) без ошибок
- Каждый контейнер проходит health check
- Контейнеры видят друг друга по именам через внутреннюю сеть
- Python workspace (uv) и Node workspace (bun) корректно резолвят зависимости
- Линтинг проходит без ошибок на stub-коде (ruff, eslint, prettier)
- `.env.example` содержит все переменные, документированные в `docs/specs.md`

**Non-Goals:**

- Бизнес-логика в API, агенте или фронтенде (стори S02+)
- Alembic-миграции и схема БД (стори S02)
- Аутентификация (стори S03)
- Реальные SSL-сертификаты (dev-среда работает на localhost)
- CI/CD pipeline
- Production-деплой на VPS

## Decisions

### D1. Образы инфраструктурных контейнеров

**Решение:** использовать официальные образы без кастомных Dockerfiles:

- `postgres`: `pgvector/pgvector:pg18` (PostgreSQL 18 с предустановленным pgvector)
- `livekit`: `livekit/livekit-server:latest`
- `litellm`: `ghcr.io/berriai/litellm:main-latest`
- `caddy`: `caddy:2-alpine`
- `coturn`: `coturn/coturn:latest`

**Альтернатива:** собирать кастомные образы для каждого. Отклонено — нет кастомизаций, лишняя сложность.

### D2. Multi-stage Dockerfiles для кастомных приложений

**Решение:** три Dockerfile с двумя targets каждый (`dev` и `prod`):

- `dev` target: volume-маунт исходников, hot-reload (uvicorn --reload, vite --host, livekit agents dev)
- `prod` target: копирование исходников в образ, оптимизированная сборка

**Альтернатива:** отдельные Dockerfile.dev и Dockerfile.prod. Отклонено — дублирование базовых слоёв.

### D3. Базовые образы

**Решение:**

- `api` и `agent`: `ghcr.io/astral-sh/uv:python3.13-bookworm-slim` — образ с предустановленным uv и Python 3.13
- `web`: `oven/bun:slim` для dev, multi-stage с `nginx:alpine` для prod static serving

**Альтернатива (Python):** `python:3.13-slim` + установка uv. Отклонено — uv-образ быстрее в CI, меньше слоёв.
**Альтернатива (Web):** `node:24-slim`. Отклонено — bun выбран как runtime и менеджер пакетов (в 30x быстрее npm при установке, нативный TypeScript).

### D4. Docker Compose: два файла vs override

**Решение:** два самостоятельных файла — `docker-compose.yml` (prod) и `docker-compose.dev.yml` (dev).

**Альтернатива:** `docker-compose.yml` + `docker-compose.override.yml`. Отклонено — override-подход неявный, легко запустить prod с dev-настройками. Два явных файла безопаснее.

### D5. Сетевая модель

**Решение:** одна bridge-сеть `twype-net`. Все контейнеры в одной сети, обращаются друг к другу по имени сервиса (например, `postgres:5432`, `litellm:4000`).

Внешние порты (dev-среда):

- `caddy`: 80, 443
- `livekit`: 7880 (внутренний), 7881 TCP, 50000-60000 UDP
- `coturn`: 3478, 5349, 49152-65535 UDP
- `web` (только dev): 5173

**Альтернатива:** несколько сетей (frontend/backend). Отклонено — для одного VPS с 7 контейнерами избыточно.

### D6. Управление Python-зависимостями: workspace

**Решение:** корневой `pyproject.toml` определяет uv workspace с members `apps/api` и `apps/agent`. Каждый app имеет свой `pyproject.toml` с зависимостями. Общие dev-зависимости (ruff, pytest) в корневом файле.

`uv sync` из корня устанавливает зависимости всех членов workspace в единый lockfile.

### D7. Makefile как единая точка входа

**Решение:** корневой `Makefile` с self-documenting help (`make` без аргументов выводит список команд). Все основные операции доступны через make-таргеты: `make dev`, `make up`, `make down`, `make install`, `make lint`, `make format`, `make test`, `make logs`, `make clean`. Таргеты оборачивают длинные docker compose и uv/bun команды в короткие запоминаемые алиасы.

**Альтернатива:** bash-скрипты в `scripts/`. Отклонено — Make стандартен, поддерживает зависимости между таргетами, параллельное выполнение (`make -j lint test`), и не требует установки.

### D8. Stub-приложения: минимальная функциональность

**Решение:**

- `apps/api`: FastAPI с единственным эндпоинтом `GET /health` → `{"status": "ok"}`
- `apps/agent`: Python-скрипт с `WorkerOptions`, подключающийся к LiveKit, но без реального pipeline (логирует "agent started")
- `apps/web`: Vite + React scaffold с `<h1>Twype</h1>` и рабочим dev-сервером

Достаточно для проверки: контейнеры стартуют, health checks проходят, hot-reload работает.

## Risks / Trade-offs

**[Версии образов могут быть несовместимы]** → Зафиксировать мажорные версии в Compose (не `latest`). Для инфраструктурных сервисов использовать конкретные теги при первом успешном запуске.

**[pgvector/pgvector:pg18 может не существовать на момент реализации]** → Проверить Docker Hub. Fallback: `postgres:18` + установка pgvector через `CREATE EXTENSION`.

**[LiveKit Agent не подключится без валидных API key/secret]** → В dev-конфигурации LiveKit Server генерирует тестовые ключи. `.env.example` содержит плейсхолдеры, `configs/livekit.yaml` задаёт dev-ключи.

**[LiteLLM требует хотя бы один настроенный провайдер]** → В dev-среде `configs/litellm.yaml` содержит заглушку-модель. Контейнер стартует, health check проходит, реальные провайдеры не нужны.

**[coturn требует внешний IP для TURN]** → В dev-среде TURN не обязателен (localhost). Конфигурация с плейсхолдером `EXTERNAL_IP`, который задаётся через `.env`.
