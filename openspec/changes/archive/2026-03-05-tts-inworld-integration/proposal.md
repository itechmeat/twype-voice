## Why

The agent voice pipeline currently handles VAD → STT → LLM but has no speech synthesis — the agent cannot speak back to the user. TTS is the missing piece to close the voice loop. Inworld AI is the primary TTS provider (golden profile), with ElevenLabs as a fallback for availability. This unblocks S09 (full voice pipeline assembly) and all subsequent voice-dependent stories.

## What Changes

- Custom TTS plugin for Inworld AI in `apps/agent/src/plugins/`, implementing the LiveKit Agents TTS interface for streaming synthesis
- ElevenLabs TTS fallback via `livekit-plugins-elevenlabs` when Inworld is unavailable
- TTS builder function following the established plugin pattern (like `build_stt()`, `build_llm()`)
- TTS plugin integrated into `AgentSession` and prewarmed at worker startup
- New environment variables for Inworld and ElevenLabs API keys, voice IDs, and synthesis parameters (language, speed, expressiveness)
- Settings extended with TTS configuration (provider selection, voice params per language)
- Russian and English voice support with language-aware voice selection matching STT-detected language

## Capabilities

### New Capabilities
- `tts-inworld`: Custom Inworld AI TTS plugin with streaming synthesis, multi-language voice selection, expressiveness/speed parameters, and ElevenLabs fallback

### Modified Capabilities
- `agent-entrypoint`: TTS plugin added to prewarm sequence and AgentSession assembly; language-aware voice selection based on STT-detected language

## Impact

- **Code:** `apps/agent/src/plugins/` (new directory), `apps/agent/src/agent.py`, `apps/agent/src/main.py`, `apps/agent/src/settings.py`
- **Dependencies:** new `livekit-plugins-elevenlabs`, Inworld HTTP/WebSocket client (custom or lightweight SDK)
- **Environment:** new env vars `INWORLD_API_KEY`, `ELEVENLABS_API_KEY`, `TTS_PROVIDER`, voice ID and synthesis params
- **Infrastructure:** no new containers; Inworld and ElevenLabs are external SaaS APIs
- **Latency:** TTS adds to voice-to-voice latency; streaming synthesis is critical to meet ~800 ms target
