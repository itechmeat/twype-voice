# Exploration: TTS Integration -- Inworld AI, ElevenLabs, LiveKit Agents Plugin Interface

Date: 2026-03-05

## Research question

What are the technical specifics of integrating TTS into the LiveKit Agents voice pipeline? Three sub-questions:

1. What is the Inworld AI TTS API surface -- endpoints, authentication, audio formats, streaming, configurable parameters?
2. Does an official `livekit-plugins-elevenlabs` package exist, and how is it configured?
3. What base class / protocol must a custom TTS plugin implement in the LiveKit Agents SDK?

## Scope

**In scope:** API surface, authentication, audio formats, streaming mechanisms, configurable voice parameters, LiveKit plugin interface contracts, existing official plugins for Inworld and ElevenLabs.

**Out of scope:** Pricing optimization, voice quality subjective comparisons, latency benchmarking, RAG integration, production deployment topology.

**Key constraint from project specs:** `livekit-agents >= 1.4.4`, Python 3.13+. The project architecture specifies Inworld as primary TTS and ElevenLabs as fallback.

## Findings

### 1. Official livekit-plugins-inworld exists -- no custom plugin needed

The most significant finding is that an [official `livekit-plugins-inworld` package](https://pypi.org/project/livekit-plugins-inworld/) already exists on PyPI. Current stable version is `1.4.4` (released March 3, 2026), with `1.5.0rc1` as a pre-release. It is maintained by the LiveKit team (maintainer: theomonnom) under Apache-2.0 license.

This means the project does not need to build a custom Inworld TTS plugin from scratch. The official plugin handles WebSocket connection pooling, streaming synthesis, audio format conversion, and the full LiveKit TTS interface contract.

Installation: `uv add "livekit-agents[inworld]~=1.4"`

**Confidence:** Corroborated (PyPI listing, LiveKit docs, GitHub source all confirm)

### 2. Inworld AI TTS API -- endpoints and protocols

Inworld exposes three API surfaces for TTS:

| Endpoint | URL | Method | Use case |
|----------|-----|--------|----------|
| Synchronous REST | `https://api.inworld.ai/tts/v1/voice` | POST | Batch, non-realtime |
| Streaming REST | `https://api.inworld.ai/tts/v1/voice:stream` | POST | Server-sent chunked audio |
| WebSocket (bidirectional) | `wss://api.inworld.ai/tts/v1/voice:streamBidirectional` | WS | Lowest latency, real-time conversational |

The LiveKit plugin uses the [WebSocket endpoint exclusively](https://github.com/livekit/agents/blob/main/livekit-plugins/livekit-plugins-inworld/livekit/plugins/inworld/tts.py) for both `synthesize()` and `stream()` methods, with a connection pool managing up to 20 connections, each supporting 5 concurrent contexts (100 concurrent streams total).

**Authentication:** HTTP header `Authorization: Basic {base64_api_key}`. The API key is Base64-encoded and obtained from the [Inworld platform](https://platform.inworld.ai/) under Settings > API Keys. Environment variable: `INWORLD_API_KEY`.

**Confidence:** Corroborated (Inworld docs, Pipecat source, LiveKit plugin source)

### 3. Inworld audio format support

The LiveKit plugin and Inworld API support these audio encodings:

| Encoding | MIME Type | Notes |
|----------|-----------|-------|
| LINEAR16 | `audio/wav` | PCM, default in LiveKit plugin |
| MP3 | `audio/mpeg` | Compressed |
| OGG_OPUS | `audio/ogg` | Compressed, low-latency codec |
| ALAW | `audio/basic` | Telephony codec |
| MULAW | `audio/basic` | Telephony codec |
| FLAC | `audio/flac` | Lossless compressed |

Default in the LiveKit plugin: LINEAR16 at 24000 Hz sample rate, 64000 bps bit rate. The Pipecat integration uses 48000 Hz LINEAR16 ([Pipecat source](https://reference-server.pipecat.ai/en/latest/_modules/pipecat/services/inworld/tts.html)).

Streaming responses contain base64-encoded audio chunks. WAV headers (first 44 bytes) are automatically stripped when concatenating chunks.

**Confidence:** Corroborated (PyPI description, LiveKit plugin source, Pipecat source)

### 4. Inworld configurable voice parameters

The LiveKit plugin exposes these parameters in the `inworld.TTS()` constructor:

| Parameter | Type | Default | Range/Notes |
|-----------|------|---------|-------------|
| `voice` | str | `"Ashley"` | Voice identifier (Ashley, Diego, Edward, Olivia, etc.) |
| `model` | str | `"inworld-tts-1.5-max"` | Model selection |
| `speaking_rate` | float | `1.0` | 0.5 (half speed) to 1.5 (1.5x) |
| `temperature` | float | `1.1` | 0 to 2; recommended 0.6-1.1 for natural output |
| `text_normalization` | str | `"ON"` | `ON`/`OFF`; expands numbers, dates, abbreviations |
| `encoding` | str | `"LINEAR16"` | One of: LINEAR16, MP3, OGG_OPUS, ALAW, MULAW, FLAC |
| `sample_rate` | int | `24000` | Hz |
| `bit_rate` | int | `64000` | bps |
| `timestamp_type` | str | optional | `WORD` or `CHARACTER`; enables aligned transcripts |
| `buffer_char_threshold` | int | `120` | WebSocket buffering: chars before synthesis starts |
| `max_buffer_delay_ms` | int | `3000` | WebSocket buffering: max delay before synthesis starts |
| `base_url` | str | `"https://api.inworld.ai/"` | REST base URL |
| `ws_url` | str | `"wss://api.inworld.ai/"` | WebSocket base URL |

There is no explicit `pitch` or `expressiveness` parameter. Temperature controls variation/expressiveness indirectly. There is no SSML support documented in the LiveKit plugin, though Inworld's [blog mentions audio markup for emotion and style](https://inworld.ai/blog/tts-custom-pronunciation-timestamps-websockets). Custom pronunciation is supported via Inworld's pronunciation guide feature.

**Confidence:** Substantiated (LiveKit plugin source, LiveKit docs; pitch/SSML absence is based on absence from source -- could exist undocumented)

### 5. Inworld available models

| Model ID | Latency | Cost | Languages |
|----------|---------|------|-----------|
| `inworld-tts-1.5-max` | <200ms P90 | $10/M chars | 13 languages including en, ru (see note) |
| `inworld-tts-1.5-mini` | ~120-130ms P90 | $5/M chars | 13 languages |
| `inworld-tts-1-max` | not specified | not specified | 13 languages |
| `inworld-tts-1` | not specified | not specified | 12 languages (no Turkish) |

**Language note:** The LiveKit docs list 13 languages for 1.5 models: en, es, fr, ko, nl, zh, de, it, ja, pl, pt, tr, hi. Inworld's marketing page claims 15 languages including Russian (ru), Arabic (ar), and Hebrew (he). The LiveKit docs language list does not include `ru`. This discrepancy could mean: (a) LiveKit Inference does not expose all Inworld languages, or (b) the LiveKit docs list is incomplete, or (c) ru support was added after the docs were written.

**Confidence:** Substantiated (LiveKit docs are explicit about 13 languages; ru presence is Conjecture based on Inworld marketing claims)

### 6. Inworld WebSocket streaming details

The WebSocket protocol uses JSON messages for control and base64-encoded audio chunks for data:

- **Create context:** Initializes a synthesis context with voice, model, audio config, and buffering parameters
- **Send text:** Pushes text tokens to a context (`{"send_text": {"text": "..."}, "contextId": "..."}`)
- **Flush context:** Signals end of text input for a context
- **Close context:** Terminates a context
- **Keepalive:** Sent every 60 seconds to maintain the connection
- **Multi-context:** Up to 5 independent contexts per WebSocket connection, each with its own voice settings
- **Auto mode:** Server-controlled text flushing for sentence-level input, configurable via `autoMode` boolean

Stale contexts are cleaned up after 120 seconds of inactivity (in the LiveKit plugin implementation).

**Confidence:** Corroborated (Pipecat source, LiveKit plugin source, Inworld blog)

### 7. ElevenLabs -- livekit-plugins-elevenlabs

The [`livekit-plugins-elevenlabs`](https://pypi.org/project/livekit-plugins-elevenlabs/) package exists on PyPI. Current stable version: `1.4.3` (released February 23, 2026), with `1.5.0rc1` as pre-release. Python >= 3.10.0.

Installation: `uv add "livekit-agents[elevenlabs]~=1.4"`

**Authentication:** `ELEVEN_API_KEY` environment variable.

**Constructor parameters for `elevenlabs.TTS()`:**

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `voice_id` | str | `"EXAVITQu4vr4xnSDxMaL"` | ElevenLabs voice identifier |
| `model` | str | `"eleven_flash_v2_5"` | Model ID |
| `language` | str | `"en"` | ISO-639-1 code |
| `streaming_latency` | int | `3` | Latency in seconds |
| `enable_ssml_parsing` | bool | `False` | SSML support |
| `chunk_length_schedule` | list[int] | `[80, 120, 200, 260]` | Chunk sizes (50-500) |

**Voice tuning parameters (via voice settings):**

| Parameter | Type | Notes |
|-----------|------|-------|
| `stability` | float | Voice consistency |
| `similarity_boost` | float | Voice similarity to original |
| `style` | float | Style exaggeration |
| `use_speaker_boost` | bool | Speaker clarity |
| `speed` | float | Speaking speed |

**Implementation details:** Uses HTTP POST for `synthesize()` (chunked response) and WebSocket for `stream()` (bidirectional). Default audio encoding: `mp3_22050_32` (MP3 at 22.05 kHz, 32 kbps). Supports MP3, Opus, and PCM output via encoding parameter. A shared `_Connection` class manages WebSocket connections with context-based message routing.

**Limitation:** Custom and community ElevenLabs voices, including voice cloning, are [not supported in LiveKit Inference](https://docs.livekit.io/agents/models/tts/plugins/elevenlabs/) -- but work with direct plugin usage (own API key).

**Confidence:** Corroborated (PyPI, LiveKit docs, GitHub source)

### 8. LiveKit Agents TTS plugin interface

The base class for all TTS plugins is [`tts.TTS`](https://docs.livekit.io/reference/python/livekit/agents/tts/index.html) from `livekit.agents`. Key interface:

```python
class TTS(ABC, EventEmitter[...]):
    def __init__(
        self,
        *,
        capabilities: TTSCapabilities,
        sample_rate: int,
        num_channels: int,
    ): ...

    # Required abstract method
    @abstractmethod
    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions,
    ) -> ChunkedStream: ...

    # Optional -- raises NotImplementedError by default
    def stream(
        self,
        *,
        conn_options: APIConnectOptions,
    ) -> SynthesizeStream: ...

    # Optional overrides
    @property
    def model(self) -> str: ...       # default: "unknown"
    @property
    def provider(self) -> str: ...    # default: "unknown"
    def prewarm(self) -> None: ...    # default: no-op
```

**`TTSCapabilities` dataclass:**
- `streaming: bool` -- whether the plugin supports `stream()` (WebSocket-based real-time synthesis)
- `aligned_transcript: bool` -- whether the plugin provides word-level timing metadata

**`ChunkedStream` (ABC):** Returned by `synthesize()`. Implements async iteration over `SynthesizedAudio` events. Provides `collect()` to gather all frames. Handles metrics and retry logic.

**`SynthesizeStream` (ABC):** Returned by `stream()`. Provides:
- `push_text(token: str)` -- queue text for synthesis
- `flush()` -- mark segment boundary
- `end_input()` -- finalize transmission

**`SynthesizedAudio` dataclass:**
- `frame: rtc.AudioFrame` -- synthesized audio data
- `request_id: str` -- tracking identifier
- `is_final: bool` -- segment completion flag
- `segment_id: str` -- streaming segment identifier
- `delta_text: str` -- associated text (streaming)

**Helper:** `_synthesize_with_stream()` wraps a `stream()` implementation to provide `synthesize()` for plugins that only support streaming inference.

**`AudioEmitter`:** Utility class that helps TTS implementers correctly handle `is_final` logic and audio frame aggregation.

**Confidence:** Corroborated (LiveKit API reference, GitHub source, DeepWiki analysis)

## Comparison

### Inworld vs ElevenLabs LiveKit plugins

| Criteria | livekit-plugins-inworld | livekit-plugins-elevenlabs |
|----------|------------------------|---------------------------|
| PyPI version (stable) | 1.4.4 | 1.4.3 |
| Streaming protocol | WebSocket (bidirectional) | WebSocket (bidirectional) |
| Non-streaming protocol | HTTP POST | HTTP POST |
| Default audio format | LINEAR16 24kHz | MP3 22.05kHz |
| Supported formats | LINEAR16, MP3, OGG_OPUS, ALAW, MULAW, FLAC | MP3, Opus, PCM |
| Speed control | `speaking_rate` (0.5-1.5) | `speed` (float) |
| Expressiveness control | `temperature` (0-2) | `stability`, `similarity_boost`, `style` |
| SSML support | Not in plugin | `enable_ssml_parsing` toggle |
| Auth env var | `INWORLD_API_KEY` | `ELEVEN_API_KEY` |
| Connection pooling | Yes (20 conns x 5 contexts) | Yes (shared connection) |
| Aligned transcripts | Yes (WORD/CHARACTER timestamps) | Yes |
| Russian language | Claimed by Inworld marketing; absent from LiveKit docs language list | Yes (eleven_multilingual_v2) |
| Custom/cloned voices | Not in LiveKit Inference; unclear for direct plugin | Not in LiveKit Inference; works with direct API key |

### Custom plugin vs official plugin

| Approach | Effort | Maintenance | Feature parity |
|----------|--------|-------------|---------------|
| Use `livekit-plugins-inworld` | Install dependency | Maintained by LiveKit team | Full -- WebSocket streaming, pooling, timestamps |
| Build custom plugin | Implement TTS base class, WebSocket client, connection pool | Self-maintained | Depends on implementation scope |

## Key takeaways

- An official `livekit-plugins-inworld` package (v1.4.4) exists and implements WebSocket streaming with connection pooling, eliminating the need for a custom plugin. (Corroborated)
- The Inworld TTS API supports three access modes: synchronous REST, streaming REST, and bidirectional WebSocket. The LiveKit plugin uses WebSocket exclusively. (Corroborated)
- Inworld supports six audio encodings (LINEAR16, MP3, OGG_OPUS, ALAW, MULAW, FLAC) with configurable sample rate and bit rate. (Corroborated)
- Configurable voice parameters are `speaking_rate` (0.5-1.5) and `temperature` (0-2, controls expressiveness). There is no explicit pitch parameter. (Substantiated)
- Russian language support in Inworld TTS is claimed in marketing materials but absent from the LiveKit docs language list -- this requires verification. (Conjecture -- depends on whether the marketing claim or the LiveKit docs list is authoritative)

## Open questions

1. **Russian language support in Inworld:** The LiveKit docs list 13 languages without Russian. Inworld marketing claims 15 languages including Russian. Which is accurate? This is critical for the project's dual-language requirement (en + ru). Needs direct API testing or Inworld support confirmation.
2. **Pitch control:** No explicit pitch parameter exists in the Inworld API or LiveKit plugin. If pitch control is a requirement, it is currently unavailable through this integration path.
3. **SSML / emotion markup:** Inworld's blog mentions "audio markup support for emotion and style" but the LiveKit plugin does not expose SSML parameters. The direct REST API may support it via the request body -- needs investigation if emotional expressiveness beyond `temperature` is required.
4. **ElevenLabs Russian voice quality:** While ElevenLabs `eleven_multilingual_v2` supports Russian, the quality and naturalness for Russian specifically has not been evaluated.
5. **LiveKit Inference vs direct API key:** LiveKit offers managed inference (no separate API key needed) but with limitations (no cloned voices). The project specs reference `INWORLD_API_KEY` directly, suggesting direct plugin usage is intended.

## Sources

1. [livekit-plugins-inworld on PyPI](https://pypi.org/project/livekit-plugins-inworld/) -- package version, supported encodings, license
2. [Inworld TTS LiveKit plugin docs](https://docs.livekit.io/agents/models/tts/plugins/inworld/) -- installation, parameters, voice options, model list
3. [Inworld TTS integration guide](https://docs.livekit.io/agents/integrations/tts/inworld/) -- configuration methods, LiveKit Inference vs direct usage
4. [Inworld Developer Quickstart](https://docs.inworld.ai/docs/quickstart-tts) -- API endpoints, authentication, request format, streaming details
5. [LiveKit Agents TTS API reference](https://docs.livekit.io/reference/python/livekit/agents/tts/index.html) -- base class, abstract methods, ChunkedStream, SynthesizeStream
6. [Inworld TTS plugin source (GitHub)](https://github.com/livekit/agents/blob/main/livekit-plugins/livekit-plugins-inworld/livekit/plugins/inworld/tts.py) -- constructor parameters, connection pooling, WebSocket implementation
7. [ElevenLabs TTS plugin source (GitHub)](https://github.com/livekit/agents/blob/main/livekit-plugins/livekit-plugins-elevenlabs/livekit/plugins/elevenlabs/tts.py) -- implementation pattern, audio formats, streaming architecture
8. [livekit-plugins-elevenlabs on PyPI](https://pypi.org/project/livekit-plugins-elevenlabs/) -- package version, Python requirements
9. [ElevenLabs TTS LiveKit plugin docs](https://docs.livekit.io/agents/models/tts/plugins/elevenlabs/) -- parameters, voice settings, limitations
10. [Pipecat Inworld TTS source](https://reference-server.pipecat.ai/en/latest/_modules/pipecat/services/inworld/tts.html) -- REST/WebSocket endpoints, request body schema, audio handling
11. [Inworld TTS WebSocket blog post](https://inworld.ai/blog/tts-custom-pronunciation-timestamps-websockets) -- WebSocket features, multi-context, smart buffering
12. [Inworld TTS overview](https://docs.inworld.ai/docs/tts/tts) -- models, latency, pricing, language count
13. [DeepWiki TTS Provider Implementations](https://deepwiki.com/livekit/agents/6.2-tts-provider-implementations) -- plugin architecture patterns
