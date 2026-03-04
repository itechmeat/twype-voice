# Технические спецификации проекта

**Версия:** 1.0 — MVP
**Дата:** март 2026

> Этот документ определяет технологический стек, версии инструментов, структуру проекта и подходы к разработке. Описание продукта — в `docs/about.md`, архитектура — в `docs/architecture.md`.

---

## 1. Правило версий

**Запрещено понижать версии зависимостей ниже указанных минимумов.**

Версии, указанные в этом документе — минимально допустимые. Обновление вверх допускается и поощряется. Понижение версии допускается **только** при наличии документированного технического обоснования и явного утверждения.

Это правило распространяется на:
- Runtime-окружения (Python, Bun, PostgreSQL)
- Все Python- и bun-зависимости
- Docker-образы
- Тулчейн (uv, Vite, и т.д.)

При добавлении новой зависимости она фиксируется в этом документе с минимальной версией.

---

## 2. Структура monorepo

Проект организован как monorepo — frontend, backend API и агент живут в одном репозитории.

```
twype-voice/
├── apps/
│   ├── api/              # FastAPI REST API
│   │   ├── src/
│   │   │   ├── auth/     # Аутентификация, JWT
│   │   │   ├── routes/   # HTTP-эндпоинты
│   │   │   ├── models/   # SQLAlchemy-модели
│   │   │   ├── schemas/  # Pydantic-схемы
│   │   │   ├── services/ # Бизнес-логика
│   │   │   └── main.py   # Точка входа FastAPI
│   │   ├── migrations/   # Alembic-миграции
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   ├── agent/            # LiveKit Agent (voice pipeline)
│   │   ├── src/
│   │   │   ├── plugins/  # Кастомные плагины (Inworld TTS)
│   │   │   ├── prompts/  # Загрузка промптов из БД
│   │   │   ├── rag/      # RAG-поиск, эмбеддинги
│   │   │   ├── emotions/ # Circumplex-модель
│   │   │   └── main.py   # Точка входа агента
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   └── web/              # React PWA
│       ├── src/
│       │   ├── components/
│       │   ├── hooks/
│       │   ├── pages/
│       │   ├── lib/      # Утилиты, API-клиент
│       │   └── main.tsx
│       ├── public/
│       ├── tests/
│       ├── package.json
│       ├── tsconfig.json
│       └── vite.config.ts
│
├── packages/
│   └── shared/           # Общие типы, константы (опционально)
│
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.agent
│   ├── Dockerfile.web
│   ├── docker-compose.yml        # Production
│   └── docker-compose.dev.yml    # Development (hot-reload)
│
├── configs/
│   ├── livekit.yaml      # Конфигурация LiveKit Server
│   ├── litellm.yaml      # Конфигурация LiteLLM Proxy
│   ├── caddy/Caddyfile   # Конфигурация Caddy
│   └── coturn/turnserver.conf
│
├── scripts/
│   ├── seed.py           # Начальные данные (промпты, конфигурация агента)
│   ├── ingest.py         # Загрузка материалов в RAG
│   └── migrate.sh        # Обёртка для запуска миграций
│
├── docs/
│   ├── about.md          # Описание продукта
│   ├── architecture.md   # Архитектура системы
│   ├── specs.md          # Технические спецификации (этот файл)
│   └── plans/            # Дизайн-документы
│
├── .env.example          # Шаблон переменных окружения
├── pyproject.toml        # Корневой Python workspace (uv)
├── package.json          # Корневой Node workspace
└── README.md
```

### Принципы организации

