## ADDED Requirements

### Requirement: Monorepo directory structure
Проект SHALL иметь структуру каталогов согласно `docs/specs.md` раздел 2: `apps/api/`, `apps/agent/`, `apps/web/`, `packages/shared/`, `docker/`, `configs/`, `scripts/`, `docs/`.

#### Scenario: Все ключевые директории существуют
- **WHEN** проект клонирован
- **THEN** существуют директории `apps/api/src/`, `apps/agent/src/`, `apps/web/src/`, `docker/`, `configs/`, `scripts/`

### Requirement: Python workspace через uv
Корневой `pyproject.toml` SHALL определять uv workspace с members `apps/api` и `apps/agent`. Каждый member SHALL иметь собственный `pyproject.toml` с зависимостями. Корневой файл SHALL содержать общие dev-зависимости (ruff, pytest, pytest-asyncio) и конфигурацию Ruff.

#### Scenario: uv sync устанавливает зависимости всех members
- **WHEN** выполняется `uv sync` из корня проекта
- **THEN** зависимости `apps/api` и `apps/agent` установлены, создан единый `uv.lock`

#### Scenario: Ruff конфигурация соответствует specs.md
- **WHEN** выполняется `uv run ruff check .`
- **THEN** используется `target-version = "py313"`, `line-length = 100`, набор правил из `docs/specs.md` раздел 8

### Requirement: Node workspace через bun
Корневой `package.json` SHALL определять bun workspace с member `apps/web`. `apps/web/package.json` SHALL содержать зависимости React 19+, Vite 7+, TypeScript 5.8+, LiveKit Client SDK.

#### Scenario: bun install устанавливает зависимости web
- **WHEN** выполняется `bun install` из корня проекта
- **THEN** зависимости `apps/web` установлены, создан `bun.lock`

### Requirement: FastAPI stub application
`apps/api/` SHALL содержать минимальное FastAPI-приложение с единственным эндпоинтом `GET /health`.

#### Scenario: Health endpoint возвращает OK
- **WHEN** отправлен HTTP GET запрос на `/health`
- **THEN** ответ имеет статус 200 и тело `{"status": "ok"}`

#### Scenario: Приложение запускается через uvicorn
- **WHEN** выполняется `uvicorn src.main:app --host 0.0.0.0 --port 8000`
- **THEN** сервер стартует без ошибок и принимает HTTP-запросы

### Requirement: LiveKit Agent stub application
`apps/agent/` SHALL содержать минимальный LiveKit Agent с `WorkerOptions`, который подключается к LiveKit Server, но не содержит voice pipeline.

#### Scenario: Agent стартует и регистрируется в LiveKit
- **WHEN** агент запущен с переменными `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- **THEN** агент подключается к LiveKit Server и готов принимать job dispatch

#### Scenario: Agent без pipeline логирует запуск
- **WHEN** агент получает dispatch на новую комнату
- **THEN** агент логирует событие, но не создаёт voice pipeline (заглушка)

### Requirement: React PWA stub application
`apps/web/` SHALL содержать Vite + React scaffold с TypeScript в strict mode, ESLint 9 flat config и Prettier.

#### Scenario: Dev server стартует
- **WHEN** выполняется `bun run dev` в `apps/web/`
- **THEN** Vite dev server запускается и отдаёт HTML-страницу

#### Scenario: TypeScript strict mode
- **WHEN** выполняется `bunx tsc --noEmit` в `apps/web/`
- **THEN** проверка типов проходит без ошибок

#### Scenario: Линтинг проходит
- **WHEN** выполняется `bunx eslint .` и `bunx prettier --check .` в `apps/web/`
- **THEN** линтинг и форматирование проходят без ошибок

### Requirement: Environment variables template
Корень проекта SHALL содержать `.env.example` со всеми переменными окружения, определёнными в `docs/specs.md` раздел 11, с плейсхолдерами вместо реальных значений.

#### Scenario: Все переменные документированы
- **WHEN** разработчик копирует `.env.example` в `.env`
- **THEN** файл содержит все переменные для API, Agent, LiteLLM, coturn с комментариями-описаниями

### Requirement: Makefile с основными командами
Корень проекта SHALL содержать `Makefile` с self-documenting help и make-таргетами для всех основных операций разработки. `make` без аргументов SHALL выводить список доступных команд с описаниями.

#### Scenario: Help выводит список команд
- **WHEN** выполняется `make` или `make help` из корня проекта
- **THEN** выводится отформатированный список всех доступных таргетов с описаниями

#### Scenario: Dev-среда запускается через make
- **WHEN** выполняется `make dev`
- **THEN** запускается `docker compose -f docker/docker-compose.dev.yml up` со всеми 7 контейнерами

#### Scenario: Production-среда запускается через make
- **WHEN** выполняется `make up`
- **THEN** запускается `docker compose -f docker/docker-compose.yml up -d`

#### Scenario: Остановка контейнеров через make
- **WHEN** выполняется `make down`
- **THEN** останавливаются и удаляются все контейнеры текущей конфигурации

#### Scenario: Установка зависимостей через make
- **WHEN** выполняется `make install`
- **THEN** выполняются `uv sync` и `bun install` для установки зависимостей всех workspace members

#### Scenario: Линтинг через make
- **WHEN** выполняется `make lint`
- **THEN** запускаются `uv run ruff check .` для Python и `bunx eslint .` для TypeScript

#### Scenario: Форматирование через make
- **WHEN** выполняется `make format`
- **THEN** запускаются `uv run ruff format .` для Python и `bunx prettier --write .` для TypeScript

#### Scenario: Тесты через make
- **WHEN** выполняется `make test`
- **THEN** запускаются `uv run pytest` для Python и `bunx vitest run` для TypeScript

#### Scenario: Логи через make
- **WHEN** выполняется `make logs`
- **THEN** выводятся логи всех контейнеров в follow-режиме

#### Scenario: Очистка через make
- **WHEN** выполняется `make clean`
- **THEN** удаляются build-артефакты, кэши, __pycache__, .pytest_cache

### Requirement: Gitignore
Корень проекта SHALL содержать `.gitignore`, исключающий: `.env`, `node_modules/`, `__pycache__/`, `.venv/`, `dist/`, `.ruff_cache/`, Docker volumes.

#### Scenario: Секреты не попадают в коммит
- **WHEN** существует файл `.env` с секретами
- **THEN** `git status` не показывает `.env` в untracked files
