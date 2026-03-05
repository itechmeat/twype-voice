## Context

Голосовой пайплайн Twype Agent собран из отдельных компонентов (Silero VAD, Deepgram STT, LiteLLM/Gemini LLM, Inworld TTS), но `AgentSession` использует базовую конфигурацию `turn_detection="vad"` без тонкой настройки endpointing, шумоподавления и заполнения пауз. LiveKit Agents SDK v1.4.4 предоставляет встроенные параметры для всего необходимого — дополнительные плагины turn detection не требуются.

Текущее состояние `build_session()` в `agent.py`:
- `turn_detection="vad"` — используется только VAD без STT endpointing
- Все endpointing/interruption параметры — значения по умолчанию SDK
- Нет noise cancellation
- Нет thinking sounds при задержке LLM

## Goals / Non-Goals

**Goals:**
- Переключить turn detection на `"stt"` — Deepgram сам определяет конец фразы по контексту, а не только по паузе
- Настроить endpointing delay: `min_endpointing_delay=0.5`, `max_endpointing_delay=3.0` (safety timeout)
- Включить `preemptive_generation=True` — LLM начинает генерацию до подтверждения конца хода, снижая задержку
- Добавить noise cancellation через `livekit-plugins-noise-cancellation`
- Реализовать thinking sounds через override `Agent.llm_node` — воспроизведение короткого filler-аудио при задержке LLM
- Настроить обработку ложных прерываний: `false_interruption_timeout=2.0`, `resume_false_interruption=True`
- Вынести все настраиваемые параметры в `AgentSettings`

**Non-Goals:**
- Кастомный `_TurnDetector` (достаточно встроенного `"stt"` mode)
- Смена STT/LLM/TTS провайдеров
- Полная обработка прерываний (S20 — отдельная история)
- Prompt system из БД (S10)

## Decisions

### D1: Turn detection mode — `"stt"` вместо `"vad"`

**Выбор:** `turn_detection="stt"`

**Альтернативы:**
- `"vad"` (текущее) — определяет конец хода только по тишине, не учитывая контекст фразы. Даёт ложные срабатывания на паузах внутри предложения.
- Кастомный `_TurnDetector` — требует реализации `predict_end_of_turn()` с LLM-вызовом, добавляет задержку и сложность. Избыточно на текущем этапе.
- `"stt"` — Deepgram Nova-3 использует языковую модель для определения конца высказывания. Более точный endpointing без дополнительной задержки. Параметры `min_endpointing_delay` и `max_endpointing_delay` дополняют STT endpointing.

**Обоснование:** STT mode даёт контекстное определение конца фразы "бесплатно" — Deepgram уже анализирует речь. В сочетании с `min_endpointing_delay=0.5` это обеспечивает баланс между скоростью отклика и точностью.

### D2: Preemptive generation для снижения задержки

**Выбор:** `preemptive_generation=True`

**Альтернативы:**
- `False` (текущее) — LLM начинает генерацию только после подтверждения конца хода. Безопаснее, но добавляет задержку равную endpointing delay.
- `True` — LLM начинает генерацию при получении транскрипта, не дожидаясь end-of-turn. Может потратить compute при прерывании, но значительно снижает voice-to-voice latency.

**Обоснование:** Целевая задержка ~800 мс требует overlap между STT endpointing и LLM inference. Дополнительный compute при false start — приемлемый trade-off.

### D3: Noise cancellation — `livekit-plugins-noise-cancellation`

**Выбор:** Пакет `livekit-plugins-noise-cancellation` (v0.2.5), BVC (Background Voice Cancellation) от LiveKit.

**Альтернативы:**
- Без шумоподавления (текущее) — фоновый шум ухудшает качество STT, особенно в мобильных сценариях.
- Krisp — коммерческий SDK, требует отдельную лицензию, нет публичного LiveKit-плагина для Python.
- `livekit-plugins-noise-cancellation` — открытый плагин LiveKit, работает как `AudioStream` фильтр перед пайплайном. Не требует дополнительных лицензий.

**Обоснование:** Единственный доступный открытый плагин шумоподавления в экосистеме LiveKit Agents для Python.

### D4: Thinking sounds через override `Agent.llm_node`

**Выбор:** Override `llm_node` в `TwypeAgent` — при задержке LLM ответа > N мс, генерировать короткий filler через TTS ("Хм...", "Дайте подумать...") параллельно с ожиданием LLM.

**Альтернативы:**
- Статический WAV-файл — не зависит от TTS, но не адаптируется по языку и звучит неестественно.
- Отдельный background task с таймером — сложнее синхронизировать с пайплайном, риск overlap с началом реального ответа.
- Override `llm_node` — точка вставки прямо в пайплайне. Можно yield filler text перед LLM stream, а `tts_node` озвучит его естественным образом. Язык определяется из последнего `last_language`.

**Обоснование:** `llm_node` — штатная точка расширения SDK. Filler генерируется как текст и проходит через обычный TTS pipeline, что обеспечивает естественное звучание и языковую адаптацию.

### D5: Конфигурация через `AgentSettings`

Новые параметры:
- `TURN_DETECTION_MODE` (default: `"stt"`) — режим turn detection
- `MIN_ENDPOINTING_DELAY` (default: `0.5`) — минимальная пауза для end-of-turn
- `MAX_ENDPOINTING_DELAY` (default: `3.0`) — safety timeout
- `PREEMPTIVE_GENERATION` (default: `True`) — упреждающая генерация LLM
- `NOISE_CANCELLATION_ENABLED` (default: `True`) — шумоподавление
- `THINKING_SOUNDS_ENABLED` (default: `True`) — filler при задержке LLM
- `THINKING_SOUNDS_DELAY` (default: `1.5`) — порог задержки LLM в секундах для filler
- `FALSE_INTERRUPTION_TIMEOUT` (default: `2.0`) — таймаут ложного прерывания
- `MIN_INTERRUPTION_DURATION` (default: `0.5`) — минимальная длительность речи для прерывания

## Risks / Trade-offs

- **[Preemptive generation waste]** → При `preemptive_generation=True` LLM может начать генерацию, которая будет отброшена. Mitigation: приемлемый compute cost для Gemini Flash-Lite; можно отключить через env.
- **[Noise cancellation quality]** → `livekit-plugins-noise-cancellation` v0.2.5 — относительно новый пакет, качество может быть нестабильным. Mitigation: `NOISE_CANCELLATION_ENABLED=True/False` для быстрого отключения.
- **[Thinking sounds timing]** → Filler может начаться слишком рано или наложиться на реальный ответ. Mitigation: `THINKING_SOUNDS_DELAY` задаёт минимальную задержку; filler yield прекращается при поступлении первого LLM chunk.
- **[STT endpointing language]** → Качество STT endpointing в Deepgram может отличаться для русского и английского. Mitigation: `min_endpointing_delay` как fallback safety net.
