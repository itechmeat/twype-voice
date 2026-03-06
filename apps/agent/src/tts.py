from __future__ import annotations

from languages import normalize_language_code
from livekit.agents import tts as livekit_tts
from livekit.plugins import elevenlabs, inworld
from settings import AgentSettings

# TODO: Replace placeholder language mappings with verified per-language voices/voice_ids.
# Currently both providers use the same defaults for "en" and "ru".
_INWORLD_VOICE_BY_LANGUAGE: dict[str, str] = {
    "en": "Olivia",
    "ru": "Olivia",
}

_ELEVENLABS_VOICE_ID_BY_LANGUAGE: dict[str, str] = {
    "en": "EXAVITQu4vr4xnSDxMaL",
    "ru": "EXAVITQu4vr4xnSDxMaL",
}
def build_tts(settings: AgentSettings, language: str | None = None) -> livekit_tts.TTS:
    normalized_language = normalize_language_code(language, multi="en")

    if settings.TTS_PROVIDER == "inworld":
        voice = (
            _INWORLD_VOICE_BY_LANGUAGE.get(normalized_language) if normalized_language else None
        ) or settings.TTS_INWORLD_VOICE

        return inworld.TTS(
            api_key=settings.INWORLD_API_KEY,
            voice=voice,
            model=settings.TTS_INWORLD_MODEL,
            speaking_rate=settings.TTS_SPEAKING_RATE,
            temperature=settings.TTS_TEMPERATURE,
        )

    if settings.TTS_PROVIDER == "elevenlabs":
        voice_id = (
            _ELEVENLABS_VOICE_ID_BY_LANGUAGE.get(normalized_language)
            if normalized_language
            else None
        ) or settings.TTS_ELEVENLABS_VOICE_ID

        resolved_language = normalized_language or "en"

        return elevenlabs.TTS(
            api_key=settings.ELEVENLABS_API_KEY,
            voice_id=voice_id,
            model=settings.TTS_ELEVENLABS_MODEL,
            language=resolved_language,
        )

    raise ValueError(f"Unsupported TTS_PROVIDER: {settings.TTS_PROVIDER!r}")
