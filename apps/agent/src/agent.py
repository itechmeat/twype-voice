from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterable, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from languages import normalize_language_code
from livekit.agents import Agent, AgentSession, llm
from livekit.agents import tts as livekit_tts
from livekit.plugins import deepgram, silero
from prompts import (
    FALLBACK_SYSTEM_PROMPT,
    FALLBACK_TEXT_GUIDANCE,
    FALLBACK_VOICE_GUIDANCE,
)
from rag import RagEngine, format_rag_context
from settings import AgentSettings
from stt import build_stt
from tts import build_tts

logger = logging.getLogger("twype-agent")


_DEFAULT_FILLER_PHRASE = "Hmm…"
MODE_ANNOTATION_HISTORY_COUNT = 6
ModeName = Literal["voice", "text"]


@dataclass(slots=True)
class ModeContext:
    current_mode: ModeName = "voice"
    previous_mode: ModeName = "voice"
    current_language: str | None = None
    switched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def switch_to(self, mode: ModeName) -> None:
        if mode == self.current_mode:
            return

        self.previous_mode = self.current_mode
        self.current_mode = mode
        self.switched_at = datetime.now(UTC)

    def set_language(self, language: str | None) -> None:
        normalized = normalize_language_code(language)
        if normalized:
            self.current_language = normalized


