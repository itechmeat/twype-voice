from __future__ import annotations

from livekit.plugins import deepgram
from settings import AgentSettings


def build_stt(settings: AgentSettings) -> deepgram.STT:
    return deepgram.STT(
        api_key=settings.DEEPGRAM_API_KEY,
        model=settings.STT_MODEL,
        language=settings.STT_LANGUAGE,
        sentiment=True,
    )
