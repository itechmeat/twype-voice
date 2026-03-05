## ADDED Requirements

### Requirement: LLM plugin integration
The agent SHALL use `livekit-plugins-openai` to connect to LiteLLM Proxy. The plugin SHALL be configured with `base_url` pointing to `LITELLM_URL` + `/v1` and `api_key` set to `LITELLM_MASTER_KEY`. The LLM plugin SHALL be passed to `AgentSession(llm=...)`.

#### Scenario: LLM plugin connects to LiteLLM Proxy
- **WHEN** the agent starts and creates an `AgentSession`
- **THEN** the LLM plugin is configured with the LiteLLM Proxy endpoint and included in the session pipeline

#### Scenario: LITELLM_URL not set
- **WHEN** the `LITELLM_URL` environment variable is not set
- **THEN** the agent fails to start with a validation error

#### Scenario: LITELLM_MASTER_KEY not set
- **WHEN** the `LITELLM_MASTER_KEY` environment variable is not set
- **THEN** the agent fails to start with a validation error

### Requirement: Streaming response generation
The agent SHALL generate streaming LLM responses to user speech. When the user finishes speaking (detected by VAD), the transcript SHALL be sent to the LLM, and the response SHALL stream back token by token through the `AgentSession` pipeline.

#### Scenario: User speaks and receives LLM response
- **WHEN** a user utterance is transcribed by STT
- **THEN** the transcript is sent to the LLM and a streaming response is generated

#### Scenario: Response streams incrementally
- **WHEN** the LLM generates a response
- **THEN** tokens are delivered incrementally through the AgentSession pipeline (available for future TTS consumption)

### Requirement: LLM model configuration
The agent SHALL use the model specified by the `LLM_MODEL` environment variable (default: `gemini-flash-lite`). The model name SHALL match a `model_name` entry in `litellm.yaml`.

#### Scenario: Default model
- **WHEN** `LLM_MODEL` is not set
- **THEN** the agent requests model `gemini-flash-lite` from LiteLLM Proxy

#### Scenario: Custom model
- **WHEN** `LLM_MODEL` is set to a different model name
- **THEN** the agent requests the specified model from LiteLLM Proxy

### Requirement: LLM generation parameters
The agent SHALL configure LLM generation with `LLM_TEMPERATURE` (default: `0.7`) and `LLM_MAX_TOKENS` (default: `512`) from environment variables.

#### Scenario: Default generation parameters
- **WHEN** `LLM_TEMPERATURE` and `LLM_MAX_TOKENS` are not set
- **THEN** the LLM plugin uses temperature `0.7` and max tokens `512`

#### Scenario: Custom generation parameters
- **WHEN** `LLM_TEMPERATURE` is set to `0.5` and `LLM_MAX_TOKENS` is set to `256`
- **THEN** the LLM plugin uses the specified values

### Requirement: Basic system prompt
The agent SHALL provide a hardcoded system prompt that defines the agent's role as a knowledgeable expert assistant. The prompt SHALL instruct the agent to respond in the user's language, maintain a conversational tone suitable for voice, and keep responses brief (2-5 sentences).

#### Scenario: System prompt included in LLM context
- **WHEN** a user utterance is sent to the LLM
- **THEN** the system prompt is included as the first message in the conversation context

#### Scenario: Agent responds in user's language
- **WHEN** the user speaks in Russian
- **THEN** the agent generates a response in Russian

#### Scenario: Agent responds in English
- **WHEN** the user speaks in English
- **THEN** the agent generates a response in English

### Requirement: LLM timeout handling
The agent SHALL set a request timeout of 15 seconds on the LLM plugin. When a timeout or connection error occurs, the agent SHALL log the error and notify the user via data channel that the service is temporarily unavailable.

#### Scenario: LLM request times out
- **WHEN** the LLM request does not complete within 15 seconds
- **THEN** the agent logs the timeout at ERROR level and sends an error notification to the user via data channel

#### Scenario: LiteLLM Proxy is unreachable
- **WHEN** the agent cannot connect to LiteLLM Proxy
- **THEN** the agent logs the connection error and sends an error notification to the user via data channel

#### Scenario: LLM error does not crash the agent
- **WHEN** an LLM request fails for any reason
- **THEN** the agent continues running and processes subsequent user utterances
