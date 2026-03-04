## 1. Зависимости и структура

- [x] 1.1 Добавить python-jose, bcrypt, resend в `apps/api/pyproject.toml` и выполнить `uv lock`
- [x] 1.2 Создать структуру модуля `apps/api/src/auth/` (`__init__.py`, `router.py`, `service.py`, `dependencies.py`, `jwt.py`, `email.py`)
- [x] 1.3 Создать файл Pydantic-схем `apps/api/src/schemas/auth.py`

## 2. JWT-модуль

- [x] 2.1 Реализовать `auth/jwt.py`: функции `create_access_token(user_id)`, `create_refresh_token(user_id)`, `decode_token(token)` с HS256, переменная `JWT_SECRET`
- [x] 2.2 Реализовать Pydantic-схемы в `schemas/auth.py`: `RegisterRequest`, `RegisterResponse`, `VerifyRequest`, `LoginRequest`, `RefreshRequest`, `TokenResponse`

## 3. Email-сервис

- [x] 3.1 Реализовать `auth/email.py`: функция `send_verification_code(email, code)` через Resend API

## 4. Auth-сервис (бизнес-логика)

- [x] 4.1 Реализовать `auth/service.py` — функция `register_user(email, password, session)`: хеширование пароля, генерация 6-значного кода, сохранение пользователя, отправка email
- [x] 4.2 Реализовать `auth/service.py` — функция `verify_user(email, code, session)`: проверка кода, проверка TTL, установка `is_verified=true`, возврат токенов
- [x] 4.3 Реализовать `auth/service.py` — функция `login_user(email, password, session)`: проверка пароля, проверка `is_verified`, возврат токенов
- [x] 4.4 Реализовать `auth/service.py` — функция `refresh_tokens(refresh_token, session)`: валидация refresh token, проверка type, генерация новой пары токенов

## 5. Auth dependency (middleware)

- [x] 5.1 Реализовать `auth/dependencies.py` — `get_current_user(token, session)`: извлечение Bearer token, декодирование JWT, проверка type="access", загрузка пользователя из БД, проверка `is_verified`

## 6. Роутер

- [x] 6.1 Реализовать `auth/router.py` — `POST /auth/register`, `POST /auth/verify`, `POST /auth/login`, `POST /auth/refresh` с корректными HTTP-кодами
- [x] 6.2 Подключить auth router в `apps/api/src/main.py`

## 7. Тесты

- [x] 7.1 Создать `apps/api/tests/conftest.py` с фикстурами: тестовая БД (async), test client (httpx AsyncClient), мок Resend
- [x] 7.2 Тесты регистрации: успешная, дубликат email, короткий пароль
- [x] 7.3 Тесты верификации: успешная, просроченный код, неверный код, уже верифицирован
- [x] 7.4 Тесты логина: успешный, неверный пароль, неверифицированный пользователь, несуществующий email
- [x] 7.5 Тесты refresh: успешный, просроченный токен, невалидный токен
- [x] 7.6 Тесты middleware: валидный токен, отсутствующий заголовок, просроченный токен, refresh token вместо access, несуществующий пользователь, неверифицированный пользователь
