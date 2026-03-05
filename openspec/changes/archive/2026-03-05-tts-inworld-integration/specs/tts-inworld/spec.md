## ADDED Requirements

### Requirement: TTS plugin initialization
The agent SHALL initialize a TTS plugin via `build_tts(settings)` factory function in `apps/agent/src/tts.py`. The function SHALL return an instance of `inworld.TTS` when `TTS_PROVIDER` is `"inworld"`, or `elevenlabs.TTS` when `TTS_PROVIDER` is `"elevenlabs"`.

#### Scenario: Inworld TTS created with default settings
- **WHEN** `TTS_PROVIDER` is `"inworld"` and `INWORLD_API_KEY` is set
- **THEN** `build_tts()` returns an `inworld.TTS` instance configured with the API key, voice from `TTS_INWORLD_VOICE`, model `TTS_INWORLD_MODEL`, speaking rate from `TTS_SPEAKING_RATE`, and temperature from `TTS_TEMPERATURE`

#### Scenario: ElevenLabs TTS created as fallback provider
- **WHEN** `TTS_PROVIDER` is `"elevenlabs"` and `ELEVENLABS_API_KEY` is set
- **THEN** `build_tts()` returns an `elevenlabs.TTS` instance configured with the API key, voice ID from `TTS_ELEVENLABS_VOICE_ID`, and model from `TTS_ELEVENLABS_MODEL`

### Requirement: TTS settings in AgentSettings
The `AgentSettings` class SHALL include TTS configuration fields: `TTS_PROVIDER` (default: `"inworld"`), `INWORLD_API_KEY` (required when provider is inworld), `TTS_INWORLD_VOICE` (default: `"Olivia"`), `TTS_INWORLD_MODEL` (default: `"inworld-tts-1.5-mini"`), `TTS_SPEAKING_RATE` (default: `1.0`), `TTS_TEMPERATURE` (default: `1.0`), `ELEVENLABS_API_KEY` (optional), `TTS_ELEVENLABS_VOICE_ID` (default: `"EXAVITQu4vr4xnSDxMaL"`), `TTS_ELEVENLABS_MODEL` (default: `"eleven_flash_v2_5"`).

#### Scenario: Default TTS settings loaded
- **WHEN** the agent starts with `TTS_PROVIDER` unset
- **THEN** `TTS_PROVIDER` defaults to `"inworld"` and all TTS settings use their documented defaults

#### Scenario: Custom TTS parameters from environment
- **WHEN** environment sets `TTS_SPEAKING_RATE=0.8` and `TTS_TEMPERATURE=0.6`
- **THEN** the Inworld TTS plugin is configured with speaking rate 0.8 and temperature 0.6

### Requirement: Streaming TTS synthesis
The TTS plugin SHALL use streaming synthesis (`stream()` method) to begin producing audio before the full LLM response is complete. The `livekit-plugins-inworld` plugin uses WebSocket bidirectional streaming; the `livekit-plugins-elevenlabs` plugin uses WebSocket streaming.

#### Scenario: TTS streams audio from LLM token stream
- **WHEN** the LLM produces response tokens via streaming
- **THEN** the TTS plugin receives tokens incrementally and begins audio synthesis before the LLM response is complete

#### Scenario: Audio output reaches client via WebRTC
- **WHEN** the TTS plugin produces synthesized audio frames
- **THEN** LiveKit transmits the audio to the client via WebRTC audio track

### Requirement: Language-aware voice selection
The `build_tts()` function SHALL accept an optional `language` parameter. When provided, it SHALL select the appropriate voice for that language from a voice mapping. When not provided, the voice from settings is used.

#### Scenario: English voice selected
- **WHEN** `build_tts()` is called with `language="en"` and provider is `"inworld"`
- **THEN** the TTS plugin is configured with the English voice from the voice mapping

#### Scenario: Default voice when no language specified
- **WHEN** `build_tts()` is called without a `language` parameter
- **THEN** the TTS plugin uses the voice configured in `TTS_INWORLD_VOICE` or `TTS_ELEVENLABS_VOICE_ID`

### Requirement: Dependencies
The agent SHALL depend on `livekit-plugins-inworld>=1.4.4` and `livekit-plugins-elevenlabs>=1.4.3` in `apps/agent/pyproject.toml`.

#### Scenario: Inworld plugin installed
- **WHEN** the agent dependencies are installed via `uv sync`
- **THEN** `livekit.plugins.inworld` is importable

#### Scenario: ElevenLabs plugin installed
- **WHEN** the agent dependencies are installed via `uv sync`
- **THEN** `livekit.plugins.elevenlabs` is importable

### Requirement: Environment variables in .env.example
The `.env.example` file SHALL document all TTS-related environment variables with placeholder values: `TTS_PROVIDER`, `INWORLD_API_KEY`, `TTS_INWORLD_VOICE`, `TTS_INWORLD_MODEL`, `TTS_SPEAKING_RATE`, `TTS_TEMPERATURE`, `ELEVENLABS_API_KEY`, `TTS_ELEVENLABS_VOICE_ID`, `TTS_ELEVENLABS_MODEL`.

#### Scenario: TTS variables documented in .env.example
- **WHEN** a developer copies `.env.example` to `.env`
- **THEN** all TTS-related variables are present with descriptive comments and defaults
