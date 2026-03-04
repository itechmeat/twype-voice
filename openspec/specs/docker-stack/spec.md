## ADDED Requirements

### Requirement: Docker Compose production configuration
Система SHALL предоставлять файл `docker/docker-compose.yml` с определением семи сервисов: `caddy`, `api`, `livekit`, `agent`, `litellm`, `postgres`, `coturn`. Все сервисы SHALL быть объединены в bridge-сеть `twype-net`.

#### Scenario: Production compose запускает все сервисы
- **WHEN** выполняется `docker compose -f docker/docker-compose.yml up -d`
- **THEN** все семь контейнеров переходят в состояние running и проходят health check в течение 60 секунд

#### Scenario: Сервисы разрешают друг друга по имени
- **WHEN** контейнер `api` обращается к `postgres:5432`
- **THEN** соединение устанавливается через внутреннюю сеть `twype-net`

### Requirement: Docker Compose development configuration
Система SHALL предоставлять файл `docker/docker-compose.dev.yml` с dev-вариантами сервисов `api`, `agent`, `web` — volume-маунт исходников и hot-reload. Инфраструктурные сервисы (`livekit`, `litellm`, `postgres`, `caddy`, `coturn`) SHALL быть идентичны production.

#### Scenario: Dev compose поддерживает hot-reload для API
- **WHEN** выполняется `docker compose -f docker/docker-compose.dev.yml up` и изменяется файл в `apps/api/src/`
- **THEN** контейнер `api` автоматически перезагружает приложение без перезапуска контейнера

#### Scenario: Dev compose поддерживает hot-reload для web
- **WHEN** изменяется файл в `apps/web/src/`
- **THEN** Vite dev server применяет HMR без полной перезагрузки страницы

### Requirement: Health checks для всех контейнеров
Каждый сервис в Docker Compose SHALL определять health check, позволяющий Docker определить готовность контейнера.

#### Scenario: Postgres health check
- **WHEN** контейнер `postgres` запущен
- **THEN** health check выполняет `pg_isready` и возвращает healthy после инициализации БД

#### Scenario: API health check
- **WHEN** контейнер `api` запущен
- **THEN** health check выполняет HTTP-запрос к `GET /health` и получает статус 200

#### Scenario: LiveKit health check
- **WHEN** контейнер `livekit` запущен
- **THEN** health check подтверждает доступность сервиса

### Requirement: Dockerfiles для кастомных приложений
Система SHALL предоставлять multi-stage Dockerfiles для `api`, `agent` и `web` с targets `dev` и `prod`.

#### Scenario: API Dockerfile dev target
- **WHEN** Dockerfile.api собирается с `--target dev`
- **THEN** образ содержит uv и Python 3.13, рабочая директория готова к volume-маунту исходников

#### Scenario: API Dockerfile prod target
- **WHEN** Dockerfile.api собирается с `--target prod`
- **THEN** образ содержит установленные зависимости и скопированные исходники, готов к запуску uvicorn

#### Scenario: Web Dockerfile prod target
- **WHEN** Dockerfile.web собирается с `--target prod`
- **THEN** образ содержит собранные статические файлы, обслуживаемые через nginx

### Requirement: Именованные Docker volumes
Система SHALL определять именованные volumes для персистентных данных: `pgdata` для PostgreSQL, `caddy-data` и `caddy-config` для Caddy.

#### Scenario: Данные PostgreSQL сохраняются между перезапусками
- **WHEN** контейнер `postgres` перезапускается через `docker compose restart postgres`
- **THEN** все данные в базе сохранены (volume `pgdata` не удаляется)

### Requirement: Сетевые порты и маршрутизация
Система SHALL открывать наружу только необходимые порты согласно сетевой карте из `docs/architecture.md`: Caddy (80, 443), LiveKit (7881 TCP, 50000-60000 UDP), coturn (3478, 5349, 49152-65535 UDP). В dev-режиме дополнительно web (5173).

#### Scenario: Внутренние порты не доступны снаружи
- **WHEN** Docker Compose запущен
- **THEN** порты `api:8000`, `litellm:4000`, `postgres:5432`, `livekit:7880` недоступны с хоста (только через внутреннюю сеть)

#### Scenario: Dev web-порт доступен с хоста
- **WHEN** запущен dev compose
- **THEN** Vite dev server доступен на `localhost:5173`

### Requirement: Зависимости между сервисами
Docker Compose SHALL определять `depends_on` с условием `service_healthy` для корректного порядка запуска.

#### Scenario: API стартует после Postgres
- **WHEN** выполняется `docker compose up`
- **THEN** контейнер `api` ожидает healthy-статуса `postgres` перед запуском

#### Scenario: Agent стартует после LiveKit, LiteLLM и Postgres
- **WHEN** выполняется `docker compose up`
- **THEN** контейнер `agent` ожидает healthy-статуса `livekit`, `litellm` и `postgres`
