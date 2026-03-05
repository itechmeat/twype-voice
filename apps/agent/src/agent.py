from __future__ import annotations

import logging
from typing import Any

from livekit.agents import Agent, AgentSession
from livekit.plugins import deepgram, silero
from settings import AgentSettings
from stt import build_stt

logger = logging.getLogger("twype-agent")


def format_participant(participant: Any | None) -> str:
    if participant is None:
        return "<unknown>"

    identity = getattr(participant, "identity", None) or "<no-identity>"
    name = getattr(participant, "name", None) or ""

    if name and name != identity:
        return f"{identity} ({name})"

    return str(identity)


def build_vad(settings: AgentSettings) -> silero.VAD:
    return silero.VAD.load(
        activation_threshold=settings.VAD_ACTIVATION_THRESHOLD,
        min_speech_duration=settings.VAD_MIN_SPEECH_DURATION,
        min_silence_duration=settings.VAD_MIN_SILENCE_DURATION,
    )


def build_session(
    settings: AgentSettings,
    *,
    vad: silero.VAD | None = None,
    stt: deepgram.STT | None = None,
) -> AgentSession:
    resolved_vad = vad or build_vad(settings)
    resolved_stt = stt or build_stt(settings)

    return AgentSession(
        vad=resolved_vad,
        stt=resolved_stt,
        turn_detection="vad",
    )


class TwypeAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="Listening mode. No responses.")

    async def on_enter(self) -> None:
        participant = getattr(getattr(self.session, "room_io", None), "linked_participant", None)
        logger.info("agent entered session, participant=%s", format_participant(participant))
