## ADDED Requirements

### Requirement: Silero VAD integration
The agent SHALL use `livekit-plugins-silero` `SileroVAD` for voice activity detection on the incoming audio stream from the linked participant. VAD SHALL be configured as part of the `AgentSession` pipeline.

#### Scenario: VAD processes incoming audio
- **WHEN** the linked participant sends audio
- **THEN** Silero VAD processes the audio stream and detects speech segments

#### Scenario: Speech start detected
- **WHEN** VAD detects the beginning of speech in the audio stream
- **THEN** the agent logs a speech-start event at DEBUG level with the participant identity

#### Scenario: Speech end detected
- **WHEN** VAD detects the end of speech (silence after speech)
- **THEN** the agent logs a speech-end event at DEBUG level with the participant identity

### Requirement: VAD configuration via settings
VAD thresholds SHALL be configurable via environment variables with sensible defaults. Configurable parameters: `VAD_ACTIVATION_THRESHOLD` (default: `0.5`), `VAD_MIN_SPEECH_DURATION` (default: `0.05`), `VAD_MIN_SILENCE_DURATION` (default: `0.3`).

#### Scenario: Default VAD configuration
- **WHEN** no VAD-related environment variables are set
- **THEN** the agent uses default thresholds (activation: 0.5, min speech: 0.05s, min silence: 0.3s)

#### Scenario: Custom VAD configuration
- **WHEN** VAD environment variables are set (e.g., `VAD_ACTIVATION_THRESHOLD=0.6`)
- **THEN** the agent uses the custom threshold values for Silero VAD

### Requirement: Silero model available at build time
The Silero ONNX model file SHALL be downloaded during Docker image build via `livekit-agents download-files`. The agent SHALL NOT download the model at runtime.

#### Scenario: Docker build downloads Silero model
- **WHEN** the agent Docker image is built
- **THEN** the build stage runs `livekit-agents download-files` and the model is cached in the image

#### Scenario: Agent starts without network access to model host
- **WHEN** the agent starts and the Silero model was downloaded at build time
- **THEN** the agent loads the model from the local filesystem without network calls
