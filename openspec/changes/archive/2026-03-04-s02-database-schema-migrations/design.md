## Context

S01 развернула monorepo с Docker Compose и контейнерами-заглушками. PostgreSQL 18 + pgvector работает, но без схемы. `apps/api/pyproject.toml` содержит только fastapi, uvicorn, pydantic. Модели и миграции отсутствуют.

Оба Python-приложения (api и agent) будут работать с одной БД. Сейчас они — отдельные пакеты в uv workspace (`apps/api`, `apps/agent`).

## Goals / Non-Goals

**Goals:**
- Определить все таблицы MVP как SQLAlchemy 2.0 async-модели
- Настроить Alembic с автогенерацией миграций
- Обеспечить доступ к моделям и сессиям из обоих приложений (api и agent)
- Создать seed-скрипт для удобства разработки

**Non-Goals:**
- HNSW-индексы на vector-колонках (создаются в S13 при реальной загрузке данных, когда определена embedding-модель и размерность)
- Миграции с downgrade (forward-only для MVP)
- ORM-level валидация (валидация — на уровне Pydantic-схем в S03+)
- Shared Python-пакет в `packages/` (преждевременно, пока достаточно прямых импортов через workspace)

## Decisions

### 1. Модели живут в `apps/api/src/models/`, agent импортирует через workspace dependency

**Решение:** Модели определяются в `apps/api/src/models/`. Agent добавляет `twype-api` как workspace-зависимость в своём `pyproject.toml` и импортирует модели напрямую.

**Альтернатива:** Создать `packages/shared/` с моделями. Отклонено — это единственный shared-код на данный момент, вводить третий пакет преждевременно. Перенести можно в любой момент.

**Альтернатива 2:** Дублировать модели в agent. Отклонено — нарушает DRY, рассинхронизация неизбежна.

### 2. Database session factory в `apps/api/src/database.py`

**Решение:** Один модуль `database.py` с `create_async_engine` и `async_sessionmaker`. Оба приложения используют один и тот же модуль. Конфигурация через `DATABASE_URL` из env.

**Обоснование:** Минимальный подход, не требует абстракций. При необходимости разных настроек пула для api и agent — можно параметризовать позже.

### 3. Naming convention через SQLAlchemy MetaData

**Решение:** Задать naming convention в `MetaData` объекте Base:

```python
convention = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

**Обоснование:** Alembic autogenerate корректно подхватывает naming convention из MetaData. Все имена constraint'ов генерируются автоматически и консистентно.

### 4. Vector-колонка без фиксированной размерности

**Решение:** В начальной миграции `embedding` колонка создаётся как `Vector()` без указания размерности. Размерность будет зафиксирована в S13, когда определена embedding-модель.

**Альтернатива:** Зафиксировать 768 или 1536 сейчас. Отклонено — преждевременное решение, зависит от выбора embedding-модели.

### 5. pgvector extension — в Alembic миграции, не в Docker entrypoint

**Решение:** `CREATE EXTENSION IF NOT EXISTS vector` выполняется в первой Alembic миграции как `op.execute()`.

**Альтернатива:** SQL-скрипт в Docker entrypoint postgres. Отклонено — extension логически связана с миграцией схемы, должна быть в одном месте. Alembic — единственный источник правды о состоянии БД.

### 6. Seed-скрипт: upsert через `ON CONFLICT`

**Решение:** Seed использует `INSERT ... ON CONFLICT (unique_key) DO UPDATE` для идемпотентности. Скрипт запускается вручную или при dev-старте.

**Обоснование:** Позволяет безопасно перезапускать seed без очистки БД. При обновлении seed-данных достаточно перезапустить скрипт.

### 7. Миграции при старте api-контейнера

**Решение:** Docker entrypoint api-контейнера: `alembic upgrade head && uvicorn ...`. В dev-compose — через shell command.

**Обоснование:** Гарантирует актуальность схемы при каждом старте. Для MVP это безопасно (один экземпляр api). В production с несколькими репликами потребуется init-container или отдельный migration-job.

## Risks / Trade-offs

- **Agent зависит от api-пакета** → Создаёт coupling между пакетами. Митигация: при росте — вынести модели в `packages/shared/`. Сейчас overhead не оправдан.
- **Forward-only миграции** → Нет возможности откатить миграцию. Митигация: для MVP допустимо; при ошибке — новая корректирующая миграция.
- **Vector без размерности** → Нельзя создать HNSW-индекс до фиксации размерности. Митигация: индекс создаётся в S13, когда данные уже загружены.
- **Миграции в entrypoint** → При ошибке миграции контейнер не стартует. Митигация: для MVP — желаемое поведение (fail fast); логи видны в `docker compose logs`.

## Open Questions

_(нет — все решения приняты на основе документации проекта)_
