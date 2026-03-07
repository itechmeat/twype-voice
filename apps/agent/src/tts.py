from __future__ import annotations

from languages import normalize_language_code
from livekit.agents import tts as livekit_tts
from livekit.plugins import elevenlabs, inworld
from settings import AgentSettings


def build_tts(settings: AgentSettings, language: str | None = None) -> livekit_tts.TTS:
    normalized_language = normalize_language_code(
        language or settings.STT_LANGUAGE,
        multi=settings.PROMPT_DEFAULT_LOCALE,
    )

    if settings.TTS_PROVIDER == "inworld":
        return inworld.TTS(
            api_key=settings.INWORLD_API_KEY,
            voice=settings.TTS_INWORLD_VOICE,
            model=settings.TTS_INWORLD_MODEL,
            speaking_rate=settings.TTS_SPEAKING_RATE,
            temperature=settings.TTS_TEMPERATURE,
        )

    if settings.TTS_PROVIDER == "elevenlabs":
        if normalized_language is None:
            raise RuntimeError("Unable to resolve TTS language for ElevenLabs")

        return elevenlabs.TTS(
            api_key=settings.ELEVENLABS_API_KEY,
            voice_id=settings.TTS_ELEVENLABS_VOICE_ID,
            model=settings.TTS_ELEVENLABS_MODEL,
            language=normalized_language,
        )

    raise ValueError(f"Unsupported TTS_PROVIDER: {settings.TTS_PROVIDER!r}")
