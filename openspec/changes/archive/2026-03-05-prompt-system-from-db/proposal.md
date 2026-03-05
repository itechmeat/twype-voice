## Why

Все промпты агента сейчас захардкожены в `apps/agent/src/prompts.py` (единственная строка `SYSTEM_PROMPT`). Это блокирует итерацию: чтобы изменить поведение агента — нужен редеплой. При этом в БД уже есть модель `AgentConfig` с 8 слоями промптов (seed-скрипт), а модель `Session` содержит поле `agent_config_snapshot` (JSONB) для заморозки конфигурации. Пора связать эти компоненты: загружать промпты из БД, собирать финальный контекст через Prompt Builder и фиксировать снимок конфигурации при старте сессии.

## What Changes

- Новый модуль Prompt Builder в агенте: загрузка всех активных промптов из `agent_config` при инициализации, сборка многослойного LLM-контекста из отдельных слоёв (system, voice mode, dual-layer, emotion, crisis, RAG context, language, proactive).
- Config snapshot: при старте сессии агент считывает текущие активные промпты и записывает их в `sessions.agent_config_snapshot`. Все последующие обращения к промптам в рамках сессии используют снимок, а не live-данные.
- Замена захардкоженного `SYSTEM_PROMPT` на динамическую сборку из БД.
- Расширение seed-скрипта: содержательные промпты вместо placeholder-ов для всех 8 слоёв.

## Capabilities

### New Capabilities
- `prompt-builder`: загрузка prompt layers из БД, сборка финального LLM-контекста из многослойной конфигурации, валидация наличия обязательных слоёв
- `config-snapshot`: заморозка agent config при старте сессии, сохранение в `sessions.agent_config_snapshot`, использование снимка на протяжении всей сессии

### Modified Capabilities
- `database-seed`: расширение seed-данных — содержательные промпты для всех 8 слоёв вместо placeholder-ов

## Impact

- **Agent (`apps/agent/`):** новый модуль Prompt Builder, изменение `prompts.py` и `agent.py` (инъекция instructions из БД вместо константы), добавление запросов к БД при старте сессии
- **Seed (`scripts/seed.py`):** обновление текстов промптов
- **Модели БД:** без изменений — `AgentConfig` и `sessions.agent_config_snapshot` уже существуют
- **Зависимости:** без новых зависимостей — используется существующий async SQLAlchemy из агента
