## 1. Зависимости и инфраструктура

- [x] 1.1 Добавить sqlalchemy, asyncpg, alembic, pgvector в `apps/api/pyproject.toml`, запустить `uv lock`
- [x] 1.2 Добавить `twype-api` как workspace-зависимость в `apps/agent/pyproject.toml`, запустить `uv lock`

## 2. Base class и database session

- [x] 2.1 Создать `apps/api/src/models/__init__.py` с декларативным Base (naming convention для ix, uq, ck, fk, pk)
- [x] 2.2 Создать `apps/api/src/database.py` с `create_async_engine`, `async_sessionmaker` и async context manager для сессий (DATABASE_URL из env)

## 3. SQLAlchemy модели

- [x] 3.1 Создать модель `User` в `apps/api/src/models/user.py` (users: id, email, password_hash, is_verified, verification_code, verification_expires_at, preferences, created_at, updated_at)
- [x] 3.2 Создать модель `Session` в `apps/api/src/models/session.py` (sessions: id, user_id FK, room_name, status, agent_config_snapshot, started_at, ended_at)
- [x] 3.3 Создать модель `Message` в `apps/api/src/models/message.py` (messages: id, session_id FK, role, mode, content, voice_transcript, sentiment_raw, valence, arousal, source_ids, created_at)
- [x] 3.4 Создать модель `KnowledgeSource` в `apps/api/src/models/knowledge_source.py` (knowledge_sources: id, source_type, title, author, url, language, tags, created_at)
- [x] 3.5 Создать модель `KnowledgeChunk` в `apps/api/src/models/knowledge_chunk.py` (knowledge_chunks: id, source_id FK, content, section, page_range, embedding Vector(), search_vector TSVector, token_count, created_at)
- [x] 3.6 Создать модель `AgentConfig` в `apps/api/src/models/agent_config.py` (agent_config: id, key UK, value, version, is_active, created_at, updated_at)
- [x] 3.7 Создать модель `TTSConfig` в `apps/api/src/models/tts_config.py` (tts_config: id, voice_id, model_id, expressiveness, speed, language, is_active, created_at)
- [x] 3.8 Реэкспортировать все модели из `apps/api/src/models/__init__.py`

## 4. Alembic

- [x] 4.1 Инициализировать Alembic в `apps/api/` с async-шаблоном, настроить `alembic.ini` и `env.py` (импорт всех моделей, DATABASE_URL из env)
- [x] 4.2 Создать начальную миграцию: `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` + autogenerate всех таблиц
- [x] 4.3 Обновить entrypoint api-контейнера в `docker/Dockerfile.api` — `alembic upgrade head` перед запуском uvicorn

## 5. Seed-скрипт

- [x] 5.1 Создать `scripts/seed.py`: тестовый пользователь (test@twype.local, is_verified=true, bcrypt-хеш)
- [x] 5.2 Добавить в seed AgentConfig записи для 8 промпт-слоёв (system_prompt, voice_prompt, dual_layer_prompt, emotion_prompt, crisis_prompt, rag_prompt, language_prompt, proactive_prompt) с placeholder-текстом на русском
- [x] 5.3 Добавить в seed TTSConfig для Inworld (model_id="inworld-tts-1.5-max", language="ru")
- [x] 5.4 Реализовать идемпотентность через INSERT ... ON CONFLICT DO UPDATE

## 6. Проверка

- [x] 6.1 Запустить `docker compose -f docker/docker-compose.dev.yml up`, убедиться что миграции применяются и все таблицы создаются
- [x] 6.2 Запустить seed-скрипт, проверить данные в БД
- [x] 6.3 Запустить `uv run ruff check . && uv run ruff format --check .` — убедиться что код проходит линтинг
