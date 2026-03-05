from __future__ import annotations

from livekit.plugins import deepgram
from settings import AgentSettings


def build_stt(settings: AgentSettings) -> deepgram.STT:
    # TODO: Deepgram API supports sentiment=true, but livekit-plugins-deepgram
    # doesn't expose it yet. Consider contributing a PR to LiveKit.
    # https://developers.deepgram.com/docs/sentiment-analysis
    return deepgram.STT(
        api_key=settings.DEEPGRAM_API_KEY,
        model=settings.STT_MODEL,
        language=settings.STT_LANGUAGE,
    )
