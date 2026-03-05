## 1. Зависимости и конфигурация

- [x] 1.1 Добавить `livekit-api>=1.0.0` в `apps/api/pyproject.toml` и выполнить `uv sync`
- [x] 1.2 Добавить `LIVEKIT_API_KEY` и `LIVEKIT_API_SECRET` в Pydantic Settings (или config-модуль), с валидацией при старте

## 2. LiveKit-токен

- [x] 2.1 Создать `apps/api/src/sessions/livekit.py` с функцией `create_livekit_token(identity, room_name, api_key, api_secret) -> str` — генерация токена через `livekit-api` SDK с грантами `room_join`, `can_publish`, `can_subscribe`, `can_publish_data`, TTL 6 часов
- [x] 2.2 Написать unit-тест для `create_livekit_token` — проверка что возвращается JWT-строка, identity и room корректны

## 3. Pydantic-схемы

- [x] 3.1 Создать `apps/api/src/schemas/sessions.py` — схемы `SessionStartResponse` (session_id, room_name, livekit_token), `SessionListItem` (id, room_name, status, started_at, ended_at), `SessionHistoryResponse` (items, total), `MessageItem` (id, role, mode, content, created_at)

## 4. Сервис сессий

- [x] 4.1 Создать `apps/api/src/sessions/service.py` — функции: `create_session(user_id, db)`, `get_user_sessions(user_id, offset, limit, db)`, `get_session_messages(session_id, user_id, db)`
- [x] 4.2 В `create_session` — генерация `room_name` формата `session-{uuid}`, создание записи Session, возврат сессии
- [x] 4.3 В `get_user_sessions` — фильтрация по `user_id`, сортировка `started_at` desc, offset/limit, возврат списка и total
- [x] 4.4 В `get_session_messages` — проверка принадлежности сессии пользователю (404 если чужая/не существует), сортировка `created_at` asc

## 5. Роутер

- [x] 5.1 Создать `apps/api/src/sessions/__init__.py` и `apps/api/src/sessions/router.py` с тремя эндпоинтами: `POST /sessions/start` (201), `GET /sessions/history` (200), `GET /sessions/{id}/messages` (200)
- [x] 5.2 В `POST /sessions/start` — вызов `create_session`, генерация LiveKit-токена, возврат `SessionStartResponse`
- [x] 5.3 В `GET /sessions/history` — параметры `offset` (default 0), `limit` (default 20, max 100), возврат `SessionHistoryResponse`
- [x] 5.4 Подключить роутер в `apps/api/src/main.py` с префиксом `/sessions` и тегом `sessions`

## 6. Тесты

- [x] 6.1 Тест `POST /sessions/start` — успешное создание, проверка полей ответа, запись в БД
- [x] 6.2 Тест `POST /sessions/start` без JWT — 401
- [x] 6.3 Тест `GET /sessions/history` — возврат сессий пользователя, пагинация, пустой список
- [x] 6.4 Тест `GET /sessions/{id}/messages` — сообщения своей сессии, 404 для чужой, пустой список
