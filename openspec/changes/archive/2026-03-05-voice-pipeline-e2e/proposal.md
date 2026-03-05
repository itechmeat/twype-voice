## Why

Все компоненты голосового пайплайна (VAD, STT, LLM, TTS) реализованы и работают по отдельности, но пайплайн собран без Turn Detector, шумоподавления и оптимизации задержки. Текущий `turn_detection="vad"` даёт ложные срабатывания и не учитывает контекст фразы. Нет thinking sounds для заполнения пауз обработки. Целевая задержка voice-to-voice ~800 мс не достигнута.

## What Changes

- Добавить Turn Detector (end-of-utterance detection) поверх VAD: пороги пауз, safety timeout 3 сек, контекстная оценка конца фразы
- Включить шумоподавление входного аудио (noise suppression) перед VAD
- Оптимизировать сквозной стриминг между всеми компонентами пайплайна для достижения целевой задержки ~800 мс
- Добавить thinking sounds / TTS fillers — короткие звуковые сигналы или голосовые заполнители при затянувшейся обработке LLM
- Настроить `AgentSession` с полным пайплайном: VAD → Turn Detector → STT → LLM → TTS → WebRTC audio
- Добавить конфигурационные параметры Turn Detector и noise suppression в `AgentSettings`

## Capabilities

### New Capabilities
- `voice-pipeline-turn-detection`: Turn Detector — определение конца высказывания пользователя с порогами пауз и safety timeout. Шумоподавление входного аудио.
- `voice-pipeline-thinking-sounds`: Thinking sounds и TTS fillers — заполнение тишины при задержке LLM-ответа звуковыми/голосовыми маркерами.

### Modified Capabilities
- `agent-entrypoint`: AgentSession собирается с Turn Detector и noise suppression; добавляются настройки в prewarm и entrypoint.

## Impact

- **Код:** `apps/agent/src/agent.py` (сборка пайплайна), `apps/agent/src/main.py` (entrypoint, prewarm), `apps/agent/src/settings.py` (новые параметры)
- **Зависимости:** возможно `livekit-plugins-turn-detector` или аналог в `apps/agent/pyproject.toml`; Krisp или встроенное шумоподавление
- **Конфигурация:** новые env-переменные в `.env.example` для Turn Detector и noise suppression
- **Производительность:** целевая задержка voice-to-voice ~800 мс; thinking sounds маскируют задержку для пользователя
