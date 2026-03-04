## Context

API-сервер (FastAPI) содержит единственный эндпоинт `/health`. Модель `User` уже создана с полями для аутентификации (`password_hash`, `is_verified`, `verification_code`, `verification_expires_at`). БД-инфраструктура (async SQLAlchemy + asyncpg, Alembic, seed) готова. Зависимости python-jose, passlib, resend указаны в specs.md, но ещё не добавлены в `pyproject.toml`.

Сейчас нужно реализовать полный auth-цикл: регистрация → верификация email → логин → refresh токенов, а также middleware для защиты будущих маршрутов.

## Goals / Non-Goals

**Goals:**
- Полный auth-цикл через 4 REST-эндпоинта
- JWT access + refresh токены
- Email-верификация через Resend
- Reusable dependency для защищённых маршрутов
- Тестовое покрытие всех эндпоинтов

**Non-Goals:**
- OAuth / SSO / сторонние провайдеры (не MVP)
- Rate limiting (отдельная история)
- Password reset flow (отдельная история)
- Фронтенд auth UI (S06+)
- Refresh token rotation / revocation list (упрощение для MVP)

## Decisions

### 1. Структура модуля auth

**Решение:** Отдельный пакет `apps/api/src/auth/` с разделением на слои.

```
apps/api/src/auth/
├── __init__.py
├── router.py      # FastAPI router с 4 эндпоинтами
├── service.py     # Бизнес-логика (регистрация, логин, верификация)
├── dependencies.py # get_current_user dependency
├── jwt.py         # Создание и валидация JWT
└── email.py       # Отправка верификационных кодов через Resend
```

**Альтернатива:** Плоская структура (всё в одном файле). Отклонена — 4 эндпоинта + JWT-логика + email-сервис = слишком много для одного файла, и service/jwt/email будут переиспользоваться в других модулях.

### 2. JWT payload и хранение

**Решение:** Stateless JWT. Access token содержит `sub` (user_id), `exp`, `type: "access"`. Refresh token — `sub`, `exp`, `type: "refresh"`. Оба подписаны одним `JWT_SECRET` (HS256).

**Альтернатива:** Хранение refresh-токенов в БД с возможностью отзыва. Отклонена для MVP — добавляет сложность без критической необходимости. Можно добавить позже без breaking changes (добавив проверку в БД при refresh).

### 3. Верификация email

**Решение:** 6-значный числовой код, хранится в `users.verification_code` с TTL в `verification_expires_at` (10 минут). Отправляется через Resend API. После успешной верификации код обнуляется.

**Альтернатива:** Ссылка-токен в email. Отклонена — для PWA/мобильного UX ввод кода удобнее, чем переход по ссылке.

### 4. Pydantic-схемы

**Решение:** Файл `apps/api/src/schemas/auth.py` с отдельными моделями для каждого запроса/ответа:
- `RegisterRequest`, `RegisterResponse`
- `VerifyRequest`, `VerifyResponse`
- `LoginRequest`, `TokenResponse` (переиспользуется для login и refresh)
- `RefreshRequest`

### 5. Dependency для защищённых маршрутов

**Решение:** FastAPI `Depends(get_current_user)` — извлекает Bearer token из заголовка `Authorization`, валидирует JWT, загружает пользователя из БД, проверяет `is_verified`. Возвращает объект `User`.

**Альтернатива:** Middleware на уровне приложения. Отклонена — dependency гибче (можно применять к отдельным роутерам), лучше интегрируется с OpenAPI-документацией.

### 6. Тестирование

**Решение:** pytest + httpx `AsyncClient` с тестовой PostgreSQL. Фикстуры в `conftest.py`: тестовая БД, async session, FastAPI test client. Resend замокан (не отправлять реальные email в тестах).

## Risks / Trade-offs

- **[Stateless refresh tokens]** → Невозможно отозвать отдельный refresh token. Митигация: короткий TTL access (15 мин), при необходимости добавить token blacklist в следующей итерации.
- **[Один JWT_SECRET для access и refresh]** → Компрометация секрета открывает оба типа. Митигация: приемлемо для MVP на single-server, разделение секретов — при масштабировании.
- **[Resend как единственный email-провайдер]** → Vendor lock-in. Митигация: email-логика изолирована в `auth/email.py`, замена провайдера — изменение одного файла.
- **[Нет rate limiting на auth-эндпоинтах]** → Потенциальный brute-force. Митигация: запланировано в отдельной истории; verification code с TTL частично ограничивает перебор.
