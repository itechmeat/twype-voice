## ADDED Requirements

### Requirement: Deepgram STT plugin integration
The agent SHALL use `livekit-plugins-deepgram` to perform streaming speech-to-text on the audio received from the linked participant. The STT plugin SHALL be configured as part of the `AgentSession` pipeline via `AgentSession(stt=...)`.

#### Scenario: STT processes speech from participant
- **WHEN** VAD detects a speech segment in the participant's audio stream
- **THEN** the audio is streamed to Deepgram for real-time transcription

#### Scenario: Deepgram API key not set
- **WHEN** `DEEPGRAM_API_KEY` environment variable is not set
- **THEN** the agent fails to start with a validation error

### Requirement: Streaming interim and final transcripts
The STT plugin SHALL produce interim (partial) transcripts during speech and a final transcript when the utterance is complete. Interim transcripts update progressively as more audio is processed.

#### Scenario: Interim transcripts during speech
- **WHEN** the participant is speaking
- **THEN** the STT plugin produces interim transcripts that progressively refine as more audio arrives

#### Scenario: Final transcript after utterance
- **WHEN** the participant finishes an utterance (silence detected by VAD)
- **THEN** the STT plugin produces a final transcript with the complete recognized text

### Requirement: Language configuration
The STT plugin SHALL support Russian and English language recognition. The language SHALL be configurable via the `STT_LANGUAGE` environment variable (default: `multi`). Supported values: `ru`, `en`, `multi`.

#### Scenario: Default language (multi)
- **WHEN** `STT_LANGUAGE` is not set
- **THEN** the STT plugin uses Deepgram's `multi` language setting for automatic language detection

#### Scenario: Explicit language setting
- **WHEN** `STT_LANGUAGE` is set to `ru`
- **THEN** the STT plugin uses Russian language model for recognition

### Requirement: STT model configuration
The STT plugin SHALL use the Deepgram model specified by the `STT_MODEL` environment variable (default: `nova-3`).

#### Scenario: Default model
- **WHEN** `STT_MODEL` is not set
- **THEN** the STT plugin uses `nova-3` model

#### Scenario: Custom model
- **WHEN** `STT_MODEL` is set to a different model name
- **THEN** the STT plugin uses the specified model

### Requirement: Sentiment extraction
The STT plugin SHALL enable Deepgram's sentiment analysis feature. The agent SHALL extract the average sentiment score (-1..1) from the final transcript result and make it available for persistence.

#### Scenario: Sentiment score extracted from final transcript
- **WHEN** a final transcript is received from Deepgram with sentiment data
- **THEN** the agent computes the average sentiment score across all sentences and associates it with the transcript

#### Scenario: Sentiment data unavailable
- **WHEN** a final transcript is received without sentiment data (feature not supported for the language/model)
- **THEN** the sentiment score SHALL be `null` and the transcript is processed normally

### Requirement: Interim transcript delivery via data channel
The agent SHALL publish interim transcripts to the LiveKit room via data channel as JSON messages. Interim transcripts SHALL use lossy delivery (`reliable=false`). Final transcripts SHALL use reliable delivery (`reliable=true`).

#### Scenario: Interim transcript sent to client
- **WHEN** an interim transcript is received from STT
- **THEN** the agent publishes a JSON message via data channel with `type: "transcript"`, `is_final: false`, `text`, and `language`

#### Scenario: Final transcript sent to client
- **WHEN** a final transcript is received from STT
- **THEN** the agent publishes a JSON message via data channel with `type: "transcript"`, `is_final: true`, `text`, `language`, `message_id`, and `sentiment_raw`

#### Scenario: Data channel message format
- **WHEN** a transcript message is published
- **THEN** the JSON payload SHALL contain at minimum: `type` (string), `is_final` (boolean), `text` (string), `language` (string)

### Requirement: STT error handling
The agent SHALL handle Deepgram connection failures gracefully. STT errors SHALL be logged but SHALL NOT crash the agent process.

#### Scenario: Deepgram connection lost during session
- **WHEN** the WebSocket connection to Deepgram is lost during an active session
- **THEN** the agent logs the error at ERROR level and the STT plugin attempts to reconnect

#### Scenario: Deepgram returns an error response
- **WHEN** Deepgram returns an error for a recognition request
- **THEN** the agent logs the error and continues processing subsequent audio