- **apps/** — самостоятельные приложения, каждое собирается в отдельный Docker-образ
- **packages/** — разделяемый код (используется, если появятся общие типы между api и agent)
- **configs/** — конфигурационные файлы для инфраструктурных контейнеров (монтируются как volumes)
- **scripts/** — утилиты, не входящие в runtime приложений
- **Python workspace** через uv — `apps/api` и `apps/agent` управляются из корневого `pyproject.toml`
- **Bun workspace** — `apps/web` управляется из корневого `package.json`

---

## 3. Runtime и тулчейн

| Инструмент | Минимальная версия | Назначение |
|---|---|---|
| Python | 3.13.12+ | Runtime для API и Agent |
| uv | 0.10.7+ | Менеджер пакетов и виртуальных окружений Python |
| Bun | 1.3+ | Runtime, менеджер пакетов, тест-раннер для frontend |
| PostgreSQL | 18.2+ | Основная БД + pgvector |
| Docker Engine | 27+ | Контейнеризация |
| Docker Compose | 2.30+ | Оркестрация контейнеров |

### Почему uv, а не pip/poetry

- Установка и резолв зависимостей на порядок быстрее
- Единый инструмент: создание venv, установка пакетов, запуск скриптов, workspace-управление
- Поддержка lockfile (`uv.lock`) для воспроизводимых сборок
- Совместим с pyproject.toml (PEP 621)

### Почему Python 3.13, а не 3.14

Python 3.14 — актуальный релиз, но некоторые C-расширения (asyncpg, pgvector, Silero) могут не иметь предсобранных wheels для 3.14. Python 3.13 — стабильная версия с полной поддержкой всех зависимостей проекта.

---

## 4. Backend — Python-зависимости

### apps/api (FastAPI REST API)

| Пакет | Минимальная версия | Назначение |
|---|---|---|
| fastapi | 0.135.1+ | HTTP-фреймворк |
| uvicorn | 0.41.0+ | ASGI-сервер |
| pydantic | 2.12.5+ | Валидация данных, схемы |
| sqlalchemy | 2.0.48+ | ORM (async mode) |
| alembic | 1.18.4+ | Миграции БД |
| asyncpg | 0.31.0+ | Async-драйвер PostgreSQL |
| pgvector | 0.4.2+ | Интеграция pgvector с SQLAlchemy |
| python-jose | 3.4+ | JWT-токены (access/refresh) |
| passlib[bcrypt] | 1.7.4+ | Хеширование паролей |
| resend | 2.7+ | Отправка email (подтверждение регистрации) |
| python-multipart | 0.0.20+ | Обработка form-data (FastAPI) |
| httpx | 0.28+ | HTTP-клиент (для тестов и внешних запросов) |

### apps/agent (LiveKit Agent)

| Пакет | Минимальная версия | Назначение |
|---|---|---|
| livekit-agents | 1.4.4+ | Фреймворк голосового агента |
| livekit-plugins-deepgram | 1.4.2+ | STT-плагин Deepgram |
| livekit-plugins-silero | 1.3.12+ | VAD (Voice Activity Detection) |
| livekit-plugins-openai | 1.4.2+ | OpenAI-совместимый LLM-плагин (для LiteLLM) |
| litellm | 1.82.0+ | LLM Proxy SDK (для прямых вызовов, если нужно) |
| sqlalchemy | 2.0.48+ | ORM (доступ к БД из агента) |
| asyncpg | 0.31.0+ | Async-драйвер PostgreSQL |
| pgvector | 0.4.2+ | Работа с векторами |
| pydantic | 2.12.5+ | Валидация данных |

### Общие Python-зависимости (workspace-уровень)

| Пакет | Минимальная версия | Назначение |
|---|---|---|
| ruff | 0.11+ | Линтинг + форматирование |
| pytest | 8.3+ | Тестирование |
| pytest-asyncio | 0.26+ | Async-тесты |

---

## 5. Frontend — Node-зависимости

### apps/web (React PWA)

| Пакет | Минимальная версия | Назначение |
|---|---|---|
| react | 19.2.4+ | UI-фреймворк |
| react-dom | 19.2.4+ | React DOM-рендерер |
| typescript | 5.8+ | Типизация |
| vite | 7.3.1+ | Билд-тул и dev-сервер |
| livekit-client | 2.17.2+ | LiveKit Client SDK |
| @livekit/components-react | 2.9.20+ | React-компоненты LiveKit |
| @tanstack/react-query | 5.75+ | Data fetching для REST API |
| react-router | 7.5+ | Маршрутизация |

### LiveKit Agents UI

Компоненты Agents UI устанавливаются через shadcn CLI и копируются в исходный код проекта (не являются зависимостью):

```bash
bunx shadcn@latest registry add @agents-ui
bunx shadcn@latest add @agents-ui/agent-control-bar
bunx shadcn@latest add @agents-ui/agent-chat-transcript
bunx shadcn@latest add @agents-ui/agent-audio-visualizer-bar
```

Основные компоненты:
- `AgentControlBar` — управление микрофоном, отключение
- `AgentChatTranscript` — лента текстового чата с транскриптами
- `AgentAudioVisualizerBar` / `Wave` / `Aura` — визуализация аудио
- `AgentChatIndicator` — индикатор состояния агента

### Dev-зависимости frontend

| Пакет | Минимальная версия | Назначение |
|---|---|---|
| vitest | 3.2+ | Тестирование |
| @testing-library/react | 16.3+ | Тестирование React-компонентов |
| eslint | 9.22+ | Линтинг (flat config) |
| prettier | 3.5+ | Форматирование |
| @vitejs/plugin-react | 4.4+ | React plugin для Vite |

---

## 6. Аутентификация (MVP)

### Подход

Для MVP — **email + password** с подтверждением почты. Без OAuth, без SSO, без сторонних провайдеров.

### Процесс регистрации

1. Пользователь вводит email + password
2. API создаёт запись в БД с `is_verified = false`
3. API отправляет email с 6-значным кодом подтверждения через Resend
4. Пользователь вводит код в приложении
5. API верифицирует код, устанавливает `is_verified = true`
6. Пользователь получает JWT-токены

### JWT-токены

- **Access token** — короткоживущий (15 минут), передаётся в заголовке `Authorization: Bearer <token>`
- **Refresh token** — долгоживущий (30 дней), используется для обновления access token
- Алгоритм: HS256 с секретом из переменной окружения

### LiveKit-токен

После валидации JWT клиент запрашивает у API LiveKit-токен для подключения к комнате. API генерирует токен через `livekit-api` Python SDK с правами, определёнными для данного пользователя.

### Хеширование паролей

bcrypt через passlib. Минимальная длина пароля — 8 символов.

### Resend

Сервис для отправки транзакционных email. Используется только для подтверждения регистрации (MVP). API-ключ передаётся через переменную окружения `RESEND_API_KEY`.

---

## 7. База данных и миграции

### SQLAlchemy 2.0

- **Async mode** через asyncpg
- **Mapped columns** (Mapped[type] вместо Column(Type))
- **Type annotations** во всех моделях
- Сессии через async context manager

```python
# Стиль объявления моделей
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

### Соглашения по именованию

- Таблицы: **snake_case, множественное число** (`users`, `sessions`, `messages`, `knowledge_chunks`)
- Колонки: **snake_case** (`created_at`, `source_type`, `embedding_vector`)
- Индексы: `ix_{table}_{column}` (автоматически через SQLAlchemy naming convention)
- Foreign keys: `fk_{table}_{column}_{ref_table}`
- Constraints: `ck_{table}_{description}`

### Alembic

- Миграции хранятся в `apps/api/migrations/`
- Автогенерация миграций: `alembic revision --autogenerate -m "description"`
- Все миграции — **forward-only** для MVP (downgrade не обязателен)
- Миграции запускаются перед стартом api-контейнера

### pgvector

- Расширение включается миграцией: `CREATE EXTENSION IF NOT EXISTS vector`
- Колонки с эмбеддингами: тип `Vector(dim)` через SQLAlchemy-интеграцию pgvector
- HNSW-индексы для ANN-поиска
- Размерность эмбеддингов определяется выбранной embedding-моделью (фиксируется при загрузке первых материалов)

---

## 8. Линтинг и кодстайл

### Python — Ruff

Ruff используется и для линтинга, и для форматирования (замена flake8, black, isort).

```toml
# pyproject.toml (корневой)
[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "ASYNC",# flake8-async
    "S",    # flake8-bandit (security)
    "T20",  # flake8-print
    "RUF",  # ruff-specific
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]  # assert допустим в тестах

[tool.ruff.format]
quote-style = "double"
```

### Frontend — ESLint + Prettier

ESLint 9+ с flat config. Prettier для форматирования.

```js
// eslint.config.js (шаблон)
import eslint from "@eslint/js";
import tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import hooksPlugin from "eslint-plugin-react-hooks";

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  {
    plugins: { react: reactPlugin, "react-hooks": hooksPlugin },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    },
  }
);
```

### TypeScript — строгий режим

```json
// tsconfig.json (ключевые опции)
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "exactOptionalPropertyTypes": true,
    "moduleResolution": "bundler",
    "target": "ES2024",
    "lib": ["ES2024", "DOM", "DOM.Iterable"]
  }
}
```

### Pre-commit hooks

Проверки перед коммитом (через `lefthook`):
- `ruff check` + `ruff format --check` для Python
- `bunx eslint .` + `bunx prettier --check .` для TypeScript
- `bunx tsc --noEmit` для проверки типов

---

## 9. Тестирование (MVP)

### Backend — pytest

| Инструмент | Назначение |
|---|---|
| pytest | Тестовый фреймворк |
| pytest-asyncio | Async-тесты |
| httpx | Async HTTP-клиент для тестов FastAPI |

Что тестируется на MVP:
- **API-эндпоинты** — каждый эндпоинт покрыт минимум одним happy-path тестом
- **Аутентификация** — регистрация, логин, refresh, верификация email
- **Критические сервисы** — генерация LiveKit-токенов, получение источников

Что НЕ тестируется на MVP:
- LiveKit Agent (voice pipeline) — тестируется вручную через Agents Playground
- Интеграция с внешними API (Deepgram, Inworld, LLM-провайдеры)
- e2e-сценарии

```python
# Структура тестов
apps/api/tests/
├── conftest.py          # Фикстуры (test client, test DB)
├── test_auth.py         # Регистрация, логин, JWT
├── test_sessions.py     # История сессий
└── test_sources.py      # Метаданные RAG-источников
```

### Frontend — Vitest

| Инструмент | Назначение |
|---|---|
| vitest | Тестовый фреймворк (интеграция с Vite) |
| @testing-library/react | Тестирование React-компонентов |

Что тестируется на MVP:
- **Утилиты** — форматирование, парсинг, хелперы
- **Ключевые компоненты** — рендеринг, пользовательские события

---

## 10. Docker-разработка

### Production (docker-compose.yml)

Полный стек из 7 контейнеров (описан в `docs/architecture.md`, раздел 1). Образы собираются multi-stage, минимальный размер.

### Development (docker-compose.dev.yml)

Отличия от production:
- **apps/api** — volume-маунт исходников, uvicorn с `--reload`
- **apps/agent** — volume-маунт исходников, LiveKit Agent в режиме `dev` (auto-reload)
- **apps/web** — volume-маунт исходников, Vite dev server с HMR
- **postgres** — тот же образ, но с dev-данными (seed)
- **livekit/coturn/litellm/caddy** — идентичны production

```yaml
# docker-compose.dev.yml (схематично)
services:
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
      target: dev
    volumes:
      - ./apps/api/src:/app/src
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - DEBUG=true

  agent:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent
      target: dev
    volumes:
      - ./apps/agent/src:/app/src
    command: python -m livekit.agents dev src/main.py

  web:
    build:
      context: .
      dockerfile: docker/Dockerfile.web
      target: dev
    volumes:
      - ./apps/web/src:/app/src
    ports:
      - "5173:5173"
    command: bunx vite --host
```

### Запуск

```bash
# Development
docker compose -f docker/docker-compose.dev.yml up

# Production
docker compose -f docker/docker-compose.yml up -d

# Миграции
docker compose exec api alembic upgrade head

# Загрузка начальных данных
docker compose exec api python scripts/seed.py
```

---

## 11. Переменные окружения

Все секреты хранятся в `.env` файле (не коммитится). Шаблон — `.env.example`.

### API-контейнер

| Переменная | Описание |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET` | Секрет для подписи JWT-токенов |
| `RESEND_API_KEY` | API-ключ Resend для email |
| `LIVEKIT_API_KEY` | LiveKit API key (для генерации токенов) |
| `LIVEKIT_API_SECRET` | LiveKit API secret |
| `LIVEKIT_URL` | URL LiveKit Server (внутренний) |

### Agent-контейнер

| Переменная | Описание |
|---|---|
| `LIVEKIT_API_KEY` | LiveKit API key |
| `LIVEKIT_API_SECRET` | LiveKit API secret |
| `LIVEKIT_URL` | URL LiveKit Server (внутренний) |
| `LITELLM_URL` | URL LiteLLM Proxy (внутренний) |
| `DATABASE_URL` | PostgreSQL connection string |
| `DEEPGRAM_API_KEY` | API-ключ Deepgram (STT) |
| `INWORLD_API_KEY` | API-ключ Inworld (TTS) |
| `ELEVENLABS_API_KEY` | API-ключ ElevenLabs (fallback TTS) |

### LiteLLM-контейнер

| Переменная | Описание |
|---|---|
| `GOOGLE_API_KEY` | API-ключ Google (Gemini) |
| `OPENAI_API_KEY` | API-ключ OpenAI (fallback LLM) |

### LiveKit-контейнер

Конфигурация через `configs/livekit.yaml` (API key/secret задаются в YAML).

### coturn-контейнер

| Переменная | Описание |
|---|---|
| `TURN_USERNAME` | Имя пользователя TURN |
| `TURN_PASSWORD` | Пароль TURN |

---

## 12. Git-конвенции

### Ветвление

- `main` — стабильная ветка, деплоится на production
- `dev` — интеграционная ветка для разработки
- Feature-ветки: `feat/short-description`
- Bugfix-ветки: `fix/short-description`

### Коммиты

Формат [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

feat(api): add user registration endpoint
fix(agent): handle STT timeout gracefully
chore(docker): update PostgreSQL to 18.3
docs(specs): add testing conventions
```

Типы: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `perf`.
Scope: `api`, `agent`, `web`, `docker`, `docs`, `ci`.
