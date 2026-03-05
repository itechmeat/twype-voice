## ADDED Requirements

### Requirement: Primary model configuration
LiteLLM Proxy SHALL be configured with Gemini Flash-Lite (`gemini/gemini-2.0-flash-lite`) as the primary model under the name `gemini-flash-lite` in `configs/litellm.yaml`.

#### Scenario: Primary model available
- **WHEN** the agent sends a chat completion request with model `gemini-flash-lite`
- **THEN** LiteLLM Proxy routes the request to `gemini/gemini-2.0-flash-lite` via Google API

#### Scenario: Primary model streaming
- **WHEN** the agent sends a streaming chat completion request
- **THEN** LiteLLM Proxy returns an SSE stream of token chunks in OpenAI-compatible format

### Requirement: Fallback model configuration
LiteLLM Proxy SHALL be configured with GPT-4.1-mini (`openai/gpt-4.1-mini`) as a fallback model. When the primary model fails (error or timeout), LiteLLM SHALL automatically retry with the fallback model.

#### Scenario: Primary model fails, fallback succeeds
- **WHEN** the primary model (Gemini Flash-Lite) returns an error or times out
- **THEN** LiteLLM Proxy automatically retries the request with GPT-4.1-mini

#### Scenario: Both models fail
- **WHEN** both primary and fallback models fail
- **THEN** LiteLLM Proxy returns an error response to the agent

### Requirement: Health check endpoint
LiteLLM Proxy SHALL expose a `/health` endpoint. The Docker container SHALL use this endpoint for its health check with the `LITELLM_MASTER_KEY` for authentication.

#### Scenario: LiteLLM is healthy
- **WHEN** a GET request is sent to `/health` with a valid master key
- **THEN** LiteLLM returns a 200 status

#### Scenario: LiteLLM is unhealthy
- **WHEN** LiteLLM Proxy cannot connect to any configured model provider
- **THEN** the health check fails and Docker marks the container as unhealthy

### Requirement: Master key authentication
LiteLLM Proxy SHALL require the `LITELLM_MASTER_KEY` environment variable for API authentication. All requests to LiteLLM SHALL include this key as a Bearer token.

#### Scenario: Request with valid master key
- **WHEN** a request includes `Authorization: Bearer <LITELLM_MASTER_KEY>`
- **THEN** LiteLLM processes the request

#### Scenario: Request without authentication
- **WHEN** a request is sent without an Authorization header
- **THEN** LiteLLM rejects the request with a 401 status
