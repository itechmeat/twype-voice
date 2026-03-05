## Why

Авторизация готова (S03), но пользователь пока не может начать голосовую сессию — нет эндпоинтов для создания сессии, генерации LiveKit-токена и просмотра истории. Без этого клиент не может подключиться к LiveKit-комнате, а агент не получит участника.

## What Changes

- Новый роутер `sessions` с тремя эндпоинтами:
  - `POST /sessions/start` — создаёт запись `Session` в БД, генерирует уникальное `room_name`, возвращает LiveKit access token с правами `can_publish`, `can_subscribe`, `can_publish_data`
  - `GET /sessions/history` — список сессий текущего пользователя (пагинация offset/limit, сортировка по `started_at` desc)
  - `GET /sessions/{id}/messages` — сообщения конкретной сессии (только если сессия принадлежит пользователю)
- LiveKit-токен генерируется через `livekit-api` Python SDK с настраиваемыми правами
- Все эндпоинты защищены JWT (используют существующий `get_current_user`)
- Pydantic-схемы для request/response
- Тесты для всех эндпоинтов

## Capabilities

### New Capabilities
- `session-endpoints`: REST API эндпоинты для управления сессиями (start, history, messages)
- `livekit-token`: Генерация LiveKit access token с правами участника

### Modified Capabilities

## Impact

- **Код:** новые файлы в `apps/api/src/` — роутер, сервис, схемы, тесты
- **Зависимости:** добавляется `livekit-api` в `apps/api/pyproject.toml`
- **API:** три новых эндпоинта, подключаемые к `main.py`
- **Модели:** используются существующие `Session` и `Message` без изменений
- **Конфигурация:** нужны `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_URL` в `.env`
