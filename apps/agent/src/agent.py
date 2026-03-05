from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from typing import Any

from livekit.agents import Agent, AgentSession
from livekit.agents import tts as livekit_tts
from livekit.plugins import deepgram, silero
from prompts import SYSTEM_PROMPT
from settings import AgentSettings
from stt import build_stt
from tts import build_tts

logger = logging.getLogger("twype-agent")


_FILLER_PHRASES_BY_LANGUAGE: dict[str, str] = {
    "ru": "Хм…",
    "en": "Hmm…",
}


def _pick_filler_phrase(language: str | None) -> str:
    normalized = (language or "").strip().lower()
    return _FILLER_PHRASES_BY_LANGUAGE.get(normalized) or _FILLER_PHRASES_BY_LANGUAGE["en"]


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
    llm: Any | None = None,
    tts: livekit_tts.TTS | None = None,
    turn_detection: str | None = None,
    min_endpointing_delay: float | None = None,
    max_endpointing_delay: float | None = None,
    preemptive_generation: bool | None = None,
    false_interruption_timeout: float | None = None,
    min_interruption_duration: float | None = None,
) -> AgentSession:
    resolved_vad = vad or build_vad(settings)
    resolved_stt = stt or build_stt(settings)
    resolved_tts = tts or build_tts(settings, language=settings.STT_LANGUAGE)

    resolved_turn_detection = turn_detection or settings.TURN_DETECTION_MODE
    resolved_min_endpointing_delay = (
        settings.MIN_ENDPOINTING_DELAY if min_endpointing_delay is None else min_endpointing_delay
    )
    resolved_max_endpointing_delay = (
        settings.MAX_ENDPOINTING_DELAY if max_endpointing_delay is None else max_endpointing_delay
    )
    resolved_preemptive_generation = (
        settings.PREEMPTIVE_GENERATION if preemptive_generation is None else preemptive_generation
    )
    resolved_false_interruption_timeout = (
        settings.FALSE_INTERRUPTION_TIMEOUT
        if false_interruption_timeout is None
        else false_interruption_timeout
    )
    if resolved_false_interruption_timeout == 0:
        resolved_false_interruption_timeout = None

    resolved_min_interruption_duration = (
        settings.MIN_INTERRUPTION_DURATION
        if min_interruption_duration is None
        else min_interruption_duration
    )

    return AgentSession(
        vad=resolved_vad,
        stt=resolved_stt,
        llm=llm,
        tts=resolved_tts,
        turn_detection=resolved_turn_detection,
        min_endpointing_delay=resolved_min_endpointing_delay,
        max_endpointing_delay=resolved_max_endpointing_delay,
        preemptive_generation=resolved_preemptive_generation,
        false_interruption_timeout=resolved_false_interruption_timeout,
        resume_false_interruption=True,
        min_interruption_duration=resolved_min_interruption_duration,
    )


class TwypeAgent(Agent):
    def __init__(
        self,
        *,
        thinking_sounds_enabled: bool = True,
        thinking_sounds_delay: float = 1.5,
        language_getter: Callable[[], str] | None = None,
    ) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self._thinking_sounds_enabled = thinking_sounds_enabled
        self._thinking_sounds_delay = thinking_sounds_delay
        self._language_getter = language_getter

    async def on_enter(self) -> None:
        participant = getattr(getattr(self.session, "room_io", None), "linked_participant", None)
        logger.info("agent entered session, participant=%s", format_participant(participant))

    async def llm_node(self, chat_ctx, tools, model_settings):
        if not self._thinking_sounds_enabled:
            passthrough = super().llm_node(chat_ctx, tools, model_settings)
            if asyncio.iscoroutine(passthrough):
                return await passthrough
            return passthrough

        result = super().llm_node(chat_ctx, tools, model_settings)
        if asyncio.iscoroutine(result):
            result = await result

        if result is None:
            return None

        if isinstance(result, str):
            return result

        if not hasattr(result, "__aiter__"):
            return result

        async def _gen():
            aiter = result.__aiter__()
            first_task = asyncio.create_task(aiter.__anext__())
            try:
                done, _pending = await asyncio.wait(
                    {first_task},
                    timeout=self._thinking_sounds_delay,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if not done:
                    language = self._language_getter() if callable(self._language_getter) else None
                    yield _pick_filler_phrase(language)

                try:
                    first_item = await first_task
                except StopAsyncIteration:
                    return

                yield first_item

                async for item in aiter:
                    yield item
            finally:
                if not first_task.done():
                    first_task.cancel()
                    with contextlib.suppress(Exception):
                        await first_task

        return _gen()
