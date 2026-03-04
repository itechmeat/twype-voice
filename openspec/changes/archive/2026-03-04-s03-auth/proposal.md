## Why

Без аутентификации API полностью открыт — любой может создавать сессии с агентом и расходовать ресурсы STT/LLM/TTS. S03 добавляет полный цикл email+password аутентификации: регистрацию, подтверждение email, логин и обновление токенов. Это фундамент для всех защищённых эндпоинтов (сессии, история, источники).

## What Changes

- Добавление 4 эндпоинтов: `POST /auth/register`, `POST /auth/verify`, `POST /auth/login`, `POST /auth/refresh`
- Хеширование паролей через passlib/bcrypt (минимум 8 символов)
- Отправка 6-значного кода верификации на email через Resend
- Генерация JWT access-токенов (15 мин, HS256) и refresh-токенов (30 дней)
- Middleware/dependency для валидации Bearer-токенов на защищённых маршрутах
- Pydantic-схемы запросов/ответов для всех auth-эндпоинтов
- Тесты на все эндпоинты аутентификации (pytest + httpx)

## Capabilities

### New Capabilities
- `auth-endpoints`: Эндпоинты регистрации, верификации email, логина и обновления токенов
- `auth-middleware`: FastAPI dependency для извлечения и валидации JWT из заголовка Authorization, предоставляющая текущего пользователя защищённым маршрутам

### Modified Capabilities
<!-- Нет изменений в существующих спецификациях -->

## Impact

- **Код:** `apps/api/src/auth/` (новый модуль), `apps/api/src/routes/` (новые роутеры), `apps/api/src/schemas/` (Pydantic-модели), `apps/api/src/main.py` (подключение роутеров)
- **Зависимости:** python-jose, passlib[bcrypt], resend — уже указаны в specs.md, нужно добавить в `pyproject.toml`
- **Переменные окружения:** `JWT_SECRET`, `RESEND_API_KEY` (уже определены в `.env.example`)
- **Тесты:** `apps/api/tests/test_auth.py`, `apps/api/tests/conftest.py` (фикстуры для тестовой БД и клиента)
- **БД:** модель User уже содержит `password_hash`, `is_verified`, `verification_code`, `verification_expires_at` — новых миграций не требуется
