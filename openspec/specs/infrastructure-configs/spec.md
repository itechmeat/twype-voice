## ADDED Requirements

### Requirement: LiveKit Server configuration
`configs/livekit.yaml` SHALL содержать конфигурацию LiveKit Server для dev-среды: API key/secret для авторизации, диапазон UDP-портов (50000-60000), настройки TURN-интеграции с coturn.

#### Scenario: LiveKit стартует с dev-конфигурацией
- **WHEN** LiveKit Server запущен с `configs/livekit.yaml`
- **THEN** сервер принимает WebSocket-соединения на порту 7880 и валидирует токены по заданному API key/secret

#### Scenario: TURN-интеграция настроена
- **WHEN** LiveKit Server обрабатывает ICE negotiation
- **THEN** он включает coturn TURN-сервер в ICE candidates для клиентов

### Requirement: LiteLLM Proxy configuration
`configs/litellm.yaml` SHALL содержать конфигурацию LiteLLM Proxy с определением моделей. В dev-среде SHALL быть определена хотя бы одна модель (Gemini Flash-Lite или placeholder).

#### Scenario: LiteLLM стартует с конфигурацией
- **WHEN** LiteLLM Proxy запущен с `configs/litellm.yaml`
- **THEN** сервер доступен на порту 4000 и отвечает на `GET /health`

#### Scenario: Модели определены в конфигурации
- **WHEN** отправлен запрос `GET /models` на LiteLLM
- **THEN** ответ содержит список настроенных моделей

### Requirement: Caddy reverse proxy configuration
`configs/caddy/Caddyfile` SHALL настраивать Caddy как reverse proxy: проксирование `/api/*` на `api:8000`, WebSocket-проксирование LiveKit signaling на `livekit:7880`. В dev-среде SHALL работать на localhost без реальных SSL-сертификатов.

#### Scenario: API проксируется через Caddy
- **WHEN** HTTP-запрос отправлен на `https://localhost/api/health`
- **THEN** Caddy проксирует его на `api:8000/health` и возвращает ответ

#### Scenario: LiveKit signaling проксируется
- **WHEN** WebSocket-соединение устанавливается на `wss://localhost/livekit-signaling`
- **THEN** Caddy проксирует его на `livekit:7880`

### Requirement: coturn TURN server configuration
`configs/coturn/turnserver.conf` SHALL настраивать coturn: listening-port 3478, TLS-порт 5349, relay-диапазон 49152-65535, аутентификация через credentials из переменных окружения.

#### Scenario: coturn стартует с конфигурацией
- **WHEN** coturn запущен с `configs/coturn/turnserver.conf`
- **THEN** сервер слушает на портах 3478 (TCP/UDP) и 5349 (TLS)

#### Scenario: TURN credentials из переменных окружения
- **WHEN** coturn стартует с `TURN_USERNAME` и `TURN_PASSWORD` из `.env`
- **THEN** аутентификация TURN-клиентов использует эти credentials