def _pick_filler_phrase() -> str:
    return _DEFAULT_FILLER_PHRASE


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
        instructions: str = FALLBACK_SYSTEM_PROMPT,
        mode_voice_guidance: str = FALLBACK_VOICE_GUIDANCE,
        mode_text_guidance: str = FALLBACK_TEXT_GUIDANCE,
        thinking_sounds_enabled: bool = True,
        thinking_sounds_delay: float = 1.5,
        default_language: str = "en",
        rag_engine: RagEngine | None = None,
    ) -> None:
        super().__init__(instructions=instructions)
        self.mode_context = ModeContext()
        self._mode_voice_guidance = mode_voice_guidance
        self._mode_text_guidance = mode_text_guidance
        self._thinking_sounds_enabled = thinking_sounds_enabled
        self._thinking_sounds_delay = thinking_sounds_delay
        self._chat_response_publisher: Callable[[str], Awaitable[None]] | None = None
        self._default_language = normalize_language_code(default_language) or "en"
        self.rag_engine = rag_engine

    @property
    def text_mode_active(self) -> bool:
        return self.mode_context.current_mode == "text"

    def set_chat_response_publisher(
        self,
        publisher: Callable[[str], Awaitable[None]] | None,
    ) -> None:
        self._chat_response_publisher = publisher

    async def on_enter(self) -> None:
        participant = getattr(getattr(self.session, "room_io", None), "linked_participant", None)
        logger.info("agent entered session, participant=%s", format_participant(participant))

    def _mode_guidance_text(self) -> str:
        if self.mode_context.current_mode == "text":
            return self._mode_text_guidance.strip() or FALLBACK_TEXT_GUIDANCE
        return self._mode_voice_guidance.strip() or FALLBACK_VOICE_GUIDANCE

    def _message_mode(self, message: llm.ChatMessage) -> ModeName:
        if message.role != "user":
            return "voice"

        extra = message.extra if isinstance(message.extra, dict) else {}
        mode = extra.get("mode")
        if mode in {"voice", "text"}:
            return mode
        return "voice"

    def _annotate_user_message(self, message: llm.ChatMessage) -> llm.ChatMessage:
        annotated = message.model_copy(deep=True)
        if annotated.role != "user":
            return annotated

        prefix = f"[{self._message_mode(annotated)}] "
        updated_content = list(annotated.content)
        for index, item in enumerate(updated_content):
            if isinstance(item, str):
                updated_content[index] = f"{prefix}{item}"
                annotated.content = updated_content
                return annotated

        annotated.content = [prefix.rstrip(), *updated_content]
        return annotated

    def _build_mode_aware_chat_ctx(self, chat_ctx: llm.ChatContext | None) -> llm.ChatContext:
        source = chat_ctx.copy() if chat_ctx is not None else llm.ChatContext.empty()
        user_message_indexes = [
            index
            for index, item in enumerate(source.items)
            if isinstance(item, llm.ChatMessage) and item.role == "user"
        ]
        annotated_indexes = set(user_message_indexes[-MODE_ANNOTATION_HISTORY_COUNT:])

        items: list[llm.ChatItem] = []
        merged_into_existing_system = False
        guidance = self._mode_guidance_text()

        for index, item in enumerate(source.items):
            if not isinstance(item, llm.ChatMessage):
                items.append(item)
                continue

            copied_item = item.model_copy(deep=True)

            if copied_item.role == "system" and not merged_into_existing_system:
                updated_content = list(copied_item.content)
                for content_index, content_item in enumerate(updated_content):
                    if isinstance(content_item, str):
                        updated_content[content_index] = f"{guidance}\n\n{content_item}"
                        break
                else:
                    updated_content = [guidance, *updated_content]

                copied_item.content = updated_content
                copied_item.extra = {
                    **(copied_item.extra if isinstance(copied_item.extra, dict) else {}),
                    "mode": self.mode_context.current_mode,
                }
                merged_into_existing_system = True
                items.append(copied_item)
                continue

            if copied_item.role == "user" and index in annotated_indexes:
                copied_item = self._annotate_user_message(copied_item)

            items.append(copied_item)

        if not merged_into_existing_system:
            items.insert(
                0,
                llm.ChatMessage(
                    role="system",
                    content=[guidance],
                    extra={"mode": self.mode_context.current_mode},
                ),
            )

        return llm.ChatContext(items=items)

    def _last_user_message(self, chat_ctx: llm.ChatContext | None) -> llm.ChatMessage | None:
        if chat_ctx is None:
            return None

        for item in reversed(chat_ctx.items):
            if isinstance(item, llm.ChatMessage) and item.role == "user":
                return item
        return None

    def _resolve_rag_language(self, message: llm.ChatMessage | None) -> str | None:
        if message is not None and isinstance(message.extra, dict):
            for key in ("language", "locale"):
                value = message.extra.get(key)
                normalized = (
                    normalize_language_code(str(value)) if isinstance(value, str) else None
                )
                if normalized:
                    return normalized

        if self.mode_context.current_language:
            return self.mode_context.current_language
        return self._default_language

    async def _inject_rag_context(
        self,
        chat_ctx: llm.ChatContext | None,
        mode_aware_chat_ctx: llm.ChatContext,
    ) -> llm.ChatContext:
        if self.rag_engine is None:
            return mode_aware_chat_ctx

        message = self._last_user_message(chat_ctx)
        if message is None:
            return mode_aware_chat_ctx

        raw_text = message.text_content
        if not raw_text:
            return mode_aware_chat_ctx

        query_text = raw_text.strip()
        if not query_text:
            return mode_aware_chat_ctx

        try:
            chunks = await self.rag_engine.search(
                query_text,
                language=self._resolve_rag_language(message),
            )
        except Exception:
            logger.exception("rag search failed")
            return mode_aware_chat_ctx

        rag_context = format_rag_context(chunks)
        if not rag_context:
            return mode_aware_chat_ctx

        mode_aware_chat_ctx.add_message(
            role="system",
            content=rag_context,
            extra={"rag": True},
        )
        return mode_aware_chat_ctx

    async def llm_node(self, chat_ctx, tools, model_settings):
        mode_aware_chat_ctx = self._build_mode_aware_chat_ctx(chat_ctx)
        mode_aware_chat_ctx = await self._inject_rag_context(chat_ctx, mode_aware_chat_ctx)

        if not self._thinking_sounds_enabled or self.text_mode_active:
            passthrough = super().llm_node(mode_aware_chat_ctx, tools, model_settings)
            if asyncio.iscoroutine(passthrough):
                return await passthrough
            return passthrough

        result = super().llm_node(mode_aware_chat_ctx, tools, model_settings)
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
                    yield _pick_filler_phrase()

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

    async def tts_node(self, text: AsyncIterable[str], model_settings):
        if not self.text_mode_active:
            result = super().tts_node(text, model_settings)
            if asyncio.iscoroutine(result):
                return await result
            return result

        async for chunk in text:
            if self._chat_response_publisher is not None and chunk:
                await self._chat_response_publisher(chunk)

        return None
