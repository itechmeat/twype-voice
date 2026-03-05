## Context

Агент использует захардкоженный `SYSTEM_PROMPT` в `apps/agent/src/prompts.py`. В БД уже существуют:
- Модель `AgentConfig` (key/value, version, is_active) с 8 prompt layers в seed-скрипте (placeholder-ы)
- Поле `sessions.agent_config_snapshot` (JSONB, nullable) — готово для заморозки конфига
- Async DB-подключение в агенте через `db.py` (`build_engine`, `build_sessionmaker`)
- `db_sessionmaker` передаётся через `proc.userdata` в prewarm

`TwypeAgent` принимает `instructions` (строку) в конструкторе через `super().__init__(instructions=SYSTEM_PROMPT)`. LiveKit Agents SDK использует это поле как system prompt для LLM.

## Goals / Non-Goals

**Goals:**
- Загрузка всех активных prompt layers из `agent_config` при старте сессии
- Сборка многослойного system prompt из отдельных слоёв в определённом порядке
- Заморозка конфигурации в `sessions.agent_config_snapshot` при старте сессии
- Использование снимка (а не live-данных) на протяжении всей сессии
- Содержательные промпты в seed-скрипте вместо placeholder-ов

**Non-Goals:**
- Админ-интерфейс для редактирования промптов (будущая история)
- Горячая перезагрузка промптов в ходе сессии
- Версионирование с diff-ами между версиями промптов
- RAG-контекст в промптах (S14 подставляет фрагменты динамически)

## Decisions

### 1. Prompt Builder как функция, не класс

Prompt Builder — это набор async-функций в `apps/agent/src/prompts.py`, а не отдельный класс. Причины:
- У Builder нет состояния между вызовами — он один раз загружает, один раз собирает
- Функциональный подход проще и прямолинейнее
- Основные функции: `load_prompt_layers(db_sessionmaker) -> dict[str, str]`, `build_instructions(layers: dict[str, str]) -> str`

Альтернатива: класс `PromptBuilder` с методами `load()` и `build()`. Отклонено — избыточная абстракция для stateless-операции.

### 2. Фиксированный порядок слоёв

Слои собираются в instructions в фиксированном порядке, определённом константой:

```python
PROMPT_LAYER_ORDER = [
    "system_prompt",
    "voice_prompt",
    "language_prompt",
    "dual_layer_prompt",
    "emotion_prompt",
    "crisis_prompt",
    "rag_prompt",
    "proactive_prompt",
]
```

`system_prompt` — базовый контекст, остальные дополняют его. `crisis_prompt` ближе к концу, чтобы быть более заметным для LLM (recency bias). `rag_prompt` — инструкция о работе с источниками (сами фрагменты подставляются позже в S14).

Альтернатива: приоритет/порядок в БД (дополнительная колонка). Отклонено — YAGNI для 8 слоёв, порядок меняется крайне редко.

### 3. Snapshot при старте сессии в entrypoint

Загрузка промптов и запись снимка происходят в `entrypoint()` (main.py) после `resolve_session_id()`. Снимок записывается в `sessions.agent_config_snapshot` через прямой SQL UPDATE. Собранные instructions передаются в `TwypeAgent(instructions=...)`.

Альтернатива: загрузка в prewarm. Отклонено — prewarm выполняется один раз на процесс, а нам нужны свежие промпты для каждой сессии.

### 4. Graceful degradation при ошибке загрузки

Если БД недоступна или промпты не найдены — агент использует fallback system prompt (текущий захардкоженный). Сессия продолжает работать, но без snapshot. Ошибка логируется на уровне ERROR.

### 5. Модели `agent_config` доступны агенту напрямую

Агент уже использует SQLAlchemy для сохранения транскриптов. Для чтения `agent_config` и обновления `sessions` агент выполняет прямые SQL-запросы через `db_sessionmaker` (без импорта моделей из `apps/api`). Это сохраняет независимость двух приложений.

## Risks / Trade-offs

- **[Latency] Запрос к БД при старте каждой сессии** → Один SELECT на 8 строк + один UPDATE — пренебрежимо мало (~5ms). Кэширование не нужно на уровне MVP.
- **[Coupling] Агент зависит от схемы `agent_config` и `sessions`** → Схема стабильна, миграции прямые. Агент использует raw SQL, не импортирует модели API.
- **[Seed drift] Промпты в seed могут устареть** → Seed — только начальные данные для dev. Production промпты редактируются через БД напрямую.
