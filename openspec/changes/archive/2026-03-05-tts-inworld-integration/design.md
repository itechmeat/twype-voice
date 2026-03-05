## Context

The agent voice pipeline currently implements VAD → STT → LLM but produces no audio output — the agent cannot speak. TTS is the last component needed to close the voice loop (S08), unblocking S09 (full pipeline assembly).

Research (see `docs/explorations/2026-03-05-tts-integration-inworld-elevenlabs-livekit.md`) revealed that an official `livekit-plugins-inworld` package (v1.4.4) already exists on PyPI. This eliminates the need for a custom plugin. Similarly, `livekit-plugins-elevenlabs` (v1.4.3) exists for the fallback provider.

Current pipeline plugins follow a consistent pattern: factory function in a dedicated module, settings in `AgentSettings`, prewarm at worker start, injection into `AgentSession`.

## Goals / Non-Goals

**Goals:**
- Add Inworld TTS to the agent pipeline so it produces spoken audio responses
- Provide ElevenLabs as a fallback when Inworld is unavailable
- Support Russian and English with language-aware voice selection
- Expose voice tuning parameters (speaking rate, temperature/expressiveness) via settings
- Follow the established plugin pattern (factory module, settings, prewarm, AgentSession)

**Non-Goals:**
- Custom TTS plugin implementation — official LiveKit plugins exist for both providers
- SSML or emotion markup — not exposed by `livekit-plugins-inworld`
- Voice cloning or custom voice training
- TTS in text mode — text chat bypasses TTS entirely (S11 scope)
- Latency benchmarking or optimization beyond using streaming mode
- Prompt-driven TTS parameter changes — database-driven config is S10 scope

## Decisions

### D1. Use official `livekit-plugins-inworld` instead of a custom plugin

The S08 story description mentions "custom TTS plugin for Inworld AI in `apps/agent/src/plugins/`". However, `livekit-plugins-inworld` v1.4.4 already implements the full LiveKit TTS interface with WebSocket streaming and connection pooling.

**Alternatives considered:**
- *Custom plugin from scratch* — significant effort, self-maintained, no advantage over official plugin
- *Wrap official plugin with custom adapter* — unnecessary indirection; voice/language selection can be handled at session build time

**Decision:** Use `livekit-plugins-inworld` directly. Add `livekit-plugins-elevenlabs` for fallback. No `apps/agent/src/plugins/` directory needed.

### D2. TTS builder module at `apps/agent/src/tts.py`

Following the STT pattern (`stt.py` → `build_stt()`), create `tts.py` with `build_tts()` that returns the configured TTS plugin instance. The builder selects Inworld or ElevenLabs based on `TTS_PROVIDER` setting (default: `inworld`).

**Alternatives considered:**
- *Inline in agent.py* — breaks the established pattern of one module per pipeline component
- *Separate builders per provider* — premature; a single builder with provider switch is sufficient

### D3. Fallback strategy: configuration-based, not runtime

The fallback to ElevenLabs is controlled by the `TTS_PROVIDER` env var (`inworld` | `elevenlabs`), not by runtime health detection. If Inworld fails mid-session, the LiveKit agent framework's built-in retry/error handling applies.

**Alternatives considered:**
- *Runtime fallback with health checks* — complex, introduces dual-provider state management, hard to test. Better suited for a future resilience story
- *No fallback at all* — insufficient; ElevenLabs support is explicitly required by S08

**Rationale:** Runtime automatic failover between TTS providers adds significant complexity (different voice IDs, different audio formats, potential quality shifts mid-conversation). Config-based selection keeps the code simple and predictable. Operators switch providers via env var if one is down.

### D4. Language-aware voice mapping

A mapping dict in `tts.py` maps language codes to voice IDs per provider. Default voices:
- Inworld: `"Olivia"` (en), TBD (ru — pending language support verification)
- ElevenLabs: configurable via `ELEVENLABS_VOICE_ID` setting

The voice is selected at session build time based on `STT_LANGUAGE` setting. If `STT_LANGUAGE` is `"multi"`, default to English voice (dynamic language switching is S12 scope).

### D5. Russian language confirmed in Inworld

Inworld TTS supports Russian — verified by manual API testing. LiveKit docs language list is incomplete. Both providers (Inworld and ElevenLabs) support the required en + ru pair.

## Risks / Trade-offs

- **[Russian in Inworld confirmed]** → Both Inworld and ElevenLabs support Russian. No risk.
- **[No runtime failover]** → Acceptable for MVP. Operator switches `TTS_PROVIDER` env var. Automatic failover can be added in a future story.
- **[Audio format mismatch]** → Inworld defaults to LINEAR16 24kHz, ElevenLabs to MP3 22kHz. LiveKit handles transcoding to Opus for WebRTC transport, so this is transparent.
- **[S08 story mentions custom plugin]** → The story description predates the existence of `livekit-plugins-inworld`. Using the official plugin is a better engineering decision. The "module suitable for a PR to LiveKit Agents repository" goal is moot — it already exists upstream.
