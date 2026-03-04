## Why

S01 создала Docker-инфраструктуру с контейнером PostgreSQL, но без схемы данных. Все последующие стори (S03 — аутентификация, S04 — сессии, S05+ — агент) зависят от таблиц в БД. Без моделей, миграций и seed-данных дальнейшая разработка заблокирована.

## What Changes

- SQLAlchemy 2.0 async-модели для всех таблиц MVP: `users`, `sessions`, `messages`, `knowledge_sources`, `knowledge_chunks`, `agent_config`, `tts_config`
- Расширение pgvector (`CREATE EXTENSION IF NOT EXISTS vector`)
- Alembic-инфраструктура в `apps/api/migrations/` с начальной миграцией
- Naming convention для индексов, FK и constraints (автоматическая через SQLAlchemy `MetaData`)
- Seed-скрипт `scripts/seed.py` с тестовыми данными: пользователь, конфигурация агента (промпты), TTS-настройки
- Добавление Python-зависимостей в `apps/api/pyproject.toml`: sqlalchemy, asyncpg, alembic, pgvector
- Database session factory (`async_sessionmaker`) с shared-модулем для доступа из api и agent

## Capabilities

### New Capabilities

- `database-models`: SQLAlchemy 2.0 async-модели всех таблиц (users, sessions, messages, knowledge_sources, knowledge_chunks, agent_config, tts_config), naming conventions, Base class
- `database-migrations`: Alembic-инфраструктура, начальная миграция, pgvector extension, forward-only policy
- `database-seed`: Seed-скрипт с начальными данными для разработки (тестовый пользователь, промпты агента, TTS-конфигурация)

### Modified Capabilities

_(нет существующих capabilities с изменением требований)_

## Impact

- **apps/api/**: новые директории `src/models/`, `migrations/`, зависимости в `pyproject.toml`
- **apps/agent/**: будет использовать те же модели (через workspace) — пока без изменений
- **scripts/seed.py**: новый скрипт
- **docker/**: контейнер postgres уже настроен, изменений не требуется; api-контейнер должен запускать миграции при старте
- **Зависимости**: sqlalchemy >=2.0.48, asyncpg >=0.31.0, alembic >=1.18.4, pgvector >=0.4.2
